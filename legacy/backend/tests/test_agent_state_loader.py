from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.models.company import Company
from backend.app.models.hiring import Candidate
from backend.app.models.worker import Worker
from backend.app.services.context_data_service import (
    calculate_candidate_readiness,
    get_company_data,
    get_worker_profile_data,
)


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def test_context_data_service_populates_normalized_contexts_from_db() -> None:
    db = _db()
    db.add(Company(id="company-1", name="테스트 제조", industry="제조", region="서울"))
    db.add(
        Worker(
            id="worker-1",
            company_id="company-1",
            name="Nguyen Van A",
            nationality="Vietnam",
            preferred_language="vi",
            visa_type="E-9",
            visa_expires_at="2026-06-01",
        )
    )
    db.commit()

    company = get_company_data("company-1", db=db)
    worker = get_worker_profile_data("worker-1", db=db)

    assert company is not None
    assert company["id"] == "company-1"
    assert company["region"] == "서울"
    assert worker is not None
    assert worker["id"] == "worker-1"
    assert worker["visa_type"] == "E-9"


def test_context_data_service_returns_none_for_missing_context() -> None:
    db = _db()

    assert get_company_data("missing-company", db=db) is None
    assert get_worker_profile_data("missing-worker", db=db) is None


def test_candidate_readiness_from_db_uses_missing_info_not_scores() -> None:
    db = _db()
    db.add(
        Candidate(
            id="candidate-1",
            company_id="company-1",
            nationality="VN",
            desired_role="assembly",
            passport=True,
            photo=False,
            health_check=False,
            understood_housing=True,
            understood_shift=False,
        )
    )
    db.commit()

    readiness = calculate_candidate_readiness(
        candidate_id="candidate-1",
        company_id="company-1",
        requested_role="assembly",
        db=db,
    )

    assert readiness[0]["candidate_id"] == "candidate-1"
    assert readiness[0]["readiness_status"] == "missing_required_info"
    assert "photo" in readiness[0]["missing_or_unconfirmed_items"]
    assert "candidate_score" not in readiness[0]
