"""Risk Rule Engine 순수 함수 — legacy 임계값 계약 고정 (DB 불필요)."""

from __future__ import annotations

from app.domain.rules import (
    DocumentStatusRecord,
    canonical_document_type,
    classify_missing_document,
    evaluate_contract_visa_conflict_risk,
    evaluate_missing_document_risk,
    evaluate_quota_review_risk,
    evaluate_reporting_deadline_risk,
    evaluate_visa_expiry_risk,
    higher_risk,
    preparation_days_for,
    visa_risk_level,
)

REF = "2026-07-17"


def test_visa_expiry_thresholds() -> None:
    assert evaluate_visa_expiry_risk(REF, "2026-07-10").severity == "CRITICAL"  # 만료 D+7
    assert evaluate_visa_expiry_risk(REF, "2026-07-10").days_overdue == 7
    assert evaluate_visa_expiry_risk(REF, "2026-08-06").severity == "HIGH"  # D-20
    assert evaluate_visa_expiry_risk(REF, "2026-09-10").severity == "MEDIUM"  # D-55
    assert evaluate_visa_expiry_risk(REF, "2026-10-10").severity == "LOW"  # D-85
    assert evaluate_visa_expiry_risk(REF, "2027-01-01").severity == "LOW"


def test_missing_document_thresholds() -> None:
    def doc(status: str = "missing", required: bool = True, due: str | None = None):
        return DocumentStatusRecord(
            worker_id="w1", document_type="passport_copy", status=status, required=required, due_date=due
        )

    assert evaluate_missing_document_risk(REF, doc(status="submitted")).severity == "LOW"
    assert evaluate_missing_document_risk(REF, doc(required=False)).severity == "LOW"
    assert evaluate_missing_document_risk(REF, doc(due=None)).severity == "MEDIUM"
    assert evaluate_missing_document_risk(REF, doc(due="2026-07-10")).severity == "CRITICAL"
    assert evaluate_missing_document_risk(REF, doc(due="2026-07-22")).severity == "HIGH"  # D-5
    assert evaluate_missing_document_risk(REF, doc(due="2026-08-20")).severity == "MEDIUM"


def test_contract_visa_conflict_only_when_contract_outlives_visa() -> None:
    # 계약이 비자보다 먼저 끝나면 충돌 아님
    assert evaluate_contract_visa_conflict_risk(REF, "2026-09-01", "2026-08-01") is None
    # 계약이 비자 만료 후까지 이어지면 비자 잔여일 기준 심각도
    conflict = evaluate_contract_visa_conflict_risk(REF, "2026-08-06", "2027-01-01")
    assert conflict is not None and conflict.severity == "HIGH"  # 비자 D-20
    expired = evaluate_contract_visa_conflict_risk(REF, "2026-07-01", "2027-01-01")
    assert expired is not None and expired.severity == "CRITICAL"


def test_reporting_deadline_thresholds() -> None:
    assert evaluate_reporting_deadline_risk(REF, "2026-07-20", reported_at="2026-07-01") is None
    assert evaluate_reporting_deadline_risk(REF, "2026-07-10", None).severity == "CRITICAL"
    assert evaluate_reporting_deadline_risk(REF, "2026-07-19", None).severity == "HIGH"  # D-2
    assert evaluate_reporting_deadline_risk(REF, "2026-07-23", None).severity == "MEDIUM"  # D-6
    assert evaluate_reporting_deadline_risk(REF, "2026-08-17", None).severity == "LOW"


def test_quota_review_thresholds() -> None:
    assert evaluate_quota_review_risk(None, None) is None
    assert evaluate_quota_review_risk(5, None).severity == "MEDIUM"
    assert evaluate_quota_review_risk(5, 5).severity == "HIGH"
    assert evaluate_quota_review_risk(5, 4).severity == "MEDIUM"
    assert evaluate_quota_review_risk(5, 2) is None


def test_visa_risk_level_uses_preparation_window() -> None:
    # E-9 준비기간 120일: 25%=30 / 50%=60 경계
    assert preparation_days_for("E-9") == 120
    assert preparation_days_for("H-2") == 90  # 미등록 유형은 기본값
    assert visa_risk_level(20, 120) == "CRITICAL"
    assert visa_risk_level(45, 120) == "HIGH"
    assert visa_risk_level(100, 120) == "MEDIUM"
    assert visa_risk_level(150, 120) == "LOW"
    assert visa_risk_level(-10, 120) == "CRITICAL"  # 만료 30일 이내
    assert visa_risk_level(-40, 120) == "HIGH"  # 만료 30일 초과 — 이미 이탈 케이스


def test_document_classification_and_canonicalization() -> None:
    assert classify_missing_document("passport_copy") == "CRITICAL"
    assert classify_missing_document("표준근로계약서") == "CRITICAL"
    assert classify_missing_document("증명사진") == "SUPPLEMENTARY"
    assert canonical_document_type("labor_contract") == "employment_contract"
    assert canonical_document_type("arc_copy") == "alien_registration"
    assert canonical_document_type("passport") == "passport_copy"
    assert higher_risk("HIGH", "MEDIUM") == "HIGH"
