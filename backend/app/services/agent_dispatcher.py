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
    selected_items = _focus_visa_items_for_query(message, selected_items)
    if _is_list_query(message) or len(selected_items) != 1:
        answer = _format_visa_item_list(selected_items, intent)
        return AgentDispatchResult(
            skipped=False,
            agent_used="visa_agent",
            answer=answer,
            risk_flags=[
                str(getattr(item, "risk_type", ""))
                for item in selected_items
                if getattr(item, "severity", "") in {"CRITICAL", "HIGH"}
            ],
            tool_calls_count=0,
            rag_collections_used=["daily_briefing_source"],
            approval_required=False,
            sub_agents=[],
            raw={"mode": "daily_briefing_item_list", "item_count": len(selected_items)},
        )

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
    handoff_triggered = result.get("handoff_triggered", False)

    lines = [f"[비자/체류 에이전트] {intent_ko} 분석 결과"]
    if summary:
        lines.append(summary)

    if risk_flags:
        lines.append(f"\n위험 플래그: {', '.join(risk_flags)}")
    else:
        lines.append("\n위험 플래그: 없음")

    if handoff_triggered and risk_flags:
        lines.append("\n행정사 검토 패키지 초안이 준비됐습니다. 담당자 승인 후 발송하세요.")

    lines.append("\n외부 발송, 정부 제출, 상태 완료 처리는 아직 수행하지 않았습니다.")
    return "\n".join(lines)


def _format_visa_item_list(selected_items: list[Any], intent: str) -> str:
    intent_ko = _INTENT_KO.get(intent, intent)
    if not selected_items:
        return "\n".join(
            [
                f"[비자/체류 에이전트] {intent_ko} 확인 결과",
                "현재 기준으로 확인된 대상자가 없습니다.",
                "외부 발송, 정부 제출, 상태 완료 처리는 수행하지 않았습니다.",
            ]
        )

    lines = [
        f"[비자/체류 에이전트] {intent_ko} 확인 결과",
        f"확인 필요한 인원은 {len(selected_items)}명입니다.",
    ]
    for index, item in enumerate(_dedupe_items(selected_items), start=1):
        name = getattr(item, "subject_display_name", None) or getattr(item, "subject_id", "")
        risk_type = getattr(item, "risk_type", "")
        missing_documents = getattr(item, "missing_documents", []) or []
        severity = getattr(item, "severity", "")
        lines.append(f"\n{index}. {name}")
        lines.append(f"- 항목: {RISK_LABELS.get(risk_type, risk_type)}")
        lines.append(f"- 기한: {_risk_timing(item)}")
        lines.append(f"- 누락 서류: {_document_list(missing_documents)}")
        if severity:
            lines.append(f"- 우선순위: {severity}")
    lines.append("\n외부 발송, 정부 제출, 상태 완료 처리는 수행하지 않았습니다.")
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
        worker_id = (
            getattr(item, "worker_id", None)
            or getattr(item, "subject_id", None)
            or getattr(item, "case_id", None)
        )
        if worker_id and worker_id != "intent_snapshot":
            return str(worker_id)
    return ""


RISK_LABELS: dict[str, str] = {
    "visa_expiry": "체류기간 연장 준비",
    "missing_document": "체류/고용 서류 누락 확인",
    "contract_visa_conflict": "계약-체류기간 충돌 검토",
    "reporting_deadline": "고용변동 신고기한 확인",
    "quota_review": "신규 인력/쿼터 검토",
    "candidate_readiness": "후보자 서류 준비상태 확인",
}


DOCUMENT_LABELS: dict[str, str] = {
    "passport_copy": "여권 사본",
    "alien_registration_copy": "외국인등록증 사본",
    "alien_registration": "외국인등록증 사본",
    "standard_labor_contract": "표준근로계약서 사본",
    "labor_contract": "표준근로계약서 사본",
    "work_permit": "고용허가서",
}


def _risk_timing(item: Any) -> str:
    if getattr(item, "expired", False):
        days_overdue = getattr(item, "days_overdue", None)
        if days_overdue is not None:
            return f"만료 후 {days_overdue}일 경과"
        return "기한 경과"
    d_day = getattr(item, "d_day", None)
    if d_day is not None:
        return f"D-{d_day}"
    due_date = getattr(item, "due_date", None)
    if due_date:
        return str(due_date)
    return "기한 확인 필요"


def _document_list(documents: list[str]) -> str:
    if not documents:
        return "현재 응답 범위에서 확인된 누락 없음"
    return ", ".join(DOCUMENT_LABELS.get(document, document) for document in documents)


def _is_list_query(message: str) -> bool:
    return any(
        keyword in message
        for keyword in ("인원", "사람", "누구", "명", "목록", "리스트", "알려줘", "정리")
    )


def _focus_visa_items_for_query(message: str, selected_items: list[Any]) -> list[Any]:
    if any(keyword in message for keyword in ("누락", "빠진", "미제출", "제출 안", "없는")):
        missing = [item for item in selected_items if getattr(item, "risk_type", "") == "missing_document"]
        return missing
    return selected_items


def _dedupe_items(items: list[Any]) -> list[Any]:
    seen: set[tuple[str, str, str]] = set()
    output: list[Any] = []
    for item in items:
        key = (
            str(getattr(item, "subject_id", "")),
            str(getattr(item, "risk_type", "")),
            ",".join(getattr(item, "missing_documents", []) or []),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output
