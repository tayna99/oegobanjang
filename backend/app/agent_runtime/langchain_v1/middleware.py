from __future__ import annotations

import re
import hashlib
import json
from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelResponse
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.messages import AIMessage, ToolMessage

from app.agent_runtime.schemas import EventType

from .schemas import (
    ApprovalBlock,
    HandoffDraft,
    RuntimeContext,
    WorkBridgeAgentResponse,
    assert_no_forbidden_response_keys,
)


FORBIDDEN_TERMS = (
    "성실",
    "이탈 가능성",
    "도망",
    "국적별 선호",
    "베트남 후보가 더",
    "네팔 후보가 더",
    "좋은 사람",
    "장기근속 가능성",
    "비자 가능 확정",
    "비자 불가능 확정",
)

FORBIDDEN_INPUT_TERMS = FORBIDDEN_TERMS + (
    "추천해줘",
    "더 나아",
    "더 낫",
    "오래 일할",
    "비자 발급 가능",
    "가능 여부 확정",
)

PII_PATTERNS = (
    ("passport_or_registration", re.compile(r"\b[A-Z][0-9]{7,9}\b")),
    ("alien_registration_number", re.compile(r"\b\d{6}-\d{7}\b")),
    ("korean_phone", re.compile(r"\b010-\d{3,4}-\d{4}\b")),
)


class SafetyValidationError(ValueError):
    pass


def _event(
    *,
    event_type: EventType,
    request_id: str,
    summary: str,
    step_name: str,
    metadata: dict[str, Any] | None = None,
    risk_level: str = "LOW",
) -> dict[str, Any]:
    return {
        "event_type": event_type.value,
        "request_id": request_id,
        "summary": redact_pii(summary),
        "step_name": step_name,
        "metadata": metadata or {},
        "risk_level": risk_level,
    }


def redact_pii(text: str) -> str:
    redacted = text
    for _, pattern in PII_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _detect_foreign_hiring_pii(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for pii_type, pattern in PII_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(
                {
                    "type": pii_type,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return matches


def validate_response_safety(response: WorkBridgeAgentResponse) -> None:
    payload_dict = response.model_dump(mode="json")
    assert_no_forbidden_response_keys(payload_dict)
    payload = response.model_dump_json()
    for term in FORBIDDEN_TERMS:
        if term in payload:
            raise SafetyValidationError(f"forbidden term in structured response: {term}")


def build_blocked_response(
    *,
    reason: str,
    user_message: str = "",
) -> WorkBridgeAgentResponse:
    return WorkBridgeAgentResponse(
        final_response=(
            "요청을 자동 처리하지 않았습니다. 후보자 평가, 국적 선호, 비자 확정 판단, "
            "외부 자동 발송은 담당자 검토가 필요합니다."
        ),
        detected_intents=_infer_blocked_intents(user_message),
        risk_flags=["langchain_v1_blocked"],
        approval=ApprovalBlock(
            required=True,
            status="PENDING",
            reason="자동 실행 없이 담당자 검토가 필요합니다.",
            blocked_actions=[
                "auto_send_to_candidate",
                "auto_submit_to_government_portal",
                "auto_send_to_admin_scrivener",
            ],
        ),
        handoff=HandoffDraft(available=False),
        blocked_reason=redact_pii(reason),
    )


def _infer_blocked_intents(message: str) -> list[str]:
    text = message.lower()
    if any(term in text for term in ["성실", "이탈", "추천", "국적", "더 나", "더 낫"]):
        return ["UNSUPPORTED_VALUE_JUDGMENT"]
    if any(term in text for term in ["법적", "법률", "확정", "가능 여부", "비자 발급 가능"]):
        return ["UNSUPPORTED_LEGAL_JUDGMENT"]
    if any(term in text for term in ["발송", "전송", "문자", "카톡", "메시지"]):
        return ["CONTACT"]
    if any(term in text for term in ["채용", "고용", "인력", "e-9", "근로자"]):
        return ["HIRING"]
    return ["BRIEFING"]


def _context_from_runtime(runtime: Any) -> RuntimeContext | None:
    context = getattr(runtime, "context", None)
    return context if isinstance(context, RuntimeContext) else None


def _json_payload(content: Any) -> Any:
    if isinstance(content, (dict, list)):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    return None


def _hash_messages(messages: list[Any]) -> str:
    redacted = redact_pii(
        json.dumps([str(getattr(msg, "content", msg)) for msg in messages], ensure_ascii=False)
    )
    return hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:16]


class WorkBridgeSafetyMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request, handler):
        context = _context_from_runtime(request.runtime)
        message_text = "\n".join(str(getattr(msg, "content", msg)) for msg in request.messages)
        for term in FORBIDDEN_INPUT_TERMS:
            if term in message_text:
                response = build_blocked_response(
                    reason=f"forbidden input term: {term}",
                    user_message=context.user_message if context else message_text,
                )
                if context is not None:
                    context.evidence_events.append(
                        _event(
                            event_type=EventType.RISK_FLAGGED,
                            request_id=context.request_id,
                            step_name="workbridge_safety_middleware",
                            summary=f"Forbidden request blocked before model call: {term}",
                            risk_level="HIGH",
                            metadata={"term": term},
                        )
                    )
                return ModelResponse(
                    result=[AIMessage(content=response.final_response)],
                    structured_response=response,
                )
        response = await handler(request)
        if response.structured_response is not None:
            if isinstance(response.structured_response, WorkBridgeAgentResponse):
                validate_response_safety(response.structured_response)
            elif isinstance(response.structured_response, dict):
                assert_no_forbidden_response_keys(response.structured_response)
        return response


class EvidenceCaptureMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request, handler):
        context = _context_from_runtime(request.runtime)
        try:
            response = await handler(request)
        except Exception as exc:
            if context is not None:
                context.model_metadata = {
                    "raw_present": False,
                    "raw_content_hash": _hash_messages(request.messages),
                    "parsing_error": str(exc),
                    "model_name": str(getattr(request.model, "model_name", request.model)),
                }
            raise

        if context is not None:
            context.model_metadata = {
                "raw_present": bool(response.result),
                "raw_content_hash": _hash_messages(response.result),
                "parsing_error": None if response.structured_response is not None else "missing_structured_response",
                "model_name": str(getattr(request.model, "model_name", request.model)),
            }
        return response

    async def awrap_tool_call(self, request, handler):
        context = _context_from_runtime(request.runtime)
        tool_name = (
            getattr(request.tool, "name", None)
            or request.tool_call.get("name")
            or "unknown_tool"
        )
        result = await handler(request)
        payload = _json_payload(getattr(result, "content", None))

        if context is not None:
            context.evidence_events.append(
                _event(
                    event_type=EventType.TOOL_EXECUTED,
                    request_id=context.request_id,
                    step_name=str(tool_name),
                    summary=f"LangChain tool executed: {tool_name}",
                    metadata={"tool_name": tool_name},
                )
            )

            if tool_name == "retrieve_workforce_materials" and isinstance(payload, dict):
                records = payload.get("records") or []
                context.evidence_events.append(
                    _event(
                        event_type=EventType.RAG_RETRIEVED,
                        request_id=context.request_id,
                        step_name=str(tool_name),
                        summary=f"RAG materials retrieved: {len(records)}",
                        metadata={
                            "source_ids": [row.get("source_id") for row in records],
                            "evidence_grades": [row.get("evidence_grade") for row in records],
                            "doc_types": [row.get("doc_type") for row in records],
                        },
                    )
                )

            if isinstance(payload, dict) and (
                payload.get("status") == "NEEDS_APPROVAL" or payload.get("approval_required")
            ):
                context.approval_metadata = {
                    "tool_name": tool_name,
                    "status": payload.get("status"),
                    "reason": payload.get("error") or "approval-required tool call",
                    "blocked_actions": [tool_name],
                }
                context.interrupt_metadata = {
                    "tool_name": tool_name,
                    "action": "approval_required_tool_call",
                    "reason": context.approval_metadata["reason"],
                    "blocked_actions": [tool_name],
                }
                context.evidence_events.append(
                    _event(
                        event_type=EventType.APPROVAL_REQUESTED,
                        request_id=context.request_id,
                        step_name=str(tool_name),
                        summary=context.approval_metadata["reason"],
                        risk_level="MEDIUM",
                        metadata=context.approval_metadata,
                    )
                )

        if isinstance(result, ToolMessage):
            return ToolMessage(
                content=redact_pii(str(result.content)),
                tool_call_id=result.tool_call_id,
                name=result.name,
                status=result.status,
                artifact=result.artifact,
            )
        return result


def build_langchain_v1_middleware() -> Sequence[Any]:
    """LangChain v1 middleware boundary.

    P0 uses HITL as a second safety net. Approval-required tools still return
    NEEDS_APPROVAL and the runtime adapter synthesizes the PENDING response.
    """

    return [
        WorkBridgeSafetyMiddleware(),
        EvidenceCaptureMiddleware(),
        PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True),
        PIIMiddleware(
            "foreign_hiring_pii",
            strategy="redact",
            detector=_detect_foreign_hiring_pii,
            apply_to_input=True,
            apply_to_output=True,
        ),
        ModelCallLimitMiddleware(run_limit=8),
        ToolCallLimitMiddleware(run_limit=12),
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_worker_message": True,
                "send_expert_package": True,
                "update_case_status_completed": True,
            }
        ),
    ]
