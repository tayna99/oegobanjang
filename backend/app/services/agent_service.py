from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime.agents.multilingual_contact_agent import (
    MessageDraftInput,
    MultilingualContactAgent,
    WorkerReplySummaryInput,
)
from backend.app.agent_runtime.agents.multilingual_contact_input_extractor import (
    extract_multilingual_contact_input,
)
from backend.app.models.evidence import EvidenceLog
from backend.app.services.contact_persistence_service import (
    save_message_draft_result,
    save_worker_reply_summary_result,
)


class AgentRunRequest(BaseModel):
    user_request: str
    input_payload: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    intent: str | None
    task_type: str | None
    plan: dict[str, Any]
    agent_results: dict[str, Any]
    approval: dict[str, Any]
    evidence_events: list[dict[str, Any]]
    risk_flags: list[str]
    final_response: str
    persistence: dict[str, Any] = Field(default_factory=dict)


class ApprovalRuntimeState(BaseModel):
    required: bool = False
    status: str = "NOT_REQUIRED"
    reason: str | None = None


class ContactRuntimeState(BaseModel):
    user_request: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    task_type: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)
    agent_results: dict[str, Any] = Field(default_factory=dict)
    approval: ApprovalRuntimeState = Field(default_factory=ApprovalRuntimeState)
    evidence_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    final_response: str = ""


def run_agent(
    request: AgentRunRequest,
    db: Session | None = None,
) -> AgentRunResponse:
    state = _run_contact_runtime(request)
    persistence = _persist_runtime_output(state, db)
    return AgentRunResponse(
        intent=state.intent,
        task_type=state.task_type,
        plan=state.plan,
        agent_results=state.agent_results,
        approval=state.approval.model_dump(),
        evidence_events=state.evidence_events,
        risk_flags=state.risk_flags,
        final_response=state.final_response,
        persistence=persistence,
    )


def _run_contact_runtime(request: AgentRunRequest) -> ContactRuntimeState:
    extraction = extract_multilingual_contact_input(
        request.user_request,
        request.input_payload,
    )
    payload = dict(extraction.input_payload)
    payload.setdefault("user_request", request.user_request)

    state = ContactRuntimeState(
        user_request=request.user_request,
        input_payload=payload,
        intent=_infer_intent(request.user_request, payload),
        task_type=_infer_task_type(payload),
        risk_flags=_dedupe(extraction.risk_flags + _request_risk_flags(request.user_request)),
    )
    state.plan = _build_plan(state)

    if state.intent != "CONTACT":
        state.agent_results["runtime"] = {
            "status": "FAILED",
            "risk_flags": ["UNSUPPORTED_INTENT"],
            "error": f"Unsupported intent: {state.intent}",
        }
        state.risk_flags = _dedupe(state.risk_flags + ["UNSUPPORTED_INTENT"])
        state.final_response = "요청을 처리하지 못했습니다: CONTACT intent가 필요합니다."
        return state

    agent = MultilingualContactAgent()
    try:
        if state.task_type == "worker_reply_summary":
            result = agent.summarize_worker_reply(
                WorkerReplySummaryInput.model_validate(payload)
            )
        else:
            result = agent.generate_message_draft(
                MessageDraftInput.model_validate(payload)
            )
    except ValidationError as exc:
        state.agent_results["multilingual_contact_agent"] = {
            "status": "FAILED",
            "risk_flags": ["INVALID_CONTACT_INPUT"],
            "error": exc.errors(),
        }
        state.risk_flags = _dedupe(state.risk_flags + ["INVALID_CONTACT_INPUT"])
        state.final_response = f"요청을 처리하지 못했습니다: {exc.errors()}"
        return state

    result_dict = result.model_dump()
    result_dict["risk_flags"] = _dedupe(state.risk_flags + result_dict.get("risk_flags", []))
    state.agent_results["multilingual_contact_agent"] = result_dict
    state.risk_flags = _dedupe(result_dict["risk_flags"])
    state.evidence_events = [
        event for event in result_dict.get("evidence_events", []) if isinstance(event, dict)
    ]

    if result_dict.get("approval_required"):
        state.approval.required = True
        state.approval.status = "PENDING"
        state.approval.reason = "다국어 메시지 발송 또는 상태 업데이트 확정 전 담당자 승인이 필요합니다."

    state.final_response = _build_final_response(result_dict)
    return state


def _infer_intent(user_request: str, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("intent", "")).upper()
    if explicit:
        return explicit
    text = " ".join(
        [
            user_request,
            str(payload.get("task_type", "")),
            str(payload.get("message_purpose", "")),
            str(payload.get("worker_reply", "")),
        ]
    ).lower()
    keywords = ("다국어", "베트남", "인도네시아", "메시지", "안내", "답변", "상담센터", "여권", "사진", "arc")
    return "CONTACT" if any(keyword in text for keyword in keywords) else "UNKNOWN"


def _infer_task_type(payload: dict[str, Any]) -> str:
    task_type = payload.get("task_type")
    if task_type in {"message_draft", "worker_reply_summary"}:
        return str(task_type)
    if payload.get("worker_reply"):
        return "worker_reply_summary"
    return "message_draft"


def _request_risk_flags(user_request: str) -> list[str]:
    text = user_request.lower()
    flags: list[str] = []
    if any(keyword in text for keyword in ("바로 발송", "보내줘", "전송해줘", "send now", "send immediately")):
        flags.append("APPROVAL_REQUIRED_FOR_SEND")
    if any(keyword in text for keyword in ("확답", "확정", "가능하다고")) and "비자" in text:
        flags.append("LEGAL_CERTAINTY_NOT_ALLOWED")
    return flags


def _build_plan(state: ContactRuntimeState) -> dict[str, Any]:
    return {
        "intent": state.intent,
        "task_type": state.task_type,
        "required_agents": ["multilingual_contact_agent"] if state.intent == "CONTACT" else [],
        "steps": [
            "extract_contact_input",
            "run_multilingual_contact_agent",
            "collect_evidence_event_candidates",
            "prepare_final_response",
        ]
        if state.intent == "CONTACT"
        else ["prepare_final_response"],
        "approval_required": state.intent == "CONTACT",
    }


def _build_final_response(result: dict[str, Any]) -> str:
    if result.get("status") != "SUCCESS":
        return f"요청을 처리하지 못했습니다: {result.get('error')}"

    lines: list[str] = []
    if result.get("korean_text") is not None:
        lines.extend(
            [
                "다국어 메시지 초안을 생성했습니다.",
                "",
                "[한국어 원문]",
                str(result.get("korean_text") or ""),
                "",
                "[번역 초안]",
                str(result.get("translated_text") or ""),
            ]
        )
    elif result.get("summary_ko") is not None:
        lines.extend(
            [
                "근로자 답변 요약과 상태 업데이트 후보를 생성했습니다.",
                "",
                "[요약]",
                str(result.get("summary_ko") or ""),
                "",
                "[상태 업데이트 후보]",
            ]
        )
        for candidate in result.get("status_update_candidates", []):
            if isinstance(candidate, dict):
                lines.append(f"- {candidate.get('candidate_type')}: {candidate.get('summary')}")

    if result.get("citations"):
        lines.extend(["", "[공식 근거 후보]"])
        for citation in result["citations"]:
            lines.append(f"- {citation.get('citation_label')}")

    if result.get("approval_required"):
        lines.extend(["", "실제 발송 또는 상태 확정 전 담당자 승인이 필요합니다."])

    if result.get("risk_flags"):
        lines.extend(["", f"risk_flags: {', '.join(result['risk_flags'])}"])

    return "\n".join(lines).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _persist_runtime_output(state: Any, db: Session | None) -> dict[str, Any]:
    persist_requested = state.input_payload.get("persist_result") is True
    if not persist_requested:
        return _not_persisted("persist_result is not true")

    if db is None:
        return _not_persisted("db session is not available")

    if state.intent != "CONTACT":
        return _not_persisted("intent is not CONTACT")

    if (
        state.task_type in {"message_draft", "worker_reply_summary"}
        and not state.input_payload.get("worker_id")
    ):
        return _not_persisted("worker_id is required for persistence")

    result = state.agent_results.get("multilingual_contact_agent") or {}
    if result.get("status") != "SUCCESS":
        return _not_persisted("agent result is not successful")

    try:
        if state.task_type == "message_draft":
            return _persist_message_draft(state, result, db)
        if state.task_type == "worker_reply_summary":
            return _persist_worker_reply_summary(state, result, db)
        return _not_persisted("unsupported task_type")
    except Exception as exc:
        db.rollback()
        return {
            "enabled": True,
            "saved": False,
            "reason": "persistence_error",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _persist_message_draft(
    state: Any,
    result: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    message = save_message_draft_result(
        db,
        agent_result=result,
        worker_id=state.input_payload.get("worker_id") or result.get("worker_id"),
        created_by=state.input_payload.get("created_by"),
        request_id=state.input_payload.get("request_id"),
    )
    db.commit()
    evidence_log_ids = _evidence_log_ids(
        db,
        contact_message_id=message.id,
        approval_id=message.approval_id,
    )
    return {
        "enabled": True,
        "saved": True,
        "contact_message_id": message.id,
        "approval_id": message.approval_id,
        "evidence_log_ids": evidence_log_ids,
    }


def _persist_worker_reply_summary(
    state: Any,
    result: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=result,
        worker_id=state.input_payload.get("worker_id") or result["worker_id"],
        request_id=state.input_payload.get("request_id"),
        source_message_id=state.input_payload.get("source_message_id"),
        requested_by=state.input_payload.get("created_by"),
        worker_reply=state.input_payload.get("worker_reply"),
    )
    db.commit()
    candidate_ids = [candidate.id for candidate in candidates]
    approval_ids = [candidate.approval_id for candidate in candidates if candidate.approval_id]
    evidence_log_ids = _evidence_log_ids(
        db,
        status_update_candidate_ids=candidate_ids,
        approval_ids=approval_ids,
    )
    return {
        "enabled": True,
        "saved": True,
        "status_update_candidate_ids": candidate_ids,
        "approval_ids": approval_ids,
        "evidence_log_ids": evidence_log_ids,
    }


def _evidence_log_ids(
    db: Session,
    *,
    contact_message_id: str | None = None,
    approval_id: str | None = None,
    status_update_candidate_ids: list[str] | None = None,
    approval_ids: list[str] | None = None,
) -> list[str]:
    stmt = select(EvidenceLog.id)
    if contact_message_id:
        stmt = stmt.where(EvidenceLog.contact_message_id == contact_message_id)
    if approval_id:
        stmt = stmt.where(EvidenceLog.approval_id == approval_id)
    if status_update_candidate_ids:
        stmt = stmt.where(
            EvidenceLog.status_update_candidate_id.in_(status_update_candidate_ids)
        )
    if approval_ids:
        stmt = stmt.where(EvidenceLog.approval_id.in_(approval_ids))
    return list(db.scalars(stmt).all())


def _not_persisted(reason: str) -> dict[str, Any]:
    return {
        "enabled": False,
        "saved": False,
        "reason": reason,
    }
