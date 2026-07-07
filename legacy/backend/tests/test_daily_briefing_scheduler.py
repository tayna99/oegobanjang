from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from app.models.daily_briefing import DailyBriefingResultRow
from app.services.daily_briefing_scheduler import (
    DailyBriefingBackgroundScheduler,
    run_scheduled_daily_briefings,
)


def test_scheduled_daily_briefing_runs_for_selected_companies():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        result = run_scheduled_daily_briefings(
            db,
            company_ids=["company_001", "company_no_risks"],
            run_date="2026-05-08",
        )

        assert result.status == "completed"
        assert result.total_companies == 2
        assert result.succeeded_count == 2
        assert result.failed_count == 0
        assert len(result.briefing_run_ids) == 2
        assert (
            db.query(DailyBriefingResultRow)
            .filter(DailyBriefingResultRow.company_id.in_(["company_001", "company_no_risks"]))
            .count()
            == 2
        )
    finally:
        db.close()


def test_scheduled_daily_briefing_captures_company_failures():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        result = run_scheduled_daily_briefings(
            db,
            company_ids=["company_001", "missing_company"],
            run_date="2026-05-08",
        )

        assert result.status == "partial_failure"
        assert result.succeeded_count == 1
        assert result.failed_count == 1
        assert result.errors[0].company_id == "missing_company"
        assert result.errors[0].error_code == "COMPANY_NOT_FOUND"
    finally:
        db.close()


def test_background_scheduler_run_once_uses_same_service_path():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    scheduler = DailyBriefingBackgroundScheduler(
        SessionLocal,
        company_ids=["company_001"],
        timezone_name="Asia/Seoul",
    )

    result = scheduler.run_once(run_date="2026-05-08")

    assert result.status == "completed"
    assert result.succeeded_count == 1
    db = SessionLocal()
    try:
        assert db.query(DailyBriefingResultRow).count() == 1
    finally:
        db.close()
