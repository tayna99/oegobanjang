from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agent_runtime.langchain_v1.contact_subagents import (
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
    normalize_contact_subagents_payload,
    run_contact_onboarding_subagent,
    run_worker_reply_interpreter_subagent,
)


CONTACT_CHAT_INTENTS = {
    "document_request_message",
    "contact_onboarding",
    "worker_reply_interpretation",
}


@dataclass(frozen=True)
class AgentChatContactExecution:
    answer: str
    contact_preview: dict[str, Any] | None = None
    contact_subagents: dict[str, Any] = field(default_factory=dict)
    tool_name: str | None = None
    approval_required: bool = True
    execution_allowed: bool = True
    actions_allowed: bool = True
    error: str | None = None


def run_agent_chat_contact_subagent(
    *,
    message: str,
    intent: str,
    entities: dict[str, str] | None = None,
) -> AgentChatContactExecution:
    if intent == "worker_reply_interpretation":
        return _run_worker_reply_interpretation(message=message, entities=entities or {})
    if intent in {"document_request_message", "contact_onboarding"}:
        return _run_contact_onboarding(message=message, intent=intent, entities=entities or {})
    return AgentChatContactExecution(
        answer="다국어 컨택 서브에이전트가 필요한 요청으로 확인되지 않았습니다.",
        execution_allowed=False,
        actions_allowed=False,
        error="UNSUPPORTED_CONTACT_INTENT",
    )


def _run_contact_onboarding(
    *,
    message: str,
    intent: str,
    entities: dict[str, str],
) -> AgentChatContactExecution:
    language_code = _supported_language(entities.get("language") or _infer_language(message))
    message_purpose = _infer_message_purpose(message, default_for_intent=intent)
    result = run_contact_onboarding_subagent(
        worker_id=_worker_id(entities),
        worker_name=_display_worker_name(message, entities),
        language_code=language_code,
        message_purpose=message_purpose,
        user_request=message,
        due_date=_due_date(message),
        contact_person="담당자",
        training_date=_training_date(message),
        training_time=_training_time(message),
        location=_training_location(message),
    )
    contact_subagents = _safe_subagents(CONTACT_ONBOARDING_SUB_AGENT, result)
    preview = {
        "kind": "message_draft",
        "language_code": result.get("language_code", language_code),
        "message_purpose": result.get("message_purpose", message_purpose),
        "status": result.get("status", "SUCCESS"),
        "korean_text": result.get("korean_text"),
        "translated_text": result.get("translated_text"),
        "sent": False,
        "external_send_performed": False,
        "approval_required": True,
    }
    if intent == "document_request_message":
        heading = "다국어 서류 요청 메시지 업무를 확인했고, 컨택 서브에이전트가 발송 전 검토용 초안을 만들었습니다."
        next_step = "누락서류 요청 초안 보기 / 담당자 승인 요청"
    else:
        heading = "다국어 컨택 안내 업무를 확인했고, 컨택 서브에이전트가 발송 전 검토용 메시지 초안을 만들었습니다."
        next_step = "초안 확인 / 담당자 승인 요청"
    answer = "\n".join(
        [
            heading,
            f"- 안내 유형: {_purpose_label(str(preview['message_purpose']))}",
            f"- 언어: {_language_label(str(preview['language_code']))}",
            f"- 다음 처리: {next_step}",
            "문자, 카톡, 외부 발송은 아직 수행하지 않았습니다.",
        ]
    )
    return AgentChatContactExecution(
        answer=answer,
        contact_preview=_drop_empty(preview),
        contact_subagents=contact_subagents,
        tool_name="run_contact_onboarding",
    )


def _run_worker_reply_interpretation(
    *,
    message: str,
    entities: dict[str, str],
) -> AgentChatContactExecution:
    worker_reply = _extract_worker_reply(message)
    if not worker_reply:
        preview = {
            "kind": "worker_reply_summary_required_input",
            "status_applied": False,
            "approval_required": True,
            "required_input": "worker_reply",
        }
        return AgentChatContactExecution(
            answer=(
                "근로자 답변 원문이 필요합니다. "
                "예: 근로자가 'Tôi có hộ chiếu, ảnh mai gửi.'라고 답했는데 요약해줘"
            ),
            contact_preview=preview,
            contact_subagents={},
            approval_required=True,
            execution_allowed=False,
            actions_allowed=False,
            error="WORKER_REPLY_REQUIRED",
        )

    language_code = _supported_language(entities.get("language") or _infer_language(worker_reply))
    result = run_worker_reply_interpreter_subagent(
        worker_id=_worker_id(entities),
        language_code=language_code,
        worker_reply=worker_reply,
        use_llm_translation=False,
    )
    candidates = result.get("status_update_candidates", [])
    candidate_count = len(candidates) if isinstance(candidates, list) else 0
    contact_subagents = _safe_subagents(WORKER_REPLY_INTERPRETER_SUB_AGENT, result)
    preview = {
        "kind": "worker_reply_summary",
        "language_code": result.get("language_code", language_code),
        "summary_ko": result.get("summary_ko"),
        "status_update_candidate_count": candidate_count,
        "status_applied": False,
        "approval_required": True,
        "manager_review_required": True,
    }
    answer = "\n".join(
        [
            "응답 해석 서브에이전트가 근로자 답변을 요약했습니다.",
            f"- 요약: {preview.get('summary_ko') or '담당자 검토용 요약을 생성했습니다.'}",
            f"- 상태 업데이트 후보: {candidate_count}건",
            "- 다음 처리: 후보 검토 / 담당자 승인 후 상태 반영",
            "상태 확정 업데이트와 외부 발송은 아직 수행하지 않았습니다.",
        ]
    )
    return AgentChatContactExecution(
        answer=answer,
        contact_preview=_drop_empty(preview),
        contact_subagents=contact_subagents,
        tool_name="run_worker_reply_interpreter",
    )


def _safe_subagents(subagent: str, result: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_contact_subagents_payload(
        {"contact_subagents": {subagent: result}},
    )
    return payload.get("contact_subagents", {})


def _extract_worker_reply(message: str) -> str | None:
    quoted = re.search(r"['\"“”‘’](.+?)['\"“”‘’]", message)
    if quoted:
        return quoted.group(1).strip() or None
    if ":" in message:
        candidate = message.split(":", 1)[1].strip()
        return candidate or None
    if "：" in message:
        candidate = message.split("：", 1)[1].strip()
        return candidate or None
    return None


def _infer_language(text: str) -> str:
    lowered = text.casefold()
    if "인도네시아" in text or "indonesian" in lowered or "saya " in lowered:
        return "id"
    return "vi"


def _supported_language(value: str | None) -> str:
    return value if value in {"vi", "id"} else "vi"


def _infer_message_purpose(message: str, *, default_for_intent: str) -> str:
    text = message.casefold()
    if "안전교육" in text or "교육" in text or "안전" in text:
        return "safety_training_notice"
    if "상담센터" in text or "상담" in text:
        return "counseling_center_guide"
    if "숙소" in text or "기숙사" in text or "생활" in text:
        return "housing_notice"
    if "외국인등록증" in text or "등록증" in text or "arc" in text:
        return "arc_request"
    if "사진" in text and "여권" not in text:
        return "photo_request"
    if "여권" in text:
        return "passport_request"
    if default_for_intent == "contact_onboarding":
        return "counseling_center_guide"
    return "passport_request"


def _worker_id(entities: dict[str, str]) -> str:
    person_ref = str(entities.get("person_ref") or "worker").lower().replace(".", "")
    if person_ref == "tran":
        return "worker_tran_masked"
    if person_ref == "nguyen":
        return "worker_nguyen_masked"
    return "worker_contact_preview"


def _display_worker_name(message: str, entities: dict[str, str]) -> str | None:
    person_ref = entities.get("person_ref")
    if person_ref:
        return person_ref
    match = re.search(r"([A-Z][A-Za-z.\-]{1,40}|[가-힣A-Za-z]{1,20})(?:한테|에게|께)", message)
    return match.group(1) if match else None


def _due_date(message: str) -> str:
    explicit = _korean_date(message) or _iso_date(message)
    return explicit or "담당자가 안내한 기한"


def _training_date(message: str) -> str:
    return _korean_date(message) or _iso_date(message) or "담당자가 확정한 일정"


def _training_time(message: str) -> str:
    match = re.search(r"(오전|오후)?\s*\d{1,2}\s*시", message)
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip().replace(" 시", "시")
    return "담당자 지정 시간"


def _training_location(message: str) -> str:
    for location in ("교육장", "회의실"):
        if location in message:
            return location
    return "사업장 교육 장소"


def _korean_date(message: str) -> str | None:
    match = re.search(r"\d{1,2}\s*월\s*\d{1,2}\s*일", message)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).replace(" 월", "월").replace(" 일", "일")


def _iso_date(message: str) -> str | None:
    match = re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", message)
    return match.group(0) if match else None


def _purpose_label(purpose: str) -> str:
    labels = {
        "passport_request": "여권 사본 요청",
        "photo_request": "증명사진 요청",
        "arc_request": "외국인등록증 요청",
        "missing_document_request": "서류 보완 요청",
        "safety_training_notice": "안전교육 안내",
        "counseling_center_guide": "상담센터 안내",
        "housing_notice": "생활/숙소 안내",
    }
    return labels.get(purpose, purpose)


def _language_label(language_code: str) -> str:
    labels = {"vi": "베트남어", "id": "인도네시아어"}
    return labels.get(language_code, language_code)


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "")}
