from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, ToolMessage

from app.agent_runtime.langchain_v1.middleware import (
    EvidenceCaptureMiddleware,
    WorkBridgeSafetyMiddleware,
    redact_pii,
)
from app.agent_runtime.langchain_v1.schemas import (
    ApprovalBlock,
    RuntimeContext,
    WorkBridgeAgentResponse,
)


def _runtime(context: RuntimeContext) -> SimpleNamespace:
    return SimpleNamespace(context=context)


def test_strict_response_rejects_extra_and_disallowed_evidence() -> None:
    with pytest.raises(ValidationError):
        WorkBridgeAgentResponse.model_validate(
            {
                "final_response": "검토 결과입니다.",
                "candidate_score": 0.9,
            }
        )

    with pytest.raises(ValidationError):
        WorkBridgeAgentResponse(
            final_response="검토 결과입니다.",
            rag_contexts=[
                {
                    "source_id": "synthetic_case",
                    "doc_type": "case_record",
                    "evidence_grade": "F",
                }
            ],
        )


@pytest.mark.asyncio
async def test_safety_middleware_blocks_forbidden_input_without_model_call() -> None:
    context = RuntimeContext(
        request_id="req-safety",
        user_message="후보 A가 더 성실한지 추천해줘",
    )
    request = SimpleNamespace(
        messages=[SimpleNamespace(content=context.user_message)],
        runtime=_runtime(context),
    )

    async def handler(_request):
        raise AssertionError("model should not be called for forbidden input")

    result = await WorkBridgeSafetyMiddleware().awrap_model_call(request, handler)

    assert isinstance(result, ModelResponse)
    assert result.structured_response.blocked_reason
    assert result.structured_response.approval.required is True
    assert result.structured_response.approval.status == "PENDING"
    assert context.evidence_events[0]["event_type"] == "risk_flagged"


@pytest.mark.asyncio
async def test_evidence_middleware_records_tool_and_rag_events() -> None:
    context = RuntimeContext(request_id="req-rag", user_message="E-9 신규 고용 절차")
    request = SimpleNamespace(
        tool=SimpleNamespace(name="retrieve_workforce_materials"),
        tool_call={"name": "retrieve_workforce_materials", "id": "tool-1"},
        runtime=_runtime(context),
    )
    payload = {
        "records": [
            {
                "source_id": "eps_employer_process",
                "doc_type": "procedure_step",
                "evidence_grade": "B",
            }
        ]
    }

    async def handler(_request):
        return ToolMessage(content=json.dumps(payload), tool_call_id="tool-1")

    result = await EvidenceCaptureMiddleware().awrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)
    event_types = [event["event_type"] for event in context.evidence_events]
    assert "tool_executed" in event_types
    assert "rag_retrieved" in event_types
    rag_event = next(event for event in context.evidence_events if event["event_type"] == "rag_retrieved")
    assert rag_event["metadata"]["source_ids"] == ["eps_employer_process"]


@pytest.mark.asyncio
async def test_evidence_middleware_records_approval_tool_metadata() -> None:
    context = RuntimeContext(request_id="req-approval", user_message="문자 발송해줘")
    request = SimpleNamespace(
        tool=SimpleNamespace(name="send_worker_message"),
        tool_call={"name": "send_worker_message", "id": "tool-approval"},
        runtime=_runtime(context),
    )
    payload = {
        "tool_name": "send_worker_message",
        "status": "NEEDS_APPROVAL",
        "approval_required": True,
        "error": "담당자 승인 후 실행 가능한 작업입니다.",
    }

    async def handler(_request):
        return ToolMessage(content=json.dumps(payload, ensure_ascii=False), tool_call_id="tool-approval")

    await EvidenceCaptureMiddleware().awrap_tool_call(request, handler)

    assert context.approval_metadata["tool_name"] == "send_worker_message"
    assert context.interrupt_metadata["action"] == "approval_required_tool_call"
    assert any(event["event_type"] == "approval_requested" for event in context.evidence_events)


@pytest.mark.asyncio
async def test_evidence_middleware_records_model_metadata_without_raw_pii() -> None:
    context = RuntimeContext(request_id="req-model", user_message="상태 확인")
    request = SimpleNamespace(
        messages=[SimpleNamespace(content="010-1234-5678 M12345678")],
        runtime=_runtime(context),
        model=SimpleNamespace(model_name="fake-model"),
    )
    structured = WorkBridgeAgentResponse(
        final_response="검토 결과입니다.",
        approval=ApprovalBlock(required=False),
    )

    async def handler(_request):
        return ModelResponse(
            result=[AIMessage(content="전화번호 010-1234-5678")],
            structured_response=structured,
        )

    await EvidenceCaptureMiddleware().awrap_model_call(request, handler)

    assert context.model_metadata["model_name"] == "fake-model"
    assert context.model_metadata["raw_present"] is True
    assert context.model_metadata["raw_content_hash"]
    assert "010-1234-5678" not in json.dumps(context.model_metadata, ensure_ascii=False)
    assert redact_pii("010-1234-5678 M12345678") == "[REDACTED] [REDACTED]"
