"""agent_dispatcher.py: 인텐트 기반으로 3개 메인 에이전트를 실제 호출해 답변을 생성한다.

인텐트 → 에이전트 매핑:
  visa_expiry / document_gap / contract_visa_conflict → visa_agent (run_visa_agent)
  document_request_message                            → multilingual_contact_agent
  quota_review / candidate_readiness / reporting_deadline / handoff_preview → hiring_agent (run_hiring_agent)
  daily_briefing / evidence_audit_review / 기타        → 디스패치 없음 (skipped=True)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.agent_runtime.schemas import ForeignHiringState

logger = logging.getLogger(__name__)

VISA_INTENTS = {"visa_expiry", "document_gap", "contract_visa_conflict"}
MULTILINGUAL_INTENTS = {"document_request_message"}
HIRING_INTENTS = {"quota_review", "candidate_readiness", "reporting_deadline", "handoff_preview"}

# 인텐트별 한국어 레이블 (응답 텍스트 조합용)
_INTENT_KO = {
    "visa_expiry": "비자/체류기간",
    "document_gap": "서류 누락",
    "contract_visa_conflict": "계약-체류기간 충돌",
    "document_request_message": "다국어 서류 요청 메시지",
    "quota_review": "채용/쿼터",
    "candidate_readiness": "후보자 서류 준비 상태",
    "reporting_deadline": "고용변동 신고기한",
    "handoff_preview": "전문가 검토 패키지",
}


@dataclass
class AgentDispatchResult:
    skipped: bool = False
    agent_used: str = ""
    answer: str = ""
    risk_flags: list[str] = field(default_factory=list)
    tool_calls_count: int = 0
    rag_collections_used: list[str] = field(default_factory=list)
    approval_required: bool = True
    sub_agents: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def dispatch_to_agent(
    *,
    intent: str,
    message: str,
    company_id: str,
    daily_briefing: Any,
    selected_items: list[Any],
    context: Any,
) -> AgentDispatchResult:
    """인텐트에 따라 에이전트를 동기 호출하고 AgentDispatchResult를 반환한다."""
    if intent in VISA_INTENTS:
        return _call_visa_agent(
            intent=intent,
            message=message,
            company_id=company_id,
            selected_items=selected_items,
        )
    if intent in MULTILINGUAL_INTENTS:
        return _call_multilingual_agent(
            message=message,
            company_id=company_id,
            selected_items=selected_items,
            context=context,
        )
    if intent in HIRING_INTENTS:
        return _call_hiring_agent(
            intent=intent,
            message=message,
            company_id=company_id,
            selected_items=selected_items,
        )
    return AgentDispatchResult(skipped=True)


# ---------------------------------------------------------------------------
# 비자/체류 에이전트
# ---------------------------------------------------------------------------

def _call_visa_agent(
    *,
    intent: str,
    message: str,
    company_id: str,
    selected_items: list[Any],
) -> AgentDispatchResult:
    from app.agent_runtime.agents.visa_agent import run_visa_agent

    worker_id = _extract_worker_id_from_items(selected_items)
    state = _make_state(
        message=message,
        company_id=company_id,
        worker_id=worker_id,
    )
    try:
        result = run_visa_agent(state, worker_id=worker_id or None)
    except Exception as exc:
        logger.warning("visa_agent 실행 실패: %s", exc)
        return AgentDispatchResult(skipped=True)

    answer = _format_visa_answer(result, intent)
    return AgentDispatchResult(
        skipped=False,
        agent_used="visa_agent",
        answer=answer,
        risk_flags=result.get("risk_flags", []),
        tool_calls_count=result.get("tool_calls", 0),
        rag_collections_used=["foreign_hiring"],
        approval_required=True,
        sub_agents=[
            s.get("name", "") for s in result.get("sub_agents", []) if s.get("name")
        ],
        raw=result,
    )


def _format_visa_answer(result: dict[str, Any], intent: str) -> str:
    intent_ko = _INTENT_KO.get(intent, intent)
    summary = result.get("summary", "")
    risk_flags = result.get("risk_flags", [])
    sub_agents = result.get("sub_agents", [])
    handoff_triggered = result.get("handoff_triggered", False)

    lines = [f"[비자/체류 에이전트] {intent_ko} 분석 결과"]
    if summary:
        lines.append(summary)

    if risk_flags:
        lines.append(f"\n위험 플래그: {', '.join(risk_flags)}")
    else:
        lines.append("\n위험 플래그: 없음")

    for sub in sub_agents:
        name = sub.get("name", "")
        sub_risk = sub.get("risk_flags", [])
        tc = sub.get("tool_calls", 0)
        if name:
            flag_str = ", ".join(sub_risk) if sub_risk else "없음"
            lines.append(f"  - {name}: tool {tc}건, 위험 {flag_str}")

    if handoff_triggered:
        lines.append("\n행정사 검토 패키지 초안이 준비됐습니다. 담당자 승인 후 발송하세요.")

    lines.append("\n외부 발송, 정부 제출, 상태 완료 처리는 아직 수행하지 않았습니다.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 다국어 에이전트
# ---------------------------------------------------------------------------

def _call_multilingual_agent(
    *,
    message: str,
    company_id: str,
    selected_items: list[Any],
    context: Any,
) -> AgentDispatchResult:
    from app.agent_runtime.agents.multilingual_contact_agent import (
        MessageDraftInput,
        MultilingualContactAgent,
    )

    language_code = _detect_language(message)
    worker_id = _extract_worker_id_from_items(selected_items)
    purpose = _detect_message_purpose(message)

    request = MessageDraftInput(
        worker_id=worker_id or "unknown",
        language_code=language_code,
        message_purpose=purpose,
        user_request=message,
        contact_person="담당자",
    )
    try:
        agent = MultilingualContactAgent()
        output = agent.generate_message_draft(request)
    except Exception as exc:
        logger.warning("multilingual_contact_agent 실행 실패: %s", exc)
        return AgentDispatchResult(skipped=True)

    answer = _format_multilingual_answer(output, language_code, purpose)
    return AgentDispatchResult(
        skipped=False,
        agent_used="multilingual_contact_agent",
        answer=answer,
        risk_flags=output.risk_flags,
        tool_calls_count=0,
        rag_collections_used=["multilingual_contact_docs"],
        approval_required=output.approval_required,
        sub_agents=[],
        raw=output.model_dump(),
    )


def _detect_language(message: str) -> str:
    if any(kw in message for kw in ("베트남", "베트남어")):
        return "vi"
    if any(kw in message for kw in ("인도네시아", "인도네시아어")):
        return "id"
    return "vi"


def _detect_message_purpose(message: str) -> str:
    if any(kw in message for kw in ("여권", "passport")):
        return "passport_request"
    if any(kw in message for kw in ("사진", "photo")):
        return "photo_request"
    if any(kw in message for kw in ("외국인등록증", "ARC", "arc")):
        return "arc_request"
    if any(kw in message for kw in ("안전교육", "안전")):
        return "safety_training_notice"
    if any(kw in message for kw in ("상담", "EPS", "eps")):
        return "counseling_center_guide"
    if any(kw in message for kw in ("숙소", "기숙사", "주거")):
        return "housing_notice"
    return "missing_document_request"


def _format_multilingual_answer(output: Any, language_code: str, purpose: str) -> str:
    lang_ko = {"vi": "베트남어", "id": "인도네시아어"}.get(language_code, language_code)
    purpose_ko = _INTENT_KO.get(purpose, purpose)
    lines = [f"[다국어 에이전트] {lang_ko} {purpose_ko} 메시지 초안"]

    if output.status == "SUCCESS":
        if output.korean_text:
            lines.append(f"\n[한국어 원문]\n{output.korean_text}")
        if output.translated_text:
            lines.append(f"\n[{lang_ko} 번역]\n{output.translated_text}")
    else:
        lines.append(f"\n메시지 초안 생성 실패: {output.error or '알 수 없는 오류'}")

    if output.risk_flags:
        lines.append(f"\n검토 필요: {', '.join(output.risk_flags)}")

    lines.append("\n근로자에게 발송하기 전 담당자 승인이 필요합니다.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 인력확보 에이전트
# ---------------------------------------------------------------------------

def _call_hiring_agent(
    *,
    intent: str,
    message: str,
    company_id: str,
    selected_items: list[Any],
) -> AgentDispatchResult:
    from app.agent_runtime.agents.hiring_agent import run_hiring_agent

    state = _make_state(
        message=message,
        company_id=company_id,
        worker_id="",
    )
    try:
        result = run_hiring_agent(state)
    except Exception as exc:
        logger.warning("hiring_agent 실행 실패: %s", exc)
        return AgentDispatchResult(skipped=True)

    answer = _format_hiring_answer(result, intent)
    return AgentDispatchResult(
        skipped=False,
        agent_used="hiring_agent",
        answer=answer,
        risk_flags=result.get("risk_flags", []),
        tool_calls_count=result.get("tool_calls", 0),
        rag_collections_used=["workforce_official", "workforce_templates"],
        approval_required=result.get("approval_required", True),
        sub_agents=list(result.get("sub_agents", [])),
        raw=result,
    )


def _format_hiring_answer(result: dict[str, Any], intent: str) -> str:
    intent_ko = _INTENT_KO.get(intent, intent)
    lines = [f"[인력확보 에이전트] {intent_ko} 분석 결과"]

    summary = result.get("summary", "")
    if summary:
        lines.append(summary)

    hiring_draft = result.get("hiring_request_draft") or {}
    if hiring_draft:
        lines.append("\n[채용 요청 초안]")
        for k, v in hiring_draft.items():
            if v:
                lines.append(f"  {k}: {v}")

    checklist = result.get("institutional_checklist") or []
    if checklist:
        lines.append("\n[기관 체크리스트]")
        for item in checklist[:5]:
            lines.append(f"  - {item}")

    readiness_table = result.get("candidate_readiness_table") or []
    if readiness_table:
        lines.append("\n[후보자 준비 현황]")
        for row in readiness_table[:5]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("candidate_id", "")
                status = row.get("status", "")
                lines.append(f"  - {name}: {status}")

    risk_flags = result.get("risk_flags", [])
    if risk_flags:
        lines.append(f"\n위험 플래그: {', '.join(risk_flags)}")

    lines.append("\n외부 발송, 정부 제출, 상태 완료 처리는 아직 수행하지 않았습니다.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------

def _make_state(
    *,
    message: str,
    company_id: str,
    worker_id: str,
) -> ForeignHiringState:
    return ForeignHiringState(
        user_message=message,
        company_id=company_id,
        worker_id=worker_id,
    )


def _extract_worker_id_from_items(selected_items: list[Any]) -> str:
    for item in selected_items:
        worker_id = getattr(item, "worker_id", None) or getattr(item, "case_id", None)
        if worker_id and worker_id != "intent_snapshot":
            return str(worker_id)
    return ""
