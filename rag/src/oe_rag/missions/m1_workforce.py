"""M1 — 인력확보 미션 (발표 p.15의 "인력확보 에이전트").

서브에이전트 2종 (legacy agents/hiring_agent.py의 책임 이식, 자유 루프 제거):
1. 채용준비 — 쿼터 rule 소비(quota_review) + 공식 절차·요청서 템플릿 근거 검색(결정론)
   + 채용 요청서 초안(SAFE_DRAFT — 초안일 뿐 제출 아님, 항상 담당자 승인 필요).
2. 후보자준비 — 스냅샷 후보자 서류 상태를 "충족/누락"으로만 정리한다.
   발표 p.16 원칙("후보 준비도: 충족/누락만 — 점수·순위 금지")을 구조로 강제:
   결과 스키마에 점수·순위·추천 필드 자체가 없다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from ..agent.factory import RagAnswer, RagCitation
from ..agent.tools import retrieve_workforce_materials
from ..orchestration.contracts import EventType
from ..orchestration.evidence import make_event
from ..orchestration.guard import assert_output_safety

MISSION_NAME = "m1_workforce"


def run_m1_workforce_mission(
    *,
    request_id: str,
    user_message: str,
    context_snapshot: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
    chat_model: BaseChatModel | None = None,
) -> dict[str, Any]:
    snapshot = context_snapshot or {}
    intent = (route or {}).get("intent", "quota_review")
    events: list[dict[str, Any]] = []

    # --- 쿼터 rule 소비 (있으면) ------------------------------------------------------
    quota_findings = [
        f for f in snapshot.get("rule_findings", []) if f.get("risk_type") == "quota_review"
    ]
    for finding in quota_findings:
        events.append(
            make_event(
                event_type=EventType.RISK_FLAGGED,
                request_id=request_id,
                step_name="m1_workforce.quota",
                agent_name=MISSION_NAME,
                summary=f"쿼터 검토 필요(rule): {finding.get('severity')}",
                risk_level=str(finding.get("severity", "LOW")),
            )
        )

    # --- 근거 검색 (결정론) ------------------------------------------------------------
    sub_agent = (
        "candidate_readiness_agent" if intent == "candidate_readiness" else "workforce_requirement_agent"
    )
    case_type = "candidate_review" if intent == "candidate_readiness" else "new_hiring"
    retrieval = retrieve_workforce_materials.invoke(
        {"query": user_message, "case_type": case_type, "sub_agent": sub_agent}
    )
    records = retrieval.get("records", [])
    citations = [
        RagCitation(
            source_id=str(r.get("source_id", "")),
            title=str(r.get("title", "")),
            evidence_grade=str(r.get("evidence_grade", "")),
        )
        for r in records
    ]
    events.append(
        make_event(
            event_type=EventType.RAG_RETRIEVED,
            request_id=request_id,
            step_name="m1_workforce.retrieve",
            agent_name=MISSION_NAME,
            summary=f"인력확보 근거 검색 {retrieval.get('retrieved_count', 0)}건",
            citation_ids=[c.source_id for c in citations][:10],
            risk_level="MEDIUM" if retrieval.get("missing_evidence") else "LOW",
        )
    )

    # --- 후보자준비: 충족/누락만 (점수·순위 필드 없음) ----------------------------------
    readiness = _candidate_readiness(snapshot) if intent == "candidate_readiness" else None

    # --- 채용 요청서 초안 (SAFE_DRAFT — 항상 승인 필요) ---------------------------------
    draft = _request_form_draft(snapshot, records, chat_model) if intent == "quota_review" else None
    if draft is not None:
        events.append(
            make_event(
                event_type=EventType.HANDOFF_PACKAGE_DRAFT_CREATED,
                request_id=request_id,
                step_name="m1_workforce.draft",
                agent_name=MISSION_NAME,
                summary="채용 요청서 초안 생성 (제출 아님 — 승인 후 사람 실행)",
                risk_level="LOW",
                metadata={"approval_required": True},
            )
        )

    # --- 최종 응답 ----------------------------------------------------------------------
    lines: list[str] = []
    if quota_findings:
        lines.append("쿼터 검토가 필요합니다 — 잔여 인원 확인 후 진행하세요.")
    if readiness is not None:
        lines.append(readiness["summary"])
    if draft is not None:
        lines.append("채용 요청서 초안을 준비했습니다 — 승인 후 송출기관·행정사에게 전달됩니다.")
    if not lines:
        top = citations[:3]
        lines.append(
            "다음 근거를 참고하세요: " + "; ".join(c.title for c in top)
            if top
            else "관련 공식 근거를 찾지 못했습니다. 담당자 확인이 필요합니다."
        )
    final_response = "\n".join(lines)
    assert_output_safety(final_response)

    approval_required = draft is not None
    answer = RagAnswer(
        final_response=final_response,
        citations=citations,
        missing_evidence=bool(retrieval.get("missing_evidence")),
        risk_flags=(["MISSING_EVIDENCE"] if retrieval.get("missing_evidence") else []),
    )
    return {
        "mission": MISSION_NAME,
        "status": "SUCCESS",
        "candidate_readiness": readiness,
        "request_form_draft": draft,
        "structured_response": answer.model_dump(),
        "approval_required": approval_required,
        "risk_flags": answer.risk_flags,
        "evidence_events": events,
    }


def _candidate_readiness(snapshot: dict[str, Any]) -> dict[str, Any]:
    """충족/누락 목록만 — 점수·순위·추천 없음(발표 원칙, 인격 평가 원천 차단)."""
    candidates = snapshot.get("candidates", [])
    candidate_documents = snapshot.get("candidate_documents", [])
    if not candidates:
        return {
            "summary": "후보자 데이터가 스냅샷에 없습니다 — 후보자 등록 후 다시 확인하세요.",
            "rows": [],
        }

    docs_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for doc in candidate_documents:
        docs_by_candidate.setdefault(str(doc.get("candidate_id")), []).append(doc)

    rows = []
    for candidate in candidates:
        cid = str(candidate.get("candidate_id"))
        docs = docs_by_candidate.get(cid, [])
        satisfied = sorted(d.get("document_type", "") for d in docs if d.get("status") == "submitted")
        missing = sorted(d.get("document_type", "") for d in docs if d.get("status") == "missing")
        rows.append(
            {
                "candidate_id": cid,
                "display_name": candidate.get("display_name", ""),
                "satisfied": satisfied,
                "missing": missing,
            }
        )
    total_missing = sum(len(r["missing"]) for r in rows)
    return {
        "summary": f"후보자 {len(rows)}명 서류 상태 — 충족/누락만 표시합니다(점수·순위 없음). 누락 합계 {total_missing}건.",
        "rows": rows,
    }


def _request_form_draft(
    snapshot: dict[str, Any],
    records: list[dict[str, Any]],
    chat_model: BaseChatModel | None,
) -> dict[str, Any]:
    company = snapshot.get("company", {})
    template = next(
        (r for r in records if "요청서" in str(r.get("title", ""))),
        None,
    )
    body = (
        f"[채용 요청서 초안]\n사업장: {company.get('name', '(사업장명)')}\n"
        "요청 인원·직무·근무조건은 담당자가 확인 후 확정하세요.\n"
        "이 초안은 승인 전 외부로 전달되지 않습니다."
    )
    return {
        "kind": "hiring_request_draft",
        "body": body,
        "template_source_id": template.get("source_id") if template else None,
        "approval_required": True,
    }
