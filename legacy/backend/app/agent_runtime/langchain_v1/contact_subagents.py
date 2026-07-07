from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.tools import tool

from app.agent_runtime.agents.multilingual_contact_agent import (
    MessageDraftInput,
    MultilingualContactAgent,
    WorkerReplySummaryInput,
)
from app.agent_runtime.translation.translator import LLMTranslationProvider


CONTACT_ONBOARDING_SUB_AGENT = "contact_onboarding_subagent"
WORKER_REPLY_INTERPRETER_SUB_AGENT = "worker_reply_interpreter_subagent"
CONTACT_SUB_AGENT_NAMES = {
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
}
_ALIEN_REGISTRATION_RE = re.compile(r"\b\d{6}-[1-4]\d{6}\b")
_PHONE_RE = re.compile(r"\b(?:010-\d{4}-\d{4}|010\d{8})\b")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")
_UNSAFE_SUMMARY_KEYS = {
    "worker_id",
    "worker_name",
    "worker_reply",
    "translated_ko",
    "korean_text",
    "translated_text",
    "message_body",
    "draft",
    "content",
    "passport_number",
    "alien_registration_number",
    "phone",
    "address",
    "sent",
    "status_applied",
    "expert_handoff_sent",
    "government_submission",
}


def run_contact_onboarding_subagent(
    *,
    worker_id: str,
    language_code: str,
    message_purpose: str,
    user_request: str,
    due_date: str | None = None,
    contact_person: str = "담당자",
    training_date: str | None = None,
    training_time: str | None = None,
    location: str | None = None,
    worker_name: str | None = None,
) -> dict[str, Any]:
    """Create a worker-facing multilingual draft without sending it."""

    agent = MultilingualContactAgent()
    result = agent.generate_message_draft(
        MessageDraftInput(
            worker_id=worker_id,
            language_code=language_code,  # type: ignore[arg-type]
            message_purpose=message_purpose,
            due_date=due_date,
            contact_person=contact_person,
            user_request=user_request,
            training_date=training_date,
            training_time=training_time,
            location=location,
            worker_name=worker_name,
        )
    )
    payload = result.model_dump()
    payload.update(
        {
            "sub_agent": CONTACT_ONBOARDING_SUB_AGENT,
            "tool_name": "run_contact_onboarding",
            "tool_grade": "SAFE_DRAFT",
            "approval_required": True,
            "sent": False,
        }
    )
    return payload


def run_worker_reply_interpreter_subagent(
    *,
    worker_id: str,
    language_code: str,
    worker_reply: str,
    use_llm_translation: bool = False,
) -> dict[str, Any]:
    """Translate/summarize a worker reply and propose non-final status candidates."""

    translation_provider = LLMTranslationProvider() if use_llm_translation else None
    agent = MultilingualContactAgent(translation_provider=translation_provider)
    result = agent.summarize_worker_reply(
        WorkerReplySummaryInput(
            worker_id=worker_id,
            language_code=language_code,  # type: ignore[arg-type]
            worker_reply=worker_reply,
        )
    )
    payload = result.model_dump()
    payload["status_update_candidates"] = [
        {**candidate, "is_final": False}
        for candidate in payload.get("status_update_candidates", [])
        if isinstance(candidate, dict)
    ]
    payload.update(
        {
            "sub_agent": WORKER_REPLY_INTERPRETER_SUB_AGENT,
            "tool_name": "run_worker_reply_interpreter",
            "tool_grade": "SAFE_DRAFT",
            "approval_required": True,
            "manager_review_required": True,
            "status_applied": False,
        }
    )
    payload["evidence_events"] = _sanitize_evidence_events(
        payload.get("evidence_events", []),
        forbidden_texts=[worker_reply, str(payload.get("translated_ko") or "")],
    )
    return payload


@tool
def run_contact_onboarding(
    worker_id: str,
    language_code: str,
    message_purpose: str,
    user_request: str,
    due_date: str | None = None,
    contact_person: str = "담당자",
    training_date: str | None = None,
    training_time: str | None = None,
    location: str | None = None,
    worker_name: str | None = None,
) -> dict[str, Any]:
    """Create a multilingual worker-facing message draft through the Contact Onboarding Sub-Agent. Does not send."""

    return run_contact_onboarding_subagent(
        worker_id=worker_id,
        language_code=language_code,
        message_purpose=message_purpose,
        user_request=user_request,
        due_date=due_date,
        contact_person=contact_person,
        training_date=training_date,
        training_time=training_time,
        location=location,
        worker_name=worker_name,
    )


@tool
def run_worker_reply_interpreter(
    worker_id: str,
    language_code: str,
    worker_reply: str,
    use_llm_translation: bool = False,
) -> dict[str, Any]:
    """Translate/summarize a worker reply and create review-only status update candidates. Does not update status."""

    return run_worker_reply_interpreter_subagent(
        worker_id=worker_id,
        language_code=language_code,
        worker_reply=worker_reply,
        use_llm_translation=use_llm_translation,
    )


def summarize_contact_subagent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sub_agent = str(payload.get("sub_agent") or "")
    summary: dict[str, Any] = {
        "status": _execution_status(payload.get("status")),
        "approval_required": bool(payload.get("approval_required", True)),
        "approval_status": _approval_status(payload),
        "risk_flags": payload.get("risk_flags", []),
    }
    if sub_agent == WORKER_REPLY_INTERPRETER_SUB_AGENT:
        summary["manager_review_required"] = bool(
            payload.get("manager_review_required", True)
        )
        summary["status_update_candidate_count"] = len(
            payload.get("status_update_candidates", [])
        )
    return summary


def normalize_contact_subagents_payload(
    domain_payload: dict[str, Any],
) -> dict[str, Any]:
    """Normalize contact sub-agent summaries to a safe dict shape."""

    if not isinstance(domain_payload, dict):
        return {}

    raw = domain_payload.get("contact_subagents")
    if raw is None:
        return domain_payload

    normalized: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = [(_infer_sub_agent_name(item, idx), item) for idx, item in enumerate(raw)]
    else:
        domain_payload.pop("contact_subagents", None)
        return domain_payload

    for key, value in items:
        if not isinstance(value, dict):
            continue
        sub_agent = _normalize_sub_agent_name(str(value.get("sub_agent") or key))
        if sub_agent not in CONTACT_SUB_AGENT_NAMES:
            continue
        normalized[sub_agent] = _safe_contact_summary(sub_agent, value)

    domain_payload["contact_subagents"] = normalized
    return domain_payload


def _safe_contact_summary(sub_agent: str, payload: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "status": _execution_status(payload.get("status")),
        "approval_required": bool(payload.get("approval_required", True)),
        "approval_status": _approval_status(payload),
        "risk_flags": [
            str(flag)
            for flag in payload.get("risk_flags", [])
            if _safe_scalar(str(flag))
        ],
    }
    if sub_agent == WORKER_REPLY_INTERPRETER_SUB_AGENT:
        summary["manager_review_required"] = bool(
            payload.get("manager_review_required", True)
        )
        summary["status_update_candidate_count"] = _candidate_count(payload)
    elif "manager_review_required" in payload:
        summary["manager_review_required"] = bool(payload.get("manager_review_required"))
    return summary


def _execution_status(value: Any) -> str:
    status = str(value or "SUCCESS").upper()
    if status == "FAILED":
        return "FAILED"
    if status == "PENDING":
        return "SUCCESS"
    return "SUCCESS" if status not in {"SUCCESS", "FAILED"} else status


def _approval_status(payload: dict[str, Any]) -> str:
    status = payload.get("approval_status")
    if not status and str(payload.get("status") or "").upper() == "PENDING":
        status = "PENDING"
    if not status and payload.get("approval_required", True):
        status = "PENDING"
    return str(status or "NOT_REQUIRED").upper()


def _candidate_count(payload: dict[str, Any]) -> int:
    explicit = payload.get("status_update_candidate_count")
    if isinstance(explicit, int):
        return max(explicit, 0)
    candidates = payload.get("status_update_candidates")
    if isinstance(candidates, list):
        return len(candidates)
    return 0


def _infer_sub_agent_name(item: Any, idx: int) -> str:
    if isinstance(item, dict):
        raw = str(
            item.get("sub_agent")
            or item.get("name")
            or item.get("agent")
            or item.get("tool_name")
            or ""
        )
        normalized = _normalize_sub_agent_name(raw)
        if normalized in CONTACT_SUB_AGENT_NAMES:
            return normalized
        if (
            "status_update_candidate_count" in item
            or "status_update_candidates" in item
            or "manager_review_required" in item
        ) and idx > 0:
            return WORKER_REPLY_INTERPRETER_SUB_AGENT
    return (
        CONTACT_ONBOARDING_SUB_AGENT
        if idx == 0
        else WORKER_REPLY_INTERPRETER_SUB_AGENT
    )


def _normalize_sub_agent_name(value: str) -> str:
    if value in CONTACT_SUB_AGENT_NAMES:
        return value
    if value == "run_contact_onboarding":
        return CONTACT_ONBOARDING_SUB_AGENT
    if value == "run_worker_reply_interpreter":
        return WORKER_REPLY_INTERPRETER_SUB_AGENT
    return value


def _safe_scalar(value: str) -> bool:
    if _ALIEN_REGISTRATION_RE.search(value):
        return False
    if _PHONE_RE.search(value):
        return False
    if _PASSPORT_RE.search(value):
        return False
    return not any(key in value for key in _UNSAFE_SUMMARY_KEYS)


def _sanitize_evidence_events(
    events: Any,
    *,
    forbidden_texts: list[str],
) -> list[dict[str, Any]]:
    safe_events = [event for event in events if isinstance(event, dict)]
    serialized = json.dumps(safe_events, ensure_ascii=False)
    for text in forbidden_texts:
        if text and text in serialized:
            return [
                {
                    "event_type": "worker_reply_summarized",
                    "agent_name": "multilingual_contact_agent",
                    "summary": (
                        "근로자 답변을 번역 및 요약했습니다. 원문과 번역 전문은 "
                        "Evidence Log 후보에 저장하지 않습니다."
                    ),
                    "source_ids": [],
                    "approval_required": True,
                },
                {
                    "event_type": "status_update_candidate_created",
                    "agent_name": "multilingual_contact_agent",
                    "summary": "서류/상태 업데이트 후보를 생성했습니다. 확정 업데이트는 수행하지 않았습니다.",
                    "source_ids": [],
                    "approval_required": True,
                },
                {
                    "event_type": "approval_requested",
                    "agent_name": "multilingual_contact_agent",
                    "summary": "상태 업데이트 후보는 담당자 검토 후 확정할 수 있습니다.",
                    "source_ids": [],
                    "approval_required": True,
                },
            ]
    return safe_events
