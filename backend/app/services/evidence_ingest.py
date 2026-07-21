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
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.counters import next_event_no
from app.db.ids import new_id
from app.domain.pii import redact_pii_payload
from app.models.citation import Citation
from app.models.evidence import EvidenceEvent

# rag(orchestration/contracts.EventType 값) → db CHECK 허용값. 매핑 없는 나머지는 그대로 통과.
_EVENT_TYPE_MAP: dict[str, str] = {
    "approval_completed": "approval_decided",
    "handoff_package_draft_created": "handoff_generated",
}

_GRADE_TO_STATUS = {"A": "official", "B": "official", "E": "internal"}


class UnmappableEventTypeError(ValueError):
    pass


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

    # RAG의 summary/metadata는 evidence와 SSE로 직결된다. 원문 input이 다시 들어오더라도
    # append-only 감사 기록에 남지 않게 저장 전 마스킹한다.
    event = cast(dict[str, Any], redact_pii_payload(event))

    db_type = map_event_type(str(event.get("event_type", "")))
    at = _parse_at(event.get("created_at"))
    event_no = next_event_no(db, company_id)

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


def canonicalize_citations(
    *,
    company_id: str,
    citations: list[dict[str, Any]],
    canonical_citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """RAG 모델이 선택한 source_id를 서버가 만든 candidate catalog으로 재주입한다.

    모델 출력은 source_id 선택에만 사용하고 title·grade·URL을 신뢰하지 않는다. 이로써 존재하지 않는
    source와 등급 승격, 타사 internal citation의 우회 저장을 차단한다.
    """
    catalog: dict[str, dict[str, Any]] = {}
    for candidate in canonical_citations:
        if not isinstance(candidate, dict):
            continue
        source_id = str(candidate.get("source_id", "")).strip()
        grade = str(candidate.get("evidence_grade", "")).upper()
        if not source_id or grade not in _GRADE_TO_STATUS:
            continue
        # A/B는 전역 공식 근거만, E는 현재 회사로 scope가 증명된 내부 근거만 허용한다.
        # RAG catalog에 company_id가 없으면 E를 거부하는 것이 타사 근거를 현재 회사에
        # 재귀속시키는 것보다 안전하다.
        scope_company_id = candidate.get("company_id")
        if grade == "E" and scope_company_id != company_id:
            continue
        if grade in {"A", "B"} and scope_company_id is not None and scope_company_id != "":
            continue
        catalog[source_id] = {
            "source_id": source_id,
            "title": str(candidate.get("title") or source_id),
            "evidence_grade": grade,
            "url": candidate.get("url"),
        }

    selected: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        source_id = str(citation.get("source_id", "")).strip()
        if source_id in seen_source_ids:
            continue
        canonical = catalog.get(source_id)
        if canonical is None:
            continue
        seen_source_ids.add(source_id)
        selected.append(canonical)
    return selected


def upsert_citations(
    db: Session,
    *,
    company_id: str,
    citations: list[dict[str, Any]],
    canonical_citations: list[dict[str, Any]],
) -> list[Citation]:
    """RagCitation dict 목록(source_id/title/evidence_grade)을 citations 테이블에
    멱등 upsert한다. id=source_id 그대로 재사용 — rag 검색 결과 자체가 이미 안정적인
    자연키를 갖고 있어(rag/src/oe_rag/chunking.py의 chunk 계약), 별도 매핑 테이블 없이
    직결 가능하다.

    정보 갭: rag의 RagCitation에는 publisher/url이 없다(agent/factory.py 계약 참고) —
    title을 source 필드 폴백으로 쓴다. 정밀한 출처 문자열이 필요해지면 rag 쪽
    citation 계약(agent/factory.RagCitation)에 publisher/url을 추가하는 후속 작업이 맞다.
    """
    citations = canonicalize_citations(
        company_id=company_id,
        citations=citations,
        canonical_citations=canonical_citations,
    )
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

        # citations.id는 현재 전역 PK다. 서로 다른 테넌트가 같은 raw source_id를
        # 사용했을 때 upsert가 기존 내부 근거를 덮어쓰지 않도록 같은 스코프만 갱신한다.
        # 충돌한 근거를 현재 회사에 재귀속하지 않고 fail-closed한다.
        existing = db.get(Citation, source_id)
        if existing is not None and existing.company_id != scoped_company_id:
            continue

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
                where=Citation.company_id.is_not_distinct_from(scoped_company_id),
            )
        )
        db.execute(stmt)
        saved_row = db.execute(select(Citation).where(Citation.id == source_id)).scalar_one_or_none()
        if saved_row is not None and saved_row.company_id == scoped_company_id:
            saved.append(saved_row)
    return saved
