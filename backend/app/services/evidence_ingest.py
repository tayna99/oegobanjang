"""rag가 방출한 evidence 이벤트·citation을 backend DB에 영속화 — plans/BACKEND_CONNECT.md B2.

두 계약이 이름 그대로 일치하지 않는 지점을 여기서 흡수한다(둘 다 정본이라 어느 쪽도
바꾸지 않는다 — rag의 EventType은 legacy schemas/evidence.py 이식, backend CHECK 제약은
db/schema.sql §9/src/types.ts EvidenceType 이식. 이력이 달라 생긴 명명 드리프트):

  rag EventType.APPROVAL_COMPLETED = "approval_completed"
    → db CHECK 허용값은 "approval_decided"
  rag EventType.HANDOFF_PACKAGE_DRAFT_CREATED = "handoff_package_draft_created"
    → db CHECK 허용값은 "handoff_generated"

citation 스코프 규칙(db/schema.sql CHECK `company_id IS NOT NULL OR status <> 'internal'`):
evidence_grade A/B(공식 법령·절차)는 전역(company_id=NULL, status=official).
evidence_grade E(내부 템플릿)는 company_id 없이 저장할 수 없다 — 반드시 회사 스코프.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.models.citation import Citation
from app.models.company import Company
from app.models.evidence import EvidenceEvent

# rag(orchestration/contracts.EventType 값) → db CHECK 허용값. 매핑 없는 나머지는 그대로 통과.
_EVENT_TYPE_MAP: dict[str, str] = {
    "approval_completed": "approval_decided",
    "handoff_package_draft_created": "handoff_generated",
}

_GRADE_TO_STATUS = {"A": "official", "B": "official", "E": "internal"}


class UnmappableEventTypeError(ValueError):
    pass


def _next_event_no(db: Session, company_id: str) -> int:
    """app/services/approvals.py의 _next_event_no와 동일 계약(companies.evidence_seq 원자 증가)."""
    from sqlalchemy import update

    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(evidence_seq=Company.evidence_seq + 1)
        .returning(Company.evidence_seq)
    ).scalar_one()


def map_event_type(rag_event_type: str) -> str:
    return _EVENT_TYPE_MAP.get(rag_event_type, rag_event_type)


def ingest_rag_evidence_event(
    db: Session,
    *,
    company_id: str,
    event: dict[str, Any],
    run_id: str | None = None,
    case_id: str | None = None,
) -> EvidenceEvent:
    """rag_client.SseEvent(event="evidence").data 하나를 EvidenceEvent 행으로 저장한다.

    PK는 새로 발급한다(rag의 id는 rag 프로세스 로컬 UUID라 backend PK 네임스페이스와
    별개) — rag 원본 id·citation_ids·metadata는 payload_ref에 JSON으로 보존해
    감사 추적을 완전하게 유지한다. citation_ids는 evidence_events 테이블에 컬럼이
    없으므로(케이스 연결은 case_citations 테이블 몫) 여기서는 payload_ref로만 남기고,
    case가 존재하는 흐름(B3' 이후)에서 case_citations 연결을 추가한다.
    """
    import json

    db_type = map_event_type(str(event.get("event_type", "")))
    at = _parse_at(event.get("created_at"))
    event_no = _next_event_no(db, company_id)

    row = EvidenceEvent(
        id=new_id(),
        company_id=company_id,
        event_no=event_no,
        type=db_type,
        at=at,
        case_id=case_id,
        action_id=None,
        approval_id=event.get("approval_id"),
        run_id=run_id,
        actor_type="agent",
        actor_user_id=None,
        actor_display=str(event.get("agent_name") or "rag-orchestration"),
        summary=str(event.get("summary", ""))[:2000],
        input_hash=None,
        output_hash=None,
        trace_id=str(event.get("request_id")) if event.get("request_id") else None,
        request_id=str(event.get("request_id")) if event.get("request_id") else None,
        payload_ref=json.dumps(
            {
                "rag_event_id": event.get("id"),
                "rag_event_type": event.get("event_type"),
                "citation_ids": event.get("citation_ids", []),
                "risk_level": event.get("risk_level"),
                "step_name": event.get("step_name"),
                "metadata": event.get("metadata", {}),
            },
            ensure_ascii=False,
        )[:4000],
    )
    db.add(row)
    return row


def _parse_at(value: Any) -> dt.datetime:
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return dt.datetime.now(dt.UTC)


def upsert_citations(
    db: Session,
    *,
    company_id: str,
    citations: list[dict[str, Any]],
) -> list[Citation]:
    """RagCitation dict 목록(source_id/title/evidence_grade)을 citations 테이블에
    멱등 upsert한다. id=source_id 그대로 재사용 — rag 검색 결과 자체가 이미 안정적인
    자연키를 갖고 있어(rag/src/oe_rag/chunking.py의 chunk 계약), 별도 매핑 테이블 없이
    직결 가능하다.

    정보 갭: rag의 RagCitation에는 publisher/url이 없다(agent/factory.py 계약 참고) —
    title을 source 필드 폴백으로 쓴다. 정밀한 출처 문자열이 필요해지면 rag 쪽
    citation 계약(agent/factory.RagCitation)에 publisher/url을 추가하는 후속 작업이 맞다.
    """
    if not citations:
        return []

    now = dt.datetime.now(dt.UTC)
    saved: list[Citation] = []
    for citation in citations:
        source_id = str(citation.get("source_id", "")).strip()
        if not source_id:
            continue
        grade = str(citation.get("evidence_grade", "")).upper()
        if grade in {"D", "F"}:
            continue  # RAG_STRATEGY: D/F는 답변 근거로 쓸 수 없다 — citation 라이브러리에도 안 올린다
        status = _GRADE_TO_STATUS.get(grade, "review_needed")
        scoped_company_id = company_id if status == "internal" else None

        stmt = (
            pg_insert(Citation)
            .values(
                id=source_id,
                company_id=scoped_company_id,
                grade=grade,
                status=status,
                title=str(citation.get("title") or source_id),
                source=str(citation.get("title") or source_id),
                source_url=citation.get("url"),
                ingest_at=now,
            )
            .on_conflict_do_update(
                index_elements=[Citation.id],
                set_={
                    "grade": grade,
                    "status": status,
                    "title": str(citation.get("title") or source_id),
                    "updated_at": now,
                },
            )
        )
        db.execute(stmt)
        saved.append(
            db.execute(select(Citation).where(Citation.id == source_id)).scalar_one()
        )
    return saved
