from __future__ import annotations

import hashlib
import ast
import json
import re
import time
from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.agents.middleware.types import ModelResponse
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
    "성격",
    "이탈 가능성",
    "도망",
    "국적별 선호",
    "국적 우열",
    "좋은 사람",
    "더 나은 후보",
    "더 낫",
    "오래 일할",
    "장기근속",
    "추천",
    "비자 가능 확정",
    "비자 불가능 확정",
    "최종 판정",
    "candidate_score",
    "nationality_preference",
    "reliability_score",
    "absconding_prediction",
    "final_eligibility_decision",
)

FORBIDDEN_INPUT_TERMS = FORBIDDEN_TERMS + (
    "추천해줘",
    "누가 나아",
    "누가 더 나아",
    "비자 발급 가능",
    "가능 여부 확정",
)
from .contact_subagents import CONTACT_ONBOARDING_SUB_AGENT
from .contact_subagents import WORKER_REPLY_INTERPRETER_SUB_AGENT

DISALLOWED_RAG_EVIDENCE_GRADES = {"D", "F"}
DISALLOWED_RAG_DOC_TYPES = {"case", "case_record"}

PII_PATTERNS = (
    ("passport_or_registration", re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,2}[0-9]{7,9}(?![A-Za-z0-9])")),
    ("alien_registration_number", re.compile(r"(?<!\d)\d{6}-\d{7}(?!\d)")),
    ("korean_phone", re.compile(r"(?<!\d)010-\d{3,4}-\d{4}(?!\d)")),
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
            "요청을 자동 처리하지 않았습니다. 후보 평가, 국적 선호, 비자 확정 판단, "
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
                "auto_send_to_sending_agency",
                "auto_submit_to_government_portal",
                "auto_send_to_admin_scrivener",
            ],
        ),
        handoff=HandoffDraft(available=False),
        blocked_reason=redact_pii(reason),
    )


def _infer_blocked_intents(message: str) -> list[str]:
    text = message.lower()
    if any(term in text for term in ["성실", "이탈", "추천", "국적", "누가 나아", "더 낫"]):
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
    if isinstance(content, dict):
        if "text" in content and set(content).issubset({"type", "text"}):
            parsed = _json_payload(content.get("text"))
            if parsed is not None:
                return parsed
        if "content" in content and set(content).issubset({"type", "content"}):
            parsed = _json_payload(content.get("content"))
            if parsed is not None:
                return parsed
        return content
    if isinstance(content, list):
        for item in content:
            payload = _json_payload(item)
            if payload is not None:
                return payload
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(content)
            except (ValueError, SyntaxError):
                return None
    return None


def _hash_messages(messages: list[Any]) -> str:
    redacted = redact_pii(
        json.dumps([str(getattr(msg, "content", msg)) for msg in messages], ensure_ascii=False)
    )
    return hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:16]


def _model_name(model: Any) -> str:
    return str(getattr(model, "model_name", None) or getattr(model, "model", None) or model)


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
        started = time.perf_counter()
        try:
            response = await handler(request)
        except Exception as exc:
            if context is not None:
                context.model_metadata = {
                    "raw_present": False,
                    "raw_content_hash": _hash_messages(request.messages),
                    "parsing_error": str(exc),
                    "model_name": _model_name(request.model),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            raise

        if context is not None:
            context.model_metadata = {
                "raw_present": bool(response.result),
                "raw_content_hash": _hash_messages(response.result),
                "parsing_error": None
                if response.structured_response is not None
                else "missing_structured_response",
                "model_name": _model_name(request.model),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "token_usage": _extract_token_usage(response.result),
            }
        return response

    async def awrap_tool_call(self, request, handler):
        context = _context_from_runtime(request.runtime)
        tool_name = (
            getattr(request.tool, "name", None)
            or request.tool_call.get("name")
            or "unknown_tool"
        )
        started = time.perf_counter()
        result = await handler(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        payload = _json_payload(getattr(result, "content", None))
        if payload is None:
            payload = _json_payload(getattr(result, "artifact", None))

        if context is not None:
            context.evidence_events.append(
                _event(
                    event_type=EventType.TOOL_EXECUTED,
                    request_id=context.request_id,
                    step_name=str(tool_name),
                    summary=f"LangChain tool executed: {tool_name}",
                    metadata={"tool_name": tool_name, "duration_ms": duration_ms},
                )
            )

            if tool_name == "retrieve_workforce_materials" and isinstance(payload, dict):
                records = payload.get("records") or []
                context.rag_contexts = _dedupe_rag_contexts(
                    [
                        *context.rag_contexts,
                        *_safe_rag_contexts_from_records(records),
                    ]
                )
                context.evidence_events.append(
                    _event(
                        event_type=EventType.RAG_RETRIEVED,
                        request_id=context.request_id,
                        step_name=str(tool_name),
                        summary=f"RAG materials retrieved: {len(records)}",
                        metadata={
                            "retrieval_count": len(records),
                            "source_ids": [row.get("source_id") for row in records],
                            "evidence_grades": [row.get("evidence_grade") for row in records],
                            "doc_types": [row.get("doc_type") for row in records],
                            "duration_ms": duration_ms,
                        },
                    )
                )
            if tool_name == "run_contact_onboarding" and isinstance(payload, dict):
                artifact = _contact_onboarding_artifact(payload)
                if artifact:
                    context.contact_artifacts[CONTACT_ONBOARDING_SUB_AGENT] = artifact
            if tool_name == "run_worker_reply_interpreter" and isinstance(payload, dict):
                artifact = _worker_reply_interpreter_artifact(payload)
                if artifact:
                    context.contact_artifacts[WORKER_REPLY_INTERPRETER_SUB_AGENT] = artifact

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


def _extract_token_usage(messages: list[Any]) -> dict[str, Any]:
    for message in messages:
        usage = getattr(message, "usage_metadata", None)
        if isinstance(usage, dict):
            return usage
        response_metadata = getattr(message, "response_metadata", None)
        if isinstance(response_metadata, dict) and isinstance(
            response_metadata.get("token_usage"),
            dict,
        ):
            return response_metadata["token_usage"]
    return {}


def _safe_rag_contexts_from_records(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    safe_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        doc_type = str(record.get("doc_type") or metadata.get("doc_type") or "")
        evidence_grade = str(
            record.get("evidence_grade") or metadata.get("evidence_grade") or ""
        )
        if (
            evidence_grade in DISALLOWED_RAG_EVIDENCE_GRADES
            or doc_type in DISALLOWED_RAG_DOC_TYPES
        ):
            continue
        safe_records.append(
            {
                "source_id": _safe_optional_text(
                    record.get("source_id") or metadata.get("source_id")
                ),
                "title": _safe_optional_text(record.get("title") or metadata.get("title")),
                "doc_type": _safe_optional_text(doc_type),
                "evidence_grade": _safe_optional_text(evidence_grade),
                "collection": _safe_optional_text(record.get("collection")),
                "chunk_id": _safe_optional_text(record.get("chunk_id")),
                "distance": _safe_distance(record.get("distance")),
                "case_type": _safe_optional_text(metadata.get("case_type")),
                "visa_type": _safe_optional_text(metadata.get("visa_type")),
            }
        )
    return _dedupe_rag_contexts(safe_records)


def _dedupe_rag_contexts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (str(record.get("source_id") or ""), str(record.get("chunk_id") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _safe_optional_text(value: Any) -> str:
    if value is None:
        return ""
    return redact_pii(str(value))


def _safe_distance(value: Any) -> float | None:
    if value is None:
        return None


def _contact_onboarding_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("status") or "").upper() != "SUCCESS":
        return {}
    if str(payload.get("approval_required")).lower() in {"false", "0", "none"}:
        return {}
    if str(payload.get("sent") or "").lower() in {"true", "sent", "1"}:
        return {}
    return {
        "status": "SUCCESS",
        "worker_id": payload.get("worker_id"),
        "message_purpose": payload.get("message_purpose"),
        "language_code": payload.get("language_code"),
        "korean_text": payload.get("korean_text"),
        "translated_text": payload.get("translated_text"),
        "approval_required": True,
        "sent": False,
        "sent_at": None,
        "citations": payload.get("citations") or [],
        "risk_flags": payload.get("risk_flags") or [],
        "evidence_events": payload.get("evidence_events") or [],
    }


def _worker_reply_interpreter_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("status") or "").upper() != "SUCCESS":
        return {}
    if str(payload.get("approval_required")).lower() in {"false", "0", "none"}:
        return {}
    if str(payload.get("manager_review_required")).lower() in {"false", "0", "none"}:
        return {}
    if str(payload.get("status_applied") or "").lower() in {"true", "applied", "1"}:
        return {}
    candidates = [
        {**candidate, "is_final": False}
        for candidate in payload.get("status_update_candidates", [])
        if isinstance(candidate, dict)
    ]
    if not candidates:
        return {}
    return {
        "status": "SUCCESS",
        "worker_id": payload.get("worker_id"),
        "language_code": payload.get("language_code"),
        "translated_ko": payload.get("translated_ko"),
        "summary_ko": payload.get("summary_ko"),
        "translation_provider": payload.get("translation_provider"),
        "status_update_candidates": candidates,
        "approval_required": True,
        "manager_review_required": True,
        "status_applied": False,
        "risk_flags": payload.get("risk_flags") or [],
        "evidence_events": payload.get("evidence_events") or [],
    }
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_langchain_v1_middleware() -> Sequence[Any]:
    """LangChain v1 middleware boundary."""

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
        ModelCallLimitMiddleware(run_limit=12),
        ToolCallLimitMiddleware(run_limit=12),
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_worker_message": True,
                "send_expert_package": True,
                "update_case_status_completed": True,
            }
        ),
    ]
