from app.services.daily_briefing_service import DailyBriefingService, build_seed_repository


def test_all_generated_actions_are_blocked_until_approved() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

    assert result.recommended_actions
    assert all(action.approval_required for action in result.recommended_actions)
    assert all(action.blocked_until_approved for action in result.recommended_actions)
    assert all(action.status == "pending_approval" for action in result.recommended_actions)


def test_manager_can_approve_action_and_audit_event_is_recorded() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    approval_id = result.recommended_actions[0].approval_id

    response = service.approve_action(approval_id, approver_id="manager_001", user_role="manager")

    assert response.status == "approved"
    assert repository.approvals[approval_id].status == "approved"
    assert repository.actions[response.action_id].status == "approved"
    assert response.evidence_event_id in repository.evidence_events
    assert repository.evidence_events[response.evidence_event_id].event_type == "approval_approved"


def test_viewer_cannot_approve_action() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    approval_id = result.recommended_actions[0].approval_id

    try:
        service.approve_action(approval_id, approver_id="viewer_001", user_role="viewer")
    except PermissionError as exc:
        assert exc.args[0] == "UNAUTHORIZED_ROLE"
    else:
        raise AssertionError("expected unauthorized role")


def test_manager_can_reject_action_and_audit_event_is_recorded() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    action = result.recommended_actions[0]

    response = service.reject_action(
        action.approval_id,
        approver_id="manager_001",
        user_role="manager",
        reason="서류 상태를 먼저 다시 확인해야 합니다.",
    )

    assert response.status == "rejected"
    assert repository.approvals[action.approval_id].status == "rejected"
    assert repository.approvals[action.approval_id].rejection_reason == "서류 상태를 먼저 다시 확인해야 합니다."
    assert repository.actions[action.action_id].status == "rejected"
    assert response.evidence_event_id in repository.evidence_events
    assert repository.evidence_events[response.evidence_event_id].event_type == "approval_rejected"


def test_manager_can_request_revision_and_action_stays_blocked() -> None:
    repository = build_seed_repository()
    service = DailyBriefingService(repository)
    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    action = result.recommended_actions[0]

    response = service.request_revision(
        action.approval_id,
        approver_id="manager_001",
        user_role="manager",
        reason="행정사 질문을 하나 더 추가해 주세요.",
    )

    assert response.status == "revision_requested"
    assert repository.approvals[action.approval_id].status == "revision_requested"
    assert repository.approvals[action.approval_id].revision_reason == "행정사 질문을 하나 더 추가해 주세요."
    assert repository.actions[action.action_id].status == "revision_requested"
    assert repository.actions[action.action_id].blocked_until_approved is True
    assert response.evidence_event_id in repository.evidence_events
    assert repository.evidence_events[response.evidence_event_id].event_type == "approval_revision_requested"
