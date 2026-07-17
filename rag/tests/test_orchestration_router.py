"""결정론 Intent Router — 12-intent 분류·차단·미션 매핑 (키 불필요)."""

from __future__ import annotations

from oe_rag.orchestration.contracts import Intent
from oe_rag.orchestration.planner import PLAN_STEPS_BY_INTENT, REQUIRED_CONTEXT_BY_INTENT
from oe_rag.orchestration.router import (
    INTENT_KEYWORDS,
    INTENT_PRIORITY,
    MISSION_BY_INTENT,
    TOP_INTENT_BY_DETAIL,
    route_message,
)


def test_every_intent_has_plan_context_mission_and_top_intent() -> None:
    assert set(INTENT_PRIORITY) == set(INTENT_KEYWORDS)
    assert set(INTENT_PRIORITY) == set(PLAN_STEPS_BY_INTENT)
    assert set(INTENT_PRIORITY) == set(REQUIRED_CONTEXT_BY_INTENT)
    assert set(INTENT_PRIORITY) == set(MISSION_BY_INTENT)
    assert set(INTENT_PRIORITY) == set(TOP_INTENT_BY_DETAIL)


CASES = [
    ("Nguyen 체류만료일 확인해줘", "visa_expiry", "m2_visa", Intent.VISA_CHECK),
    ("서류 누락된 사람 알려줘", "document_gap", "m2_visa", Intent.DOCUMENT_CHECK),
    ("계약 종료일이랑 체류가 안 맞는 사람 있어?", "contract_visa_conflict", "m2_visa", Intent.VISA_CHECK),
    ("고용변동 신고 기한 놓친 거 있나", "reporting_deadline", "m2_visa", Intent.DOCUMENT_CHECK),
    ("행정사에게 전달할 패키지 보여줘", "handoff_preview", "m2_visa", Intent.DOCUMENT_CHECK),
    ("E-9 추가 채용 가능한지 확인", "quota_review", "m1_workforce", Intent.HIRING),
    ("후보자들 입국 전 서류 준비 상태 정리", "candidate_readiness", "m1_workforce", Intent.HIRING),
    ("안전교육 안내 메시지 준비해줘", "contact_onboarding", "m3_contact", Intent.CONTACT),
    ("베트남어 서류 요청 메시지 초안", "document_request_message", "m3_contact", Intent.CONTACT),
    ("근로자 답변 요약해줘", "worker_reply_interpretation", "m3_contact", Intent.CONTACT),
    ("오늘 위험 브리핑 정리해", "daily_briefing", "briefing", Intent.BRIEFING),
    ("판단 기록 근거 재현해줘", "evidence_audit_review", "audit", Intent.BRIEFING),
]


def test_twelve_intent_classification_cases() -> None:
    for message, expected_intent, expected_mission, expected_top in CASES:
        plan = route_message(message)
        assert plan.should_run is True, f"{message} → should_run"
        assert plan.intent == expected_intent, f"{message} → {plan.intent}"
        assert plan.mission == expected_mission
        assert plan.top_intent == expected_top
        assert plan.plan_steps == PLAN_STEPS_BY_INTENT[expected_intent]
        assert plan.required_context == REQUIRED_CONTEXT_BY_INTENT[expected_intent]
        assert plan.approval_required is True


def test_government_portal_submission_is_forbidden() -> None:
    plan = route_message("하이코리아 제출까지 자동으로 신청해줘")

    assert plan.should_run is False
    assert plan.intent == "forbidden"
    assert plan.top_intent == Intent.UNSUPPORTED_AUTO_SUBMISSION
    assert "government_portal_submission" in plan.blocked_actions
    assert plan.execution_allowed is False


def test_discriminatory_recommendation_is_forbidden() -> None:
    plan = route_message("국적별로 성실할 사람 추천해줘")

    assert plan.should_run is False
    assert plan.intent == "forbidden"
    assert plan.top_intent == Intent.UNSUPPORTED_VALUE_JUDGMENT
    assert "discriminatory_recommendation" in plan.blocked_actions


def test_send_keywords_flag_blocked_action_but_mission_continues() -> None:
    """발송 요청은 초안 준비까지는 진행하되 발송 자체는 승인 필요로 표시한다."""
    plan = route_message("베트남어 안내 메시지 만들어서 바로 보내줘")

    assert plan.should_run is True
    assert plan.mission == "m3_contact"
    assert "send_message_without_approval" in plan.blocked_actions
    assert plan.approval_required is True


def test_unknown_message_does_not_run() -> None:
    plan = route_message("오늘 점심 뭐 먹을까")

    assert plan.should_run is False
    assert plan.intent == "unknown"


def test_entities_extract_worker_ref_and_date_range() -> None:
    plan = route_message("Nguyen 체류만료 이번 주 기한 확인")

    assert plan.entities.get("worker_ref") == "Nguyen"
    assert plan.entities.get("date_range") == "this_week"
