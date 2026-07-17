"""Intent Router(결정론 정본) — legacy services/daily_briefing_planner.py 이식.

발표 p.16: "Intent Router — Bounded intent 정규화. LLM은 router 1회만, 라우팅 매핑은
코드로." 키워드 분류가 **정본 폴백**이고(OPENAI_API_KEY 없이 동작), LLM 구조화 출력은
있으면 향상으로 얹는다(G3의 /intent 엔드포인트).

12개 세부 업무 intent → 미션 매핑(dict)까지 코드로 고정한다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .contracts import Intent

# 세부 업무 intent 12종별 키워드 사전 — legacy INTENT_KEYWORDS 그대로.
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "worker_reply_interpretation": (
        "근로자 답변",
        "답변 보고",
        "답했는데",
        "요약해줘",
        "상태 업데이트",
        "상태 반영",
    ),
    "contact_onboarding": (
        "안전교육 일정",
        "안전교육 안내",
        "교육 일정",
        "교육 안내",
        "상담센터 안내",
        "숙소 안내",
        "생활 안내",
        "온보딩",
    ),
    "document_request_message": (
        "다국어 서류 요청",
        "서류 요청 메시지",
        "요청메시지",
        "메시지 만들어",
        "요청 메시지 생성",
        "메시지 초안",
        "서류 요청 초안",
        "안내 메시지",
        "안내문",
        "베트남어",
        "네팔어",
        "번역",
    ),
    "candidate_readiness": (
        "후보자들",
        "후보자 요건",
        "후보자 서류",
        "후보자 준비",
        "입국 전에",
        "입국 전 서류",
        "요건 매칭",
        "후보자 매칭",
    ),
    "evidence_audit_review": (
        "감사 로그",
        "감사로그",
        "근거 재현",
        "판단 기록",
        "근거 확인",
        "audit review",
    ),
    "contract_visa_conflict": (
        "contract visa conflict",
        "계약-체류",
        "계약 체류",
        "계약 종료일",
        "계약 끝나는",
        "계약종료",
        "안 맞는",
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
        "채용",
        "인원",
        "티오",
        "신규 고용",
        "추가 채용",
        "고용 가능한지",
        "채용 준비",
    ),
    "handoff_preview": (
        "handoff",
        "handoff preview",
        "행정사 검토",
        "행정사에게 전달",
        "행정사 패키지",
        "검토 패키지",
        "전달 패키지",
        "전달할 패키지",
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
        "현황",
        "기한 임박",
        "임박 건",
        "이번 주 기한",
        "이번주 기한",
        "오늘 위험",
        "위험 브리핑",
        "급한 케이스",
        "정리해",
        "리스크",
    ),
}

# 구체적 intent가 일반적 intent보다 먼저 매칭되도록 하는 우선순위 — legacy INTENT_PRIORITY.
INTENT_PRIORITY: tuple[str, ...] = (
    "worker_reply_interpretation",
    "contact_onboarding",
    "document_request_message",
    "candidate_readiness",
    "evidence_audit_review",
    "contract_visa_conflict",
    "reporting_deadline",
    "handoff_preview",
    "document_gap",
    "visa_expiry",
    "quota_review",
    "daily_briefing",
)

# 자동 실행 차단 키워드 — legacy BLOCKED_ACTION_KEYWORDS.
BLOCKED_ACTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "discriminatory_recommendation": (
        "국적별 추천",
        "국적별로 추천",
        "국적별로 성실",
        "국적 선호",
        "성실할 사람 추천",
        "이탈 가능성",
        "국적별 점수",
        "국적별 순위",
        "나라별 추천",
    ),
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

# 세부 intent → 미션 매핑 (발표 p.15 "에이전트 3개" 라우팅 — LLM 아님, 코드 dict).
MISSION_BY_INTENT: dict[str, str] = {
    "quota_review": "m1_workforce",
    "candidate_readiness": "m1_workforce",
    "visa_expiry": "m2_visa",
    "document_gap": "m2_visa",
    "contract_visa_conflict": "m2_visa",
    "reporting_deadline": "m2_visa",
    "handoff_preview": "m2_visa",
    "contact_onboarding": "m3_contact",
    "document_request_message": "m3_contact",
    "worker_reply_interpretation": "m3_contact",
    "daily_briefing": "briefing",
    "evidence_audit_review": "audit",
}

# 세부 intent → 상위 Intent enum (LLM 구조화 출력·evidence 기록용).
TOP_INTENT_BY_DETAIL: dict[str, Intent] = {
    "quota_review": Intent.HIRING,
    "candidate_readiness": Intent.HIRING,
    "visa_expiry": Intent.VISA_CHECK,
    "contract_visa_conflict": Intent.VISA_CHECK,
    "document_gap": Intent.DOCUMENT_CHECK,
    "reporting_deadline": Intent.DOCUMENT_CHECK,
    "handoff_preview": Intent.DOCUMENT_CHECK,
    "contact_onboarding": Intent.CONTACT,
    "document_request_message": Intent.CONTACT,
    "worker_reply_interpretation": Intent.CONTACT,
    "daily_briefing": Intent.BRIEFING,
    "evidence_audit_review": Intent.BRIEFING,
}

# 차단 사유 → UNSUPPORTED_* 상위 Intent.
BLOCKED_TOP_INTENT: dict[str, Intent] = {
    "discriminatory_recommendation": Intent.UNSUPPORTED_VALUE_JUDGMENT,
    "government_portal_submission": Intent.UNSUPPORTED_AUTO_SUBMISSION,
}


class RoutePlan(BaseModel):
    """라우팅 결과 계약 — legacy DailyBriefingPlan을 일반화 이식."""

    should_run: bool
    intent: str | None = None
    mission: str | None = None
    top_intent: Intent | None = None
    plan_steps: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    entities: dict[str, str] = Field(default_factory=dict)
    blocked_actions: list[str] = Field(default_factory=list)
    approval_required: bool = True
    execution_allowed: bool = False


def route_message(message: str) -> RoutePlan:
    """자연어 요청 → 결정론 라우팅 (legacy plan_daily_briefing_from_message 이식).

    forbidden(차별 추천·정부포털 제출) 감지 시 실행 자체를 차단하고,
    발송·전달류 차단 키워드는 blocked_actions로만 표시한다(미션은 계속 — 초안까지는 준비).
    """
    from .planner import PLAN_STEPS_BY_INTENT, REQUIRED_CONTEXT_BY_INTENT

    normalized = message.casefold()
    blocked = _blocked_actions(normalized)
    if "government_portal_submission" in blocked or "discriminatory_recommendation" in blocked:
        forbidden_reason = (
            "government_portal_submission"
            if "government_portal_submission" in blocked
            else "discriminatory_recommendation"
        )
        return RoutePlan(
            should_run=False,
            intent="forbidden",
            top_intent=BLOCKED_TOP_INTENT[forbidden_reason],
            blocked_actions=blocked,
            approval_required=True,
            execution_allowed=False,
        )

    intent = classify_intent(normalized)
    if intent is None:
        return RoutePlan(
            should_run=False,
            intent="unknown",
            blocked_actions=blocked,
            approval_required=True,
            execution_allowed=False,
        )

    return RoutePlan(
        should_run=True,
        intent=intent,
        mission=MISSION_BY_INTENT[intent],
        top_intent=TOP_INTENT_BY_DETAIL[intent],
        plan_steps=PLAN_STEPS_BY_INTENT[intent],
        required_context=REQUIRED_CONTEXT_BY_INTENT[intent],
        entities=_extract_lightweight_entities(message),
        blocked_actions=blocked,
        approval_required=True,
        execution_allowed=True,
    )


def classify_intent(normalized_message: str) -> str | None:
    for intent in INTENT_PRIORITY:
        keywords = INTENT_KEYWORDS[intent]
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
    if "이번 주" in message or "이번주" in message or "this week" in message.casefold():
        entities["date_range"] = "this_week"
    elif "이번 달" in message or "this month" in message.casefold():
        entities["date_range"] = "this_month"
    return entities
