from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_source_snapshot_hash_is_deterministic_and_excludes_raw_pii() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)

    first = service._source_snapshot_hash("company_001", "2026-05-08")
    second = service._source_snapshot_hash("company_001", "2026-05-08")

    assert first == second
    assert "Nguyen" not in first
    assert "Tran" not in first


def test_source_snapshot_hash_changes_when_document_state_changes() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    before = service._source_snapshot_hash("company_001", "2026-05-08")

    repository.documents[0].status = "submitted"
    after = service._source_snapshot_hash("company_001", "2026-05-08")

    assert after != before


def test_source_snapshot_hash_changes_when_contract_end_date_changes() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    before = service._source_snapshot_hash("company_001", "2026-05-08")

    repository.workers[0].contract_end_date = "2026-08-31"
    after = service._source_snapshot_hash("company_001", "2026-05-08")

    assert after != before
