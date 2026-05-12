from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_create_handoff_action_has_redacted_preview() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    handoff_actions = [
        action for action in result.recommended_actions if action.action_type == "create_handoff"
    ]

    assert handoff_actions
    preview = service.get_handoff_preview(handoff_actions[0].action_id)
    assert preview.case_id == handoff_actions[0].case_id
    assert "Nguyen V." in str(preview.content_redacted)
    assert "Nguyen Van A" not in str(preview.content_redacted)
    assert preview.citation_ids


def test_handoff_preview_is_blocked_when_redaction_fails() -> None:
    repository = build_seed_repository()
    repository.force_redaction_failure = True
    service = DailyBriefingService(repository)

    try:
        service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    except RuntimeError as exc:
        assert exc.args[0] == "PII_REDACTION_FAILED"
    else:
        raise AssertionError("expected redaction failure")


def test_request_document_action_returns_real_message_draft_without_external_send() -> None:
    service = DailyBriefingService(build_seed_repository())
    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    request_action = next(action for action in result.recommended_actions if action.action_type == "request_document")

    draft = service.get_document_request_draft(request_action.action_id)

    assert draft.action_id == request_action.action_id
    assert draft.status == "preview_only"
    assert draft.approval_required is True
    assert draft.external_send_performed is False
    assert "passport_copy" in draft.missing_documents
    assert "Tran T." in draft.korean_text
    assert "Tran Thi B" not in draft.model_dump_json()
    assert draft.translated_text
