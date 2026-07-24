"""evidence_ingest — 이벤트 타입 매핑·PK 발급·citation 등급 스코프 규칙 (PG 하니스)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.company import Company
from app.models.evidence import EvidenceEvent
from app.services.evidence_ingest import (
    ingest_rag_evidence_event,
    map_event_type,
    upsert_citations,
)


@pytest.fixture()
def company(db: Session) -> str:
    db.add(Company(id="cmp_evi_test", name="증빙테스트제조"))
    db.flush()
    return "cmp_evi_test"


def test_map_event_type_translates_known_drift() -> None:
    assert map_event_type("approval_completed") == "approval_decided"
    assert map_event_type("handoff_package_draft_created") == "handoff_generated"


def test_map_event_type_passes_through_unmapped_values() -> None:
    assert map_event_type("rag_retrieved") == "rag_retrieved"
    assert map_event_type("intent_classified") == "intent_classified"


def test_ingest_event_satisfies_db_check_constraint_for_all_rag_event_types(db: Session, company: str) -> None:
    """G1의 EventType 9종 전체가 실제로 evidence_events.type CHECK를 통과하는지 — 계약 드리프트 회귀 가드."""
    rag_event_types = [
        "intent_classified",
        "plan_created",
        "tool_executed",
        "rag_retrieved",
        "risk_flagged",
        "approval_requested",
        "approval_completed",  # → approval_decided 매핑 경유
        "handoff_package_draft_created",  # → handoff_generated 매핑 경유
        "final_response_generated",
    ]
    for rag_type in rag_event_types:
        row = ingest_rag_evidence_event(
            db,
            company_id=company,
            event={
                "id": "rag-evt-1",
                "event_type": rag_type,
                "request_id": "req-1",
                "summary": f"테스트 이벤트 {rag_type}",
                "citation_ids": ["src_1"],
                "risk_level": "LOW",
            },
        )
        db.flush()  # CHECK 제약 위반 시 여기서 즉시 IntegrityError
        assert row.type == map_event_type(rag_type)


def test_ingest_event_assigns_monotonic_event_no_per_company(db: Session, company: str) -> None:
    first = ingest_rag_evidence_event(
        db, company_id=company, event={"event_type": "intent_classified", "summary": "a"}
    )
    db.flush()
    second = ingest_rag_evidence_event(
        db, company_id=company, event={"event_type": "rag_retrieved", "summary": "b"}
    )
    db.flush()

    assert second.event_no == first.event_no + 1


def test_ingest_event_preserves_rag_metadata_in_payload_ref_not_in_dedicated_columns(
    db: Session, company: str
) -> None:
    row = ingest_rag_evidence_event(
        db,
        company_id=company,
        event={
            "id": "rag-evt-xyz",
            "event_type": "rag_retrieved",
            "request_id": "req-9",
            "summary": "근거 3건",
            "citation_ids": ["s1", "s2", "s3"],
            "risk_level": "MEDIUM",
            "metadata": {"missing_evidence": False},
        },
    )
    db.flush()

    payload = json.loads(row.payload_ref)
    assert payload["rag_event_id"] == "rag-evt-xyz"
    assert payload["citation_ids"] == ["s1", "s2", "s3"]
    assert row.trace_id == "req-9"


def test_ingest_event_defaults_actor_to_agent(db: Session, company: str) -> None:
    row = ingest_rag_evidence_event(
        db, company_id=company, event={"event_type": "intent_classified", "summary": "x"}
    )
    db.flush()

    assert row.actor_type == "agent"


def test_upsert_citations_official_grade_is_global_scope(db: Session, company: str) -> None:
    payload = [{"source_id": "E9_STAY_EXT_STEP1", "title": "체류연장 1단계", "evidence_grade": "B"}]
    saved = upsert_citations(
        db,
        company_id=company,
        citations=payload,
        canonical_citations=payload,
    )
    db.flush()

    assert saved[0].company_id is None
    assert saved[0].status == "official"
    assert saved[0].grade == "B"


def test_upsert_citations_internal_grade_requires_company_scope(db: Session, company: str) -> None:
    """CHECK (company_id IS NOT NULL OR status <> 'internal') 위반 회귀 가드."""
    payload = [
        {
            "source_id": "handoff_questions_template",
            "title": "행정사 확인 질문",
            "evidence_grade": "E",
            "company_id": company,
        }
    ]
    saved = upsert_citations(
        db,
        company_id=company,
        citations=payload,
        canonical_citations=payload,
    )
    db.flush()  # CHECK 위반이면 여기서 즉시 실패해야 한다

    assert saved[0].company_id == company
    assert saved[0].status == "internal"


def test_upsert_citations_excludes_low_grade_evidence(db: Session, company: str) -> None:
    payload = [
        {"source_id": "d_grade_doc", "title": "D등급", "evidence_grade": "D"},
        {"source_id": "f_grade_doc", "title": "F등급(합성)", "evidence_grade": "F"},
    ]
    saved = upsert_citations(
        db,
        company_id=company,
        citations=payload,
        canonical_citations=payload,
    )

    assert saved == []
    remaining = db.execute(select(Citation)).scalars().all()
    assert remaining == []


def test_upsert_citations_is_idempotent(db: Session, company: str) -> None:
    payload = [{"source_id": "E9_STAY_EXT_STEP1", "title": "체류연장 1단계", "evidence_grade": "B"}]

    upsert_citations(db, company_id=company, citations=payload, canonical_citations=payload)
    db.flush()
    upsert_citations(db, company_id=company, citations=payload, canonical_citations=payload)
    db.flush()

    rows = db.execute(select(Citation).where(Citation.id == "E9_STAY_EXT_STEP1")).scalars().all()
    assert len(rows) == 1


def test_upsert_citations_uses_catalog_not_model_metadata(db: Session, company: str) -> None:
    catalog = [
        {
            "source_id": "official_source",
            "title": "정본 B등급 근거",
            "evidence_grade": "B",
            "url": "https://example.test/official",
        }
    ]
    model_output = [
        {"source_id": "official_source", "title": "조작된 제목", "evidence_grade": "A"},
        {"source_id": "unknown_or_other_company", "title": "타사 근거", "evidence_grade": "E"},
    ]

    saved = upsert_citations(
        db,
        company_id=company,
        citations=model_output,
        canonical_citations=catalog,
    )
    db.flush()

    assert [row.id for row in saved] == ["official_source"]
    row = db.get(Citation, "official_source")
    assert row is not None
    assert row.title == "정본 B등급 근거"
    assert row.grade == "B"
    assert row.company_id is None


def test_upsert_citations_rejects_internal_catalog_from_another_company(db: Session, company: str) -> None:
    saved = upsert_citations(
        db,
        company_id=company,
        citations=[{"source_id": "other_company_template", "title": "model title", "evidence_grade": "E"}],
        canonical_citations=[
            {
                "source_id": "other_company_template",
                "title": "other company internal template",
                "evidence_grade": "E",
                "company_id": "cmp_other",
            }
        ],
    )
    db.flush()

    assert saved == []
    assert db.get(Citation, "other_company_template") is None


def test_upsert_citations_does_not_overwrite_other_company_internal_source_id(db: Session, company: str) -> None:
    """전역 PK 충돌이 타사 internal citation을 현재 회사 것으로 바꾸면 안 된다."""
    other_company = "cmp_other"
    db.execute(
        text(
            "INSERT INTO companies (id, name) VALUES (:id, 'Other')"
        ),
        {"id": other_company},
    )
    db.execute(
        text(
            "INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at) "
            "VALUES ('shared_internal_source', :company_id, 'E', 'internal', 'Other company title', "
            "'Other company title', now())"
        ),
        {"company_id": other_company},
    )
    db.flush()

    saved = upsert_citations(
        db,
        company_id=company,
        citations=[{"source_id": "shared_internal_source", "title": "forged", "evidence_grade": "E"}],
        canonical_citations=[
            {
                "source_id": "shared_internal_source",
                "title": "Current company template",
                "evidence_grade": "E",
                "company_id": company,
            }
        ],
    )
    db.flush()

    row = db.get(Citation, "shared_internal_source")
    assert saved == []
    assert row is not None
    assert row.company_id == other_company
    assert row.title == "Other company title"
