from app.services.daily_briefing_service import (
    DocumentStatusRecord,
    evaluate_quota_review_risk,
    evaluate_reporting_deadline_risk,
    evaluate_contract_visa_conflict_risk,
    evaluate_missing_document_risk,
    evaluate_visa_expiry_risk,
)


def test_visa_expiry_d30_is_high() -> None:
    result = evaluate_visa_expiry_risk("2026-05-08", "2026-06-07")

    assert result.severity == "HIGH"
    assert result.d_day == 30
    assert result.expired is False


def test_visa_expiry_already_expired_is_critical() -> None:
    result = evaluate_visa_expiry_risk("2026-05-08", "2026-05-05")

    assert result.severity == "CRITICAL"
    assert result.expired is True
    assert result.days_overdue == 3


def test_required_missing_document_overdue_is_critical() -> None:
    document = DocumentStatusRecord(
        worker_id="worker_001",
        document_type="passport_copy",
        status="missing",
        required=True,
        due_date="2026-05-05",
    )

    result = evaluate_missing_document_risk("2026-05-08", document)

    assert result.severity == "CRITICAL"
    assert result.expired is True
    assert result.days_overdue == 3


def test_required_missing_document_without_due_date_is_medium() -> None:
    document = DocumentStatusRecord(
        worker_id="worker_001",
        document_type="passport_copy",
        status="missing",
        required=True,
        due_date=None,
    )

    result = evaluate_missing_document_risk("2026-05-08", document)

    assert result.severity == "MEDIUM"
    assert result.expired is False
    assert result.d_day is None


def test_contract_after_visa_expiry_is_high_conflict_when_visa_expires_soon() -> None:
    result = evaluate_contract_visa_conflict_risk(
        reference_date="2026-05-08",
        visa_expiry_date="2026-06-07",
        contract_end_date="2026-07-31",
    )

    assert result.severity == "HIGH"
    assert result.d_day == 30
    assert result.expired is False


def test_contract_visa_conflict_is_none_when_contract_ends_before_visa() -> None:
    result = evaluate_contract_visa_conflict_risk(
        reference_date="2026-05-08",
        visa_expiry_date="2026-07-31",
        contract_end_date="2026-06-07",
    )

    assert result is None


def test_reporting_deadline_d3_is_high() -> None:
    result = evaluate_reporting_deadline_risk(
        reference_date="2026-05-08",
        reporting_due_date="2026-05-11",
        reported_at=None,
    )

    assert result.severity == "HIGH"
    assert result.d_day == 3


def test_reporting_deadline_already_reported_is_none() -> None:
    result = evaluate_reporting_deadline_risk(
        reference_date="2026-05-08",
        reporting_due_date="2026-05-11",
        reported_at="2026-05-07T09:00:00+09:00",
    )

    assert result is None


def test_quota_review_at_limit_is_high() -> None:
    result = evaluate_quota_review_risk(quota_limit=3, current_foreign_worker_count=3)

    assert result.severity == "HIGH"


def test_quota_review_with_one_remaining_is_medium() -> None:
    result = evaluate_quota_review_risk(quota_limit=3, current_foreign_worker_count=2)

    assert result.severity == "MEDIUM"
