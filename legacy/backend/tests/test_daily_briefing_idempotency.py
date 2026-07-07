from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_same_source_snapshot_returns_same_briefing_without_duplicate_actions() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)

    first = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    second = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

    assert second.briefing_run_id == first.briefing_run_id
    assert second.source_snapshot_hash == first.source_snapshot_hash
    assert second.rerun_count == 1
    assert [action.action_id for action in second.recommended_actions] == [
        action.action_id for action in first.recommended_actions
    ]
    assert len(repository.actions) == len(first.recommended_actions)


def test_changed_source_snapshot_updates_same_briefing_run() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)

    first = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    repository.documents[0].status = "submitted"
    second = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

    assert second.briefing_run_id == first.briefing_run_id
    assert second.source_snapshot_hash != first.source_snapshot_hash
    assert second.rerun_count == 1
    assert len(repository.actions) <= len(first.recommended_actions)
