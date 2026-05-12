import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from app.models.daily_briefing import (
    DailyBriefingApproval,
    DailyBriefingCandidateDocumentSource,
    DailyBriefingCandidateSource,
    DailyBriefingCitationSource,
    DailyBriefingCompanySource,
    DailyBriefingDocumentSource,
    DailyBriefingEvidenceEvent,
    DailyBriefingReportingEventSource,
    DailyBriefingResultRow,
    DailyBriefingWorkerSource,
)
from app.services.daily_briefing_service import (
    DailyBriefingService,
    SqlAlchemyDailyBriefingRepository,
    build_repository_from_db_sources,
    build_sqlalchemy_daily_briefing_service,
    build_seed_repository,
)


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def test_sqlalchemy_repository_persists_briefing_across_instances() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        repository = SqlAlchemyDailyBriefingRepository(db, source_repository=build_seed_repository())
        result = DailyBriefingService(repository).run_daily_briefing(
            "company_001",
            "2026-05-08",
            user_role="manager",
        )
        db.commit()

    with session_factory() as db:
        repository = SqlAlchemyDailyBriefingRepository(db, source_repository=build_seed_repository())

        assert result.briefing_run_id in repository.briefings
        assert repository.briefings[result.briefing_run_id].source_snapshot_hash == result.source_snapshot_hash
        assert db.get(DailyBriefingResultRow, result.briefing_run_id) is not None
        assert db.query(DailyBriefingApproval).count() == len(result.recommended_actions)
        assert db.query(DailyBriefingEvidenceEvent).count() == len(result.evidence_event_ids)


def test_sqlalchemy_repository_reuses_actions_on_same_company_date() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        repository = SqlAlchemyDailyBriefingRepository(db, source_repository=build_seed_repository())
        service = DailyBriefingService(repository)

        first = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
        second = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
        db.commit()

        assert second.briefing_run_id == first.briefing_run_id
        assert db.query(DailyBriefingApproval).count() == len(first.recommended_actions)


def test_sqlalchemy_service_uses_db_source_rows_when_present() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        db.add(
            DailyBriefingCompanySource(
                id="company_db",
                company_name="DB Source Company",
                timezone="Asia/Seoul",
                quota_limit="1",
                current_foreign_worker_count="1",
            )
        )
        db.add(
            DailyBriefingWorkerSource(
                id="worker_db_001",
                company_id="company_db",
                display_name_masked="[WORKER_DB_001]",
                raw_name="Private Worker",
                visa_expiry_date="2026-05-20",
                contract_end_date="2026-06-30",
            )
        )
        db.add(
            DailyBriefingDocumentSource(
                id="worker_db_001:passport_copy",
                worker_id="worker_db_001",
                document_type="passport_copy",
                status="missing",
                required=True,
                due_date="2026-05-09",
            )
        )
        db.add(
            DailyBriefingCitationSource(
                id="cit_visa_expiry",
                title="DB citation for visa expiry",
                source_type="official",
                source="DB official source",
                ingest_at="2026-05-01T00:00:00+09:00",
            )
        )
        db.add(
            DailyBriefingCitationSource(
                id="cit_missing_document",
                title="DB citation for missing document",
                source_type="official",
                source="DB official source",
                ingest_at="2026-05-01T00:00:00+09:00",
            )
        )
        db.add(
            DailyBriefingReportingEventSource(
                id="change_db_001",
                company_id="company_db",
                worker_id="worker_db_001",
                event_type="employment_change",
                occurred_at="2026-04-26",
                discovered_at="2026-04-26",
                reporting_due_date="2026-05-11",
                status="open",
            )
        )
        for citation_id in ("cit_contract_visa_conflict", "cit_reporting_deadline", "cit_quota_review"):
            db.add(
                DailyBriefingCitationSource(
                    id=citation_id,
                    title=f"DB citation for {citation_id}",
                    source_type="official",
                    source="DB official source",
                    ingest_at="2026-05-01T00:00:00+09:00",
                )
            )
        db.commit()

        service = build_sqlalchemy_daily_briefing_service(db)
        result = service.run_daily_briefing(
            "company_db",
            "2026-05-08",
            user_role="manager",
        )

        assert result.company_id == "company_db"
        assert result.risk_summary.by_risk_type["reporting_deadline"] == 1
        assert result.risk_summary.by_risk_type["quota_review"] == 1
        assert result.risk_summary.by_risk_type["contract_visa_conflict"] == 1
        assert "Private Worker" not in result.model_dump_json()
        assert any(action.action_type == "request_document" for action in result.recommended_actions)


def test_sqlalchemy_service_uses_db_candidate_source_rows() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        db.add(
            DailyBriefingCompanySource(
                id="company_candidate",
                company_name="Candidate Source Company",
                timezone="Asia/Seoul",
                quota_limit="3",
                current_foreign_worker_count="1",
            )
        )
        db.add(
            DailyBriefingCandidateSource(
                id="candidate_db_001",
                company_id="company_candidate",
                display_name_masked="[CANDIDATE_DB_001]",
                raw_name="Candidate Private Name",
                status="registered",
            )
        )
        db.add(
            DailyBriefingCandidateDocumentSource(
                id="candidate_db_001:passport_copy",
                candidate_id="candidate_db_001",
                document_type="passport_copy",
                status="missing",
                required=True,
                due_date="2026-05-10",
            )
        )
        db.add(
            DailyBriefingCitationSource(
                id="cit_candidate_readiness",
                title="Candidate readiness source",
                source_type="official",
                source="Candidate readiness checklist",
                ingest_at="2026-05-01T00:00:00+09:00",
            )
        )
        db.commit()

        service = build_sqlalchemy_daily_briefing_service(db)
        result = service.run_daily_briefing(
            "company_candidate",
            "2026-05-08",
            user_role="manager",
        )

        item = next(item for item in result.items if item.risk_type == "candidate_readiness")
        assert item.subject_type == "candidate"
        assert item.subject_id == "candidate_db_001"
        assert item.missing_documents == ["passport_copy"]
        assert "Candidate Private Name" not in result.model_dump_json()


def test_db_source_loader_falls_back_to_seed_when_source_tables_empty() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        repository = build_repository_from_db_sources(db, fallback=build_seed_repository())

        assert "company_001" in repository.companies


def test_db_source_loader_blocks_seed_fallback_when_disabled() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        try:
            build_repository_from_db_sources(db, fallback=None)
        except LookupError as exc:
            assert exc.args[0] == "MISSING_SOURCE_DATA"
        else:
            raise AssertionError("Expected empty source tables to fail without seed fallback")


def test_sqlalchemy_service_blocks_seed_source_rows_when_fallback_disabled() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        try:
            build_sqlalchemy_daily_briefing_service(db, allow_seed_source_fallback=False)
        except LookupError as exc:
            assert exc.args[0] == "MISSING_SOURCE_DATA"
        else:
            raise AssertionError("Expected service build to fail without source data")


def test_sqlalchemy_service_persists_seed_source_rows_before_running() -> None:
    session_factory = _session_factory()
    with session_factory() as db:
        assert db.query(DailyBriefingCompanySource).count() == 0

        service = build_sqlalchemy_daily_briefing_service(db)
        result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
        db.commit()

        assert result.company_id == "company_001"
        assert db.query(DailyBriefingCompanySource).count() >= 2
        assert db.query(DailyBriefingWorkerSource).count() >= 4
        assert db.query(DailyBriefingDocumentSource).count() >= 2
        assert db.query(DailyBriefingCitationSource).count() >= 5

    with session_factory() as db:
        worker = db.get(DailyBriefingWorkerSource, "worker_001")
        assert worker is not None
        worker.visa_expiry_date = "2026-12-31"
        db.commit()

        service = build_sqlalchemy_daily_briefing_service(db)
        result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

        worker_001_visa_items = [
            item
            for item in result.items
            if item.subject_id == "worker_001" and item.risk_type == "visa_expiry"
        ]
        assert worker_001_visa_items == []
