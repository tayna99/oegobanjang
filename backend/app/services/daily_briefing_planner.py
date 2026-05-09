from __future__ import annotations

from pydantic import BaseModel, Field


class DailyBriefingPlan(BaseModel):
    should_run: bool
    intent: str | None = None
    plan_steps: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    entities: dict[str, str] = Field(default_factory=dict)
    blocked_actions: list[str] = Field(default_factory=list)
    approval_required: bool = True
    execution_allowed: bool = False
    target_service: str | None = None


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "contract_visa_conflict": (
        "contract visa conflict",
        "계약-체류",
        "계약 체류",
        "계약 종료일",
        "계약종료",
        "겹치는",
        "충돌",
    ),
    "reporting_deadline": (
        "reporting deadline",
        "고용변동",
        "신고 기한",
        "신고기한",
        "신고",
        "기한 놓친",
    ),
    "quota_review": (
        "quota",
        "쿼터",
        "e-9",
        "신규 고용",
        "추가 채용",
        "고용 가능한지",
        "채용 준비",
    ),
    "handoff_preview": (
        "handoff",
        "handoff preview",
        "행정사 검토",
        "행정사 패키지",
        "검토 패키지",
        "전달 패키지",
    ),
    "document_gap": (
        "document gap",
        "missing document",
        "서류",
        "누락",
        "빠진",
        "빠진 거",
        "서류 점검",
    ),
    "visa_expiry": (
        "visa expiry",
        "비자",
        "체류만료",
        "체류 만료",
        "갱신",
        "만료일",
    ),
    "daily_briefing": (
        "daily briefing",
        "브리핑",
        "오늘 위험",
        "위험 브리핑",
        "급한 케이스",
        "정리해",
        "리스크",
    ),
}


PLAN_STEPS_BY_INTENT: dict[str, list[str]] = {
    "daily_briefing": [
        "load_company_worker_document_state",
        "evaluate_rule_based_daily_risks",
        "validate_citations",
        "create_pending_next_actions",
        "return_approval_ready_briefing",
    ],
    "visa_expiry": [
        "resolve_worker_reference",
        "load_worker_state",
        "evaluate_visa_expiry",
        "check_missing_renewal_documents",
        "create_pending_next_actions",
    ],
    "document_gap": [
        "load_company_worker_document_state",
        "evaluate_missing_required_documents",
        "create_document_request_actions",
        "return_approval_ready_briefing",
    ],
    "contract_visa_conflict": [
        "load_worker_contract_and_visa_dates",
        "evaluate_contract_visa_conflict",
        "flag_expert_review_if_needed",
        "create_pending_next_actions",
    ],
    "reporting_deadline": [
        "load_reporting_events",
        "evaluate_reporting_deadlines",
        "flag_overdue_or_urgent_reports",
        "create_pending_next_actions",
    ],
    "quota_review": [
        "load_company_quota_state",
        "evaluate_quota_review_need",
        "prepare_readiness_checklist",
        "create_pending_next_actions",
    ],
    "handoff_preview": [
        "resolve_case_or_worker_reference",
        "load_risk_and_citation_context",
        "create_handoff_preview",
        "return_internal_preview_only",
    ],
}


REQUIRED_CONTEXT_BY_INTENT: dict[str, list[str]] = {
    "daily_briefing": ["company", "workers", "documents", "citations", "approvals"],
    "visa_expiry": ["company", "workers", "documents", "citations"],
    "document_gap": ["company", "workers", "documents", "citations"],
    "contract_visa_conflict": ["company", "workers", "contracts", "citations"],
    "reporting_deadline": ["company", "workers", "reporting_events", "citations"],
    "quota_review": ["company", "quota", "workers", "citations"],
    "handoff_preview": ["company", "cases", "actions", "citations", "approvals"],
}


BLOCKED_ACTION_KEYWORDS = {
    "send_message_without_approval": (
        "카톡",
        "문자",
        "발송",
        "바로 보내",
        "바로 전송",
        "send now",
    ),
    "external_handoff_without_approval": (
        "행정사에게 보내",
        "노무사에게 보내",
        "바로 전달",
        "즉시 전달",
    ),
    "government_portal_submission": (
        "정부 포털",
        "정부24 제출",
        "하이코리아 제출",
        "포털 제출",
        "자동 제출",
        "신청해",
    ),
}


def plan_daily_briefing_from_message(message: str) -> DailyBriefingPlan:
    normalized = message.casefold()
    blocked_actions = _blocked_actions(normalized)
    if "government_portal_submission" in blocked_actions:
        return DailyBriefingPlan(
            should_run=False,
            intent="forbidden",
            blocked_actions=blocked_actions,
            approval_required=True,
            execution_allowed=False,
        )

    intent = _classify_intent(normalized)
    if intent is None:
        return DailyBriefingPlan(
            should_run=False,
            intent="unknown",
            blocked_actions=blocked_actions,
            approval_required=True,
            execution_allowed=False,
        )

    return DailyBriefingPlan(
        should_run=True,
        intent=intent,
        plan_steps=PLAN_STEPS_BY_INTENT[intent],
        required_context=REQUIRED_CONTEXT_BY_INTENT[intent],
        entities=_extract_lightweight_entities(message),
        blocked_actions=blocked_actions,
        approval_required=True,
        execution_allowed=True,
        target_service="daily_briefing",
    )


def _classify_intent(normalized_message: str) -> str | None:
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.casefold() in normalized_message for keyword in keywords):
            return intent
    return None


def _blocked_actions(normalized_message: str) -> list[str]:
    return [
        action
        for action, keywords in BLOCKED_ACTION_KEYWORDS.items()
        if any(keyword.casefold() in normalized_message for keyword in keywords)
    ]


def _extract_lightweight_entities(message: str) -> dict[str, str]:
    entities: dict[str, str] = {}
    for token in message.replace(",", " ").split():
        if token and token[0].isupper() and token.isascii():
            entities.setdefault("worker_ref", token)
            break
    if "이번 달" in message or "this month" in message.casefold():
        entities["date_range"] = "this_month"
    return entities
