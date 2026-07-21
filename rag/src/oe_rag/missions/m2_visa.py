"""M2 — 비자·서류 미션 (발표 p.15의 "비자서류 에이전트").

서브에이전트 2종 (legacy agents/visa_agent.py:142,205의 책임을 이식하되, bind_tools
자유 판단 루프는 발표 원칙("LLM 자유 tool loop 금지") 위반이라 순차 결정론 호출로 대체):

1. 비자만료위험도 분석 — backend가 스냅샷에 실어 보낸 rule_findings(visa_expiry·
   contract_visa_conflict)를 **소비만** 한다. severity는 이 미션 어디에서도 재계산·
   변경되지 않는다(p.16 "Rule이 케이스를 확정").
2. 서류우선순위 — 스냅샷 documents의 missing_class(CRITICAL/SUPPLEMENTARY,
   backend rules.classify_missing_document가 이미 분류)를 소비해 우선순위를 세운다.

LLM은 최대 1회 — 담당자용 요약 문구만 다듬는다(오프라인이면 결정론 템플릿).
CRITICAL/HIGH 위험이 있으면 행정사 handoff 초안을 준비하고 approval_required=true
(pending-first — 전달은 승인 후 사람 몫).
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from ..agent.factory import RagAnswer, RagCitation
from ..agent.tools import search_policy_documents
from ..orchestration.contracts import EventType
from ..orchestration.evidence import make_event
from ..orchestration.guard import assert_output_safety

MISSION_NAME = "m2_visa"

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

_HANDOFF_SEVERITIES = {"CRITICAL", "HIGH"}

_SUMMARY_SYSTEM_PROMPT = (
    "당신은 외국인 고용 운영 OS '외고반장'의 비자·서류 담당 요약기입니다. "
    "주어진 rule 판정 결과와 누락 서류 목록을 담당자가 읽기 쉬운 한국어로 정리하세요. "
    "위험도(severity)·D-day 숫자는 절대 바꾸지 말고 그대로 인용하세요. "
    "비자 가능/불가능 판정, 법률 자문, 후보 평가는 금지입니다."
)


class VisaSummaryDraft(BaseModel):
    """LLM 요약 출력 계약 — severity는 여기 없다(LLM이 만질 수 없는 값)."""

    summary: str = Field(description="담당자용 상황 요약(한국어)")
    next_steps: list[str] = Field(default_factory=list, description="권장 다음 단계")


def run_m2_visa_mission(
    *,
    request_id: str,
    user_message: str,
    context_snapshot: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
    chat_model: BaseChatModel | None = None,
) -> dict[str, Any]:
    snapshot = context_snapshot or {}
    findings = snapshot.get("rule_findings", [])
    events: list[dict[str, Any]] = []

    # --- 서브에이전트 1: 비자만료위험도 (rule 소비만) --------------------------------
    visa_findings = [
        f for f in findings if f.get("risk_type") in {"visa_expiry", "contract_visa_conflict"}
    ]
    mission_severity = _max_severity(visa_findings + [f for f in findings if f.get("risk_type") == "missing_document"])

    if visa_findings:
        worst = min(visa_findings, key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "LOW"), 9))
        events.append(
            make_event(
                event_type=EventType.RISK_FLAGGED,
                request_id=request_id,
                step_name="m2_visa.risk",
                agent_name=MISSION_NAME,
                summary=f"비자 위험 판정(rule): {worst.get('severity')}"
                + (f" D-{worst['d_day']}" if worst.get("d_day") is not None else ""),
                risk_level=str(worst.get("severity", "LOW")),
                metadata={"rule_findings_count": len(visa_findings)},
            )
        )

    # --- 서브에이전트 2: 서류우선순위 (missing_class 소비) ----------------------------
    documents = snapshot.get("documents", [])
    missing_docs = [d for d in documents if d.get("status") == "missing"]
    critical_missing = [d for d in missing_docs if d.get("missing_class") == "CRITICAL"]
    supplementary_missing = [d for d in missing_docs if d.get("missing_class") != "CRITICAL"]
    prioritized = [*critical_missing, *supplementary_missing]

    if missing_docs:
        events.append(
            make_event(
                event_type=EventType.RISK_FLAGGED,
                request_id=request_id,
                step_name="m2_visa.documents",
                agent_name=MISSION_NAME,
                summary=f"누락 서류 {len(missing_docs)}건 (필수 {len(critical_missing)}건)",
                risk_level="HIGH" if critical_missing else "MEDIUM",
                metadata={"critical": len(critical_missing), "supplementary": len(supplementary_missing)},
            )
        )

    # --- 근거 검색 (결정론 tool 호출 — LLM 판단 없음) --------------------------------
    policy = search_policy_documents.invoke(
        {"query": user_message, "visa_type": _visa_type_hint(snapshot), "top_k": 5}
    )
    citations = [
        RagCitation(
            source_id=str(c.get("source_id", "")),
            title=str(c.get("title", "")),
            evidence_grade=str(c.get("evidence_grade", "")),
        )
        for c in policy.get("citations", [])
        if str(c.get("source_id", "")).strip()
        and str(c.get("evidence_grade", "")).upper() in {"A", "B", "E"}
    ]
    events.append(
        make_event(
            event_type=EventType.RAG_RETRIEVED,
            request_id=request_id,
            step_name="m2_visa.retrieve",
            agent_name=MISSION_NAME,
            summary=f"비자·체류 근거 검색 {policy.get('retrieved_count', 0)}건",
            citation_ids=[c.source_id for c in citations][:10],
            risk_level="MEDIUM" if policy.get("missing_evidence") else "LOW",
            metadata={"missing_evidence": bool(policy.get("missing_evidence"))},
        )
    )

    # --- handoff (pending-first) ---------------------------------------------------
    handoff_needed = mission_severity in _HANDOFF_SEVERITIES
    if handoff_needed:
        events.append(
            make_event(
                event_type=EventType.HANDOFF_PACKAGE_DRAFT_CREATED,
                request_id=request_id,
                step_name="m2_visa.handoff",
                agent_name=MISSION_NAME,
                summary="행정사 검토 패키지 초안 준비 (전송 없음 — 승인 후 사람 실행)",
                risk_level=mission_severity,
                metadata={"approval_required": True},
            )
        )

    # --- 요약 (LLM 최대 1회 / 오프라인 결정론 템플릿) --------------------------------
    summary_text, next_steps = _summarize(
        user_message, visa_findings, prioritized, chat_model
    )

    final_lines = [summary_text]
    if next_steps:
        final_lines.append("다음 단계: " + " / ".join(next_steps))
    if handoff_needed:
        final_lines.append("위험도가 높아 행정사 검토 패키지 초안을 준비했습니다 — 승인 후 전달됩니다.")
    final_response = "\n".join(final_lines)
    assert_output_safety(final_response)

    answer = RagAnswer(
        final_response=final_response,
        citations=citations,
        missing_evidence=bool(policy.get("missing_evidence")),
        risk_flags=(["MISSING_EVIDENCE"] if policy.get("missing_evidence") else []),
    )

    return {
        "mission": MISSION_NAME,
        "status": "SUCCESS",
        "severity": mission_severity,  # rule 최고 심각도 — LLM 개입 불가 값
        "risk_findings": visa_findings,
        "document_priority": prioritized,
        "handoff": {"prepared": handoff_needed, "approval_required": handoff_needed},
        "structured_response": answer.model_dump(),
        "citation_catalog": [citation.model_dump() for citation in citations],
        "approval_required": handoff_needed,
        "risk_flags": answer.risk_flags,
        "evidence_events": events,
    }


def _max_severity(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "LOW"
    return min(
        (str(f.get("severity", "LOW")) for f in findings),
        key=lambda s: _SEVERITY_ORDER.get(s, 9),
    )


def _visa_type_hint(snapshot: dict[str, Any]) -> str:
    workers = snapshot.get("workers", [])
    if workers:
        return str(workers[0].get("visa_type", "E-9"))
    return "E-9"


def _summarize(
    user_message: str,
    visa_findings: list[dict[str, Any]],
    prioritized_docs: list[dict[str, Any]],
    chat_model: BaseChatModel | None,
) -> tuple[str, list[str]]:
    finding_lines = [
        f"- {f.get('display_label') or f.get('risk_type')}: {f.get('severity')}"
        + (f" (D-{f['d_day']})" if f.get("d_day") is not None else "")
        + (f" · 근로자 {f.get('worker_id')}" if f.get("worker_id") else "")
        for f in visa_findings
    ]
    doc_lines = [
        f"- {d.get('doc_type')} ({d.get('missing_class') or 'SUPPLEMENTARY'})"
        for d in prioritized_docs
    ]

    if chat_model is not None:
        structured = chat_model.with_structured_output(VisaSummaryDraft)
        result = structured.invoke(
            [
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"요청: {user_message}\n\nRule 판정:\n" + ("\n".join(finding_lines) or "- 없음")
                        + "\n\n누락 서류(우선순위순):\n" + ("\n".join(doc_lines) or "- 없음")
                    ),
                },
            ]
        )
        if isinstance(result, VisaSummaryDraft):
            return result.summary, result.next_steps

    # 결정론 템플릿 (오프라인 정본)
    parts = []
    if finding_lines:
        parts.append("비자·체류 위험 판정(rule):\n" + "\n".join(finding_lines))
    else:
        parts.append("현재 rule 판정 기준 임박한 비자·체류 위험이 없습니다.")
    if doc_lines:
        parts.append("누락 서류 우선순위:\n" + "\n".join(doc_lines))
    next_steps = []
    if prioritized_docs:
        next_steps.append("필수 누락 서류 요청 초안 검토")
    if finding_lines:
        next_steps.append("체류 연장 준비 일정 확인")
    return "\n\n".join(parts), next_steps
