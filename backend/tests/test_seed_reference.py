"""전역 참조 시드(db/seed_reference.sql)가 룰 엔진 ContextSnapshot에 실리는지 검증.

seed_reference.sql은 "빈 DB에서도 제품이 동작하려면 필요한 전역 참조"(document_requirements·
전역 A/B citations)를 담는다(설계: plans/SEED_DESIGN_2026-07-20.md). db/validate.py가 DDL
불변식을 검증한다면, 이 테스트는 그 시드가 실제로 context_service를 통해 소비되는지 —
즉 이게 비면 룰 엔진이 서류 요건 0으로 공전한다는 전제 — 를 증명한다.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.worker import Worker
from app.services.context_service import build_context_snapshot

SEED_REFERENCE = Path(__file__).resolve().parents[2] / "db" / "seed_reference.sql"


def _load_reference_seed(db: Session) -> None:
    # exec_driver_sql은 SQLAlchemy의 bind-param(:name) 파싱을 우회해 원문 SQL을 그대로
    # psycopg에 넘긴다 — 시드의 타임스탬프 리터럴('...T00:00:00Z')이 bindparam으로 오인되지 않는다.
    db.connection().exec_driver_sql(SEED_REFERENCE.read_text(encoding="utf-8"))
    db.flush()


def test_reference_seed_feeds_document_requirements_into_snapshot(db: Session) -> None:
    _load_reference_seed(db)

    db.add(Company(id="cmp_seed_ref", name="시드참조테스트"))
    db.add(
        Worker(
            id="wrk_ref",
            company_id="cmp_seed_ref",
            display_name="Nguyen Van A",
            nationality="베트남",
            visa_type="E-9",
            stay_expires_at=dt.date(2026, 8, 6),
        )
    )
    db.flush()

    snapshot = build_context_snapshot(
        db,
        company_id="cmp_seed_ref",
        required_context=["company", "workers", "documents", "citations"],
        reference_date="2026-07-17",
    )

    reqs = snapshot.document_requirements
    # 빈 DB였다면 0건 — 참조 시드가 로드되면 전역 요건이 회사 무관하게 실린다.
    assert reqs, "reference seed should populate the snapshot document_requirements"

    visa_e9 = [r for r in reqs if r["case_type"] == "visa_expiry" and r["visa_type"] == "E-9"]
    assert any(r["required_doc"] == "여권 사본" for r in visa_e9), "E-9 연장 필수서류(여권 사본)가 실려야 한다"

    # required_doc 정본은 한국어 라벨(worker_documents·프론트와 동일 언어).
    assert all(any("가" <= ch <= "힣" for ch in r["required_doc"]) for r in reqs)

    # citation_id가 있는 요건은 전역 근거(company_id NULL)를 가리킨다 — 트리거가 강제하는 계약.
    linked = [r for r in reqs if r["citation_id"]]
    assert linked, "적어도 일부 요건은 전역 근거에 연결돼야 한다"
