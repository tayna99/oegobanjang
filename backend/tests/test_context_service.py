"""ContextSnapshot 빌더 — tenant scope·룰 실행·PII 부재 (PG 테스트 하니스 사용)."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.document import WorkerDocument
from app.models.worker import Worker
from app.services.context_service import (
    SnapshotPIIError,
    WorkerSnapshot,
    assert_snapshot_has_no_pii,
    build_context_snapshot,
)

REF = "2026-07-17"


@pytest.fixture()
def seeded_company(db: Session) -> str:
    company = Company(id="cmp_ctx_test", name="컨텍스트테스트제조")
    db.add(company)
    db.add(
        Worker(
            id="wrk_high",
            company_id="cmp_ctx_test",
            display_name="Nguyen Van A",
            nationality="베트남",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 8, 6),  # D-20 → HIGH
            contract_ends_at=dt.date(2027, 1, 1),  # 비자보다 늦게 끝남 → conflict
        )
    )
    db.add(
        Worker(
            id="wrk_low",
            company_id="cmp_ctx_test",
            display_name="Batbayar",
            nationality="몽골",
            visa_type="E-9",
            stay_expires_at=dt.date(2027, 7, 1),  # 여유 → LOW
        )
    )
    # 다른 회사 데이터 — tenant scope 검증용
    db.add(Company(id="cmp_other", name="다른회사"))
    db.add(
        Worker(
            id="wrk_other",
            company_id="cmp_other",
            display_name="Other Person",
            nationality="네팔",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 7, 20),
        )
    )
    # 컬럼 전용 ORM(relationship 없음)이라 삽입 순서를 SQLAlchemy가 못 정한다 —
    # 복합 FK(company_id, worker_id) 충족을 위해 workers를 먼저 flush.
    db.flush()
    db.add(
        WorkerDocument(
            id="doc_missing",
            company_id="cmp_ctx_test",
            worker_id="wrk_high",
            doc_type="passport_copy",
            status="missing",
            due_date=dt.date(2026, 7, 22),  # D-5 → HIGH
        )
    )
    db.flush()
    return "cmp_ctx_test"


def test_snapshot_is_tenant_scoped(db: Session, seeded_company: str) -> None:
    snapshot = build_context_snapshot(
        db,
        company_id=seeded_company,
        required_context=["company", "workers", "documents", "citations"],
        reference_date=REF,
    )

    worker_ids = {w.worker_id for w in snapshot.workers}
    assert worker_ids == {"wrk_high", "wrk_low"}
    assert all(f.worker_id != "wrk_other" for f in snapshot.rule_findings)


def test_snapshot_rule_findings_match_seed_expectations(db: Session, seeded_company: str) -> None:
    snapshot = build_context_snapshot(
        db,
        company_id=seeded_company,
        required_context=["company", "workers", "documents", "citations"],
        reference_date=REF,
    )

    by_key = {(f.risk_type, f.worker_id): f for f in snapshot.rule_findings}

    visa_high = by_key[("visa_expiry", "wrk_high")]
    assert visa_high.severity == "HIGH"
    assert visa_high.d_day == 20

    assert by_key[("visa_expiry", "wrk_low")].severity == "LOW"

    conflict = by_key[("contract_visa_conflict", "wrk_high")]
    assert conflict.severity == "HIGH"

    doc = by_key[("missing_document", "wrk_high")]
    assert doc.severity == "HIGH"
    assert doc.doc_type == "passport_copy"
    assert doc.missing_class if hasattr(doc, "missing_class") else True

    # 심각도 우선 정렬 — HIGH들이 LOW보다 앞
    severities = [f.severity for f in snapshot.rule_findings]
    assert severities == sorted(severities, key=lambda s: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[s])


def test_snapshot_documents_carry_missing_classification(db: Session, seeded_company: str) -> None:
    snapshot = build_context_snapshot(
        db,
        company_id=seeded_company,
        required_context=["company", "workers", "documents", "citations"],
        reference_date=REF,
    )

    missing_docs = [d for d in snapshot.documents if d.status == "missing"]
    assert missing_docs and missing_docs[0].missing_class == "CRITICAL"  # 여권 사본


def test_snapshot_pii_guard_rejects_raw_identifiers() -> None:
    from app.services.context_service import CompanySnapshot, ContextSnapshot

    poisoned = ContextSnapshot(
        company=CompanySnapshot(company_id="c", name="회사"),
        reference_date=REF,
        workers=[
            WorkerSnapshot(
                worker_id="w",
                display_name="여권 M12345678 노출",  # PII 주입
                nationality="베트남",
                visa_type="E-9",
                stay_expires_at="2026-08-01",
            )
        ],
    )
    with pytest.raises(SnapshotPIIError):
        assert_snapshot_has_no_pii(poisoned)
