from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_evidence_events_use_v1_schema_and_do_not_store_raw_pii() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    events = [repository.evidence_events[event_id] for event_id in result.evidence_event_ids]

    assert {event.event_type for event in events} >= {
        "input_received",
        "state_loaded",
        "risk_flagged",
        "approval_requested",
        "handoff_preview_generated",
    }
    assert all(event.event_version == "v1" for event in events)
    assert all(event.hash_algorithm == "sha256" for event in events)
    rendered = "\n".join(event.model_dump_json() for event in events)
    assert "Nguyen" not in rendered
    assert "Tran" not in rendered
