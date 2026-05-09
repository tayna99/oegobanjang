from __future__ import annotations

from pathlib import Path

import pytest

from app.agent_runtime.langchain_v1.runtime import (
    normalize_runtime_input,
    run_langchain_v1_agent,
    to_foreign_hiring_state,
)
from app.agent_runtime.langchain_v1.schemas import (
    ApprovalBlock,
    HandoffDraft,
    WorkBridgeAgentResponse,
)
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from app.agent_runtime.schemas import Intent


class FakeAgent:
    async def ainvoke(self, payload):
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="신규 고용 준비 초안입니다.",
                detected_intents=["HIRING"],
                risk_flags=[],
                approval=ApprovalBlock(required=False, status="NOT_REQUIRED"),
                handoff=HandoffDraft(available=False),
                rag_contexts=[
                    {
                        "source_id": "eps_employer_process",
                        "title": "사업주 고용절차",
                    }
                ],
                domain_payload={"runtime": "fake"},
                blocked_reason="",
            )
        }


def test_user_request_is_normalized_into_runtime_input() -> None:
    runtime_input = normalize_runtime_input(
        user_request="베트남 근로자에게 안전교육 안내 메시지 작성해줘",
        input_payload={"task_type": "message_draft"},
    )

    assert runtime_input.user_message == "베트남 근로자에게 안전교육 안내 메시지 작성해줘"
    assert runtime_input.input_payload == {"task_type": "message_draft"}
    assert runtime_input.thread_id == runtime_input.request_id


@pytest.mark.asyncio
async def test_runtime_uses_structured_response_from_create_agent_shape() -> None:
    runtime_input = normalize_runtime_input(
        user_message="E-9 근로자 신규 고용 준비해줘",
        user_id="user-1",
        company_id="company-1",
    )

    state = await run_langchain_v1_agent(runtime_input, agent=FakeAgent())
    compat_state = to_foreign_hiring_state(state)

    assert state.structured_response.final_response == "신규 고용 준비 초안입니다."
    assert compat_state.detected_intents == [Intent.HIRING]
    assert len(compat_state.rag_contexts) == 1
    assert runtime_state_store.get(runtime_input.request_id) is not None


@pytest.mark.asyncio
async def test_runtime_missing_openai_key_returns_structured_blocked_response(
    monkeypatch,
) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module
    from app.agent_runtime.langchain_v1.tools import RuntimePreflightError

    def fail_create_agent(*args, **kwargs):
        raise RuntimePreflightError("OPENAI_API_KEY is required for langchain_v1 runtime")

    monkeypatch.setattr(runtime_module, "create_workbridge_agent", fail_create_agent)
    runtime_input = normalize_runtime_input(
        user_message="E-9 근로자 3명 채용 준비해줘",
        user_id="user-1",
        company_id="company-1",
    )

    state = await run_langchain_v1_agent(runtime_input)
    compat_state = to_foreign_hiring_state(state)

    assert state.structured_response.blocked_reason
    assert compat_state.approval.required is True
    assert compat_state.approval.status == "PENDING"
    assert compat_state.detected_intents == [Intent.HIRING]


def test_production_api_and_runner_do_not_import_custom_graph_workflow() -> None:
    root = Path(__file__).resolve().parents[2]
    runner_source = (root / "backend/app/agent_runtime/runner.py").read_text(encoding="utf-8")
    api_source = (root / "backend/app/api/v1/agent.py").read_text(encoding="utf-8")

    assert "app.agent_runtime.graph.workflow" not in runner_source
    assert "app.agent_runtime.graph.workflow" not in api_source
    assert "get_compiled_app" not in runner_source
    assert "get_compiled_app" not in api_source
