from app.services.daily_briefing_service import (
    CandidateDocumentStatusRecord,
    CandidateRecord,
    DailyBriefingService,
    InMemoryDailyBriefingRepository,
    build_seed_repository,
)


def test_daily_briefing_generates_core_mvp_result() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )

    assert result.briefing_run_id == "brf_company_001_2026-05-08"
    assert result.risk_summary.total_count == 6
    assert result.risk_summary.critical_count == 2
    assert result.risk_summary.high_count == 3
    assert result.risk_summary.medium_count == 1
    assert result.approval_required is True
    assert {item.risk_type for item in result.items} == {
        "contract_visa_conflict",
        "quota_review",
        "reporting_deadline",
        "visa_expiry",
        "missing_document",
    }
    assert any(action.action_type == "request_document" for action in result.recommended_actions)
    assert any(action.action_type == "create_handoff" for action in result.recommended_actions)
    assert all(action.status == "pending_approval" for action in result.recommended_actions)
    assert result.citation_summaries
    assert result.evidence_event_ids
    assert any(action.label == "누락서류 요청 초안 생성" for action in result.recommended_actions)
    assert any(summary.title == "체류기간 만료 전 갱신 준비 안내" for summary in result.citation_summaries)
    assert any(summary.title == "계약 종료일과 체류만료일 충돌 검토 안내" for summary in result.citation_summaries)
    assert any(summary.title == "고용변동 신고기한 검토 안내" for summary in result.citation_summaries)
    assert any(summary.title == "E-9 고용 쿼터 검토 안내" for summary in result.citation_summaries)


def test_daily_briefing_generates_contract_visa_conflict_item_and_handoff() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )

    conflict_item = next(item for item in result.items if item.risk_type == "contract_visa_conflict")
    assert conflict_item.subject_id == "worker_001"
    assert conflict_item.severity == "HIGH"
    assert conflict_item.d_day == 30
    assert conflict_item.citation_ids == ["cit_contract_visa_conflict"]

    conflict_actions = [
        action for action in result.recommended_actions if action.action_id in conflict_item.next_action_ids
    ]
    assert [action.action_type for action in conflict_actions] == ["create_handoff"]
    preview = service.get_handoff_preview(conflict_actions[0].action_id)
    assert preview.content_redacted["risk_summary"]["risk_type"] == "contract_visa_conflict"
    assert "계약" in " ".join(preview.content_redacted["recommended_questions"])


def test_daily_briefing_generates_reporting_deadline_item() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )

    item = next(item for item in result.items if item.risk_type == "reporting_deadline")
    assert item.subject_type == "case"
    assert item.subject_id == "change_evt_001"
    assert item.severity == "HIGH"
    assert item.d_day == 3
    assert item.citation_ids == ["cit_reporting_deadline"]


def test_daily_briefing_generates_quota_review_item_without_confirming_eligibility() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )

    item = next(item for item in result.items if item.risk_type == "quota_review")
    assert item.subject_type == "company"
    assert item.subject_id == "company_001"
    assert item.severity == "MEDIUM"
    action = next(action for action in result.recommended_actions if action.action_id in item.next_action_ids)
    preview = service.get_handoff_preview(action.action_id)
    assert preview.content_redacted["quota_review"]["eligibility_confirmed"] is False


def test_daily_briefing_generates_candidate_readiness_without_matching_or_scoring() -> None:
    repository = build_seed_repository()
    repository.candidates.append(
        CandidateRecord(
            candidate_id="candidate_001",
            company_id="company_001",
            display_name_masked="[CANDIDATE_001]",
            raw_name="Candidate Private Name",
            status="registered",
        )
    )
    repository.candidate_documents.append(
        CandidateDocumentStatusRecord(
            candidate_id="candidate_001",
            document_type="passport_copy",
            status="missing",
            required=True,
            due_date="2026-05-10",
        )
    )
    service = DailyBriefingService(repository)

    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )

    item = next(item for item in result.items if item.risk_type == "candidate_readiness")
    assert item.subject_type == "candidate"
    assert item.subject_id == "candidate_001"
    assert item.severity == "HIGH"
    assert item.missing_documents == ["passport_copy"]
    payload = result.model_dump_json()
    assert "Candidate Private Name" not in payload
    assert "matching_score" not in payload
    assert "recommend_candidate" not in payload


def test_no_risk_briefing_returns_empty_items_without_approval() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_no_risks",
        date="2026-05-08",
        user_role="manager",
    )

    assert result.items == []
    assert result.recommended_actions == []
    assert result.risk_summary.total_count == 0
    assert result.approval_required is False
    assert result.evidence_event_ids


def test_daily_briefing_uses_company_timezone_today_when_date_omitted() -> None:
    service = DailyBriefingService(build_seed_repository())

    result = service.run_daily_briefing(
        company_id="company_001",
        date=None,
        user_role="manager",
    )

    assert result.date
    assert result.briefing_run_id == f"brf_company_001_{result.date}"


def test_tenant_scope_violation_uses_standard_error() -> None:
    service = DailyBriefingService(build_seed_repository())

    try:
        service.run_daily_briefing(
            company_id="company_001",
            date="2026-05-08",
            user_role="manager",
            allowed_company_ids=["company_other"],
        )
    except PermissionError as exc:
        assert exc.args[0] == "TENANT_SCOPE_VIOLATION"
    else:
        raise AssertionError("expected tenant scope violation")


def test_repository_transaction_rolls_back_on_save_failure() -> None:
    repository = InMemoryDailyBriefingRepository.fail_on_save_fixture()
    service = DailyBriefingService(repository)

    try:
        service.run_daily_briefing(
            company_id="company_001",
            date="2026-05-08",
            user_role="manager",
        )
    except RuntimeError as exc:
        assert exc.args[0] == "STATE_SAVE_FAILED"
    else:
        raise AssertionError("expected state save failure")

    assert repository.briefings == {}
    assert repository.cases == {}
    assert repository.actions == {}
    assert repository.approvals == {}
    assert repository.evidence_events == {}


def test_handoff_preview_uses_readable_korean_internal_questions() -> None:
    service = DailyBriefingService(build_seed_repository())
    result = service.run_daily_briefing(
        company_id="company_001",
        date="2026-05-08",
        user_role="manager",
    )
    handoff_action = next(action for action in result.recommended_actions if action.action_type == "create_handoff")
    preview = service.get_handoff_preview(handoff_action.action_id)

    assert preview.content_redacted["recommended_questions"] == [
        "검토에 필요한 추가 서류가 있는지 확인해 주세요.",
        "체류/계약 일정 충돌 여부를 전문가가 확인해 주세요.",
    ]
