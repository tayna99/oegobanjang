from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft
from backend.app.services.contact_persistence_service import (
    save_message_draft_result,
    save_worker_reply_summary_result,
)
from backend.app.services.handoff_persistence_service import save_handoff_package_draft


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def _client_with_db(db: Session) -> TestClient:
    def override_db():
        return db

    app.dependency_overrides[get_sync_db] = override_db
    return TestClient(app)


def _clear_client_override() -> None:
    app.dependency_overrides.pop(get_sync_db, None)


def _message_result() -> dict:
    return {
        "worker_id": "worker-demo-001",
        "language_code": "vi",
        "message_purpose": "safety_training_notice",
        "status": "SUCCESS",
        "korean_text": "5월 10일 10시에 교육장에서 안전교육이 있습니다.",
        "translated_text": "Có buổi đào tạo an toàn vào ngày 10 tháng 5 lúc 10 giờ.",
        "approval_required": True,
        "citations": [{"source_id": "mock_safety_source"}],
        "evidence_events": [
            {
                "event_type": "message_draft_created",
                "agent_name": "multilingual_contact_agent",
                "summary": "베트남어 안전교육 안내 메시지 초안이 생성됨",
                "source_ids": ["mock_safety_source"],
                "approval_required": True,
            }
        ],
        "risk_flags": ["APPROVAL_REQUIRED_FOR_SEND"],
    }


def _worker_reply_result() -> dict:
    return {
        "worker_id": "worker-demo-001",
        "language_code": "vi",
        "status": "SUCCESS",
        "translated_ko": "여권은 보유한 것으로 보이며 사진은 내일 제출 가능하다는 답변입니다.",
        "summary_ko": "근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘",
        "status_update_candidates": [
            {
                "candidate_type": "passport_received_candidate",
                "field": "passport",
                "candidate_status": "available",
                "is_final": False,
            }
        ],
        "approval_required": True,
        "manager_review_required": True,
        "evidence_events": [
            {
                "event_type": "status_update_candidate_created",
                "agent_name": "multilingual_contact_agent",
                "summary": "서류 상태 업데이트 후보가 생성됨",
                "source_ids": [],
                "approval_required": True,
            }
        ],
        "risk_flags": ["MANAGER_REVIEW_REQUIRED"],
    }


def _handoff_draft() -> dict:
    return {
        "package_type": "expert_handoff_draft",
        "case_type": "stay_extension",
        "case_summary": {
            "summary": "체류만료가 임박하여 서류 누락 여부 확인이 필요합니다.",
            "risk_level": "HIGH",
        },
        "worker_summary": {
            "masked_worker_id": "worker_***",
            "visa_type": "E-9",
            "stay_expires_at": "2026-06-01",
            "contract_ends_at": "2026-05-25",
        },
        "document_summary": {"missing_documents": ["passport_copy"]},
        "contact_summary": {
            "last_contact_summary": "근로자가 사진 추후 제출 의사를 밝혔습니다.",
            "message_draft_exists": True,
            "raw_worker_reply_included": False,
            "full_translation_included": False,
        },
        "evidence": {
            "citation_ids": ["gov24_stay_extension"],
            "evidence_log_ids": [],
            "not_for_legal_judgment": True,
        },
        "approval": {"approval_required": True, "status": "PENDING"},
        "approval_required": True,
        "not_for_legal_judgment": True,
        "raw_worker_reply_included": False,
        "full_translation_included": False,
        "message_body_included": False,
        "handoff_ready": True,
        "handoff_blockers": [],
        "risk_flags": ["D-30 임박"],
    }


def _save_message(db: Session) -> ContactMessage:
    return save_message_draft_result(
        db,
        agent_result=_message_result(),
        company_id="company-demo-001",
        created_by="manager-demo",
        request_id="request-demo",
    )


def _save_candidate(db: Session) -> StatusUpdateCandidate:
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=_worker_reply_result(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
        request_id="request-demo",
        worker_reply="Tôi có hộ chiếu.",
    )
    return candidates[0]


def _save_handoff(db: Session) -> dict:
    return save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_handoff_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
        created_by="manager-demo",
    )


def test_list_approvals_defaults_to_pending_for_same_company() -> None:
    db = _db()
    message = _save_message(db)
    other_message = save_message_draft_result(
        db,
        agent_result=_message_result(),
        company_id="company-other-001",
        created_by="manager-demo",
        request_id="request-other",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/approvals",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [item["approval_id"] for item in body["items"]] == [message.approval_id]
    assert other_message.approval_id not in json.dumps(body)
    assert body["items"][0]["approval_status"] == "PENDING"
    assert body["items"][0]["target_type"] == "contact_message"
    assert body["items"][0]["target"]["message_purpose"] == "safety_training_notice"
    _assert_safe_payload(body)


@pytest.mark.parametrize(
    ("status", "expected_status"),
    [
        ("PENDING", "PENDING"),
        ("APPROVED", "APPROVED"),
        ("REJECTED", "REJECTED"),
    ],
)
def test_list_approvals_filters_by_status(
    status: str,
    expected_status: str,
) -> None:
    db = _db()
    pending_message = _save_message(db)
    approved_message = _save_message(db)
    rejected_message = _save_message(db)
    db.get(Approval, approved_message.approval_id).status = "APPROVED"
    approved_message.status = "APPROVED"
    db.get(Approval, rejected_message.approval_id).status = "REJECTED"
    rejected_message.status = "REJECTED"
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals?status={status}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["approval_status"] == expected_status
    if status == "PENDING":
        assert item["approval_id"] == pending_message.approval_id
    elif status == "APPROVED":
        assert item["approval_id"] == approved_message.approval_id
    else:
        assert item["approval_id"] == rejected_message.approval_id
    _assert_safe_payload(body)


@pytest.mark.parametrize(
    ("target_type", "expected_field"),
    [
        ("contact_message", "message_purpose"),
        ("status_update_candidate", "target_key"),
        ("handoff_package_draft", "package_type"),
    ],
)
def test_list_approvals_filters_by_target_type(
    target_type: str,
    expected_field: str,
) -> None:
    db = _db()
    _save_message(db)
    _save_candidate(db)
    _save_handoff(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals?target_type={target_type}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["target_type"] == target_type
    assert expected_field in body["items"][0]["target"]
    _assert_safe_payload(body)


def test_list_approvals_without_company_header_returns_403() -> None:
    db = _db()
    _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get("/api/v1/approvals")
    finally:
        _clear_client_override()

    assert response.status_code == 403
    _assert_safe_payload(response.json())


@pytest.mark.parametrize(
    "query",
    [
        "status=UNKNOWN",
        "target_type=unsupported_target",
    ],
)
def test_list_approvals_rejects_unknown_filters(query: str) -> None:
    db = _db()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals?{query}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 400
    _assert_safe_payload(response.json())


def test_list_approvals_clamps_limit_and_offset() -> None:
    db = _db()
    _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/approvals?limit=200&offset=-10",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["limit"] == 100
    assert body["offset"] == 0
    assert body["total"] == 1
    _assert_safe_payload(body)


def test_get_contact_message_approval_success_for_same_company() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals/{message.approval_id}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approval_id"] == message.approval_id
    assert body["target_type"] == "contact_message"
    assert body["target_id"] == message.id
    assert body["approval_status"] == "PENDING"
    assert body["target_status"] == "PENDING_APPROVAL"
    assert body["approval_required"] is True
    _assert_safe_payload(body)


def test_get_approval_with_other_company_returns_403_without_sensitive_data() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals/{message.approval_id}",
            headers={"X-Company-Id": "company-other-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 403
    _assert_safe_payload(response.json())


def test_get_approval_without_company_header_returns_403() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(f"/api/v1/approvals/{message.approval_id}")
    finally:
        _clear_client_override()

    assert response.status_code == 403


def test_get_missing_approval_returns_404() -> None:
    db = _db()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/approvals/missing-approval",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 404


def test_approve_contact_message_updates_review_state_without_sending() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{message.approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo", "reason": "검토 완료"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approval_status"] == "APPROVED"
    assert body["target_status"] == "APPROVED"
    _assert_safe_payload(body)

    saved_message = db.get(ContactMessage, message.id)
    approval = db.get(Approval, message.approval_id)
    assert saved_message.status == "APPROVED"
    assert saved_message.sent_at is None
    assert approval.status == "APPROVED"
    assert approval.reason == "검토 완료"


def test_approve_status_update_candidate_without_applying_worker_documents() -> None:
    db = _db()
    candidate = _save_candidate(db)
    original_candidate_status = candidate.candidate_status
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{candidate.approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target_type"] == "status_update_candidate"
    assert body["approval_status"] == "APPROVED"
    assert body["target_status"] == "APPROVED"
    _assert_safe_payload(body)

    saved_candidate = db.get(StatusUpdateCandidate, candidate.id)
    approval = db.get(Approval, candidate.approval_id)
    assert saved_candidate.status == "APPROVED"
    assert saved_candidate.status != "APPLIED"
    assert saved_candidate.candidate_status == original_candidate_status
    assert approval.status == "APPROVED"


def test_approve_handoff_package_draft_without_transfer() -> None:
    db = _db()
    result = _save_handoff(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{result['approval_id']}/approve",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target_type"] == "handoff_package_draft"
    assert body["approval_status"] == "APPROVED"
    assert body["target_status"] == "APPROVED"
    _assert_safe_payload(body)

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    assert draft.status == "APPROVED"
    assert draft.transferred_at is None
    assert approval.status == "APPROVED"


def test_reject_contact_message_updates_target_status() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{message.approval_id}/reject",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo", "reason": "보완 필요"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approval_status"] == "REJECTED"
    assert body["target_status"] == "REJECTED"
    _assert_safe_payload(body)

    saved_message = db.get(ContactMessage, message.id)
    approval = db.get(Approval, message.approval_id)
    assert saved_message.status == "REJECTED"
    assert saved_message.sent_at is None
    assert approval.status == "REJECTED"


def test_reviewed_approval_reprocessing_returns_409() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        first = client.post(
            f"/api/v1/approvals/{message.approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
        second = client.post(
            f"/api/v1/approvals/{message.approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert first.status_code == 200, first.text
    assert second.status_code == 409
    _assert_safe_payload(second.json())


def test_rejected_approval_reprocessing_returns_409() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        first = client.post(
            f"/api/v1/approvals/{message.approval_id}/reject",
            headers={"X-Company-Id": "company-demo-001"},
        )
        second = client.post(
            f"/api/v1/approvals/{message.approval_id}/reject",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert first.status_code == 200, first.text
    assert second.status_code == 409
    _assert_safe_payload(second.json())


def test_missing_target_row_returns_409() -> None:
    db = _db()
    message = _save_message(db)
    approval_id = message.approval_id
    db.delete(message)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 409
    _assert_safe_payload(response.json())


def test_unsupported_target_type_returns_409() -> None:
    db = _db()
    approval = Approval(
        target_type="unsupported_target",
        target_id="target-demo",
        status="PENDING",
    )
    db.add(approval)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/approvals/{approval.id}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 409
    _assert_safe_payload(response.json())


def test_approval_review_writes_summary_only_evidence_log() -> None:
    db = _db()
    message = _save_message(db)
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/approvals/{message.approval_id}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        _clear_client_override()

    assert response.status_code == 200, response.text
    logs = db.scalars(select(EvidenceLog)).all()
    review_logs = [
        log for log in logs if log.event_type == "contact_message_approved"
    ]
    assert review_logs
    review_log = review_logs[0]
    assert review_log.summary == "메시지 초안이 승인되었습니다."
    assert review_log.company_id == "company-demo-001"
    assert review_log.approval_id == message.approval_id

    payload = json.dumps(
        {
            "summary": review_log.summary,
            "source_ids": review_log.source_ids,
            "risk_flags": review_log.risk_flags,
        },
        ensure_ascii=False,
    )
    assert "5월 10일 10시에 교육장에서 안전교육" not in payload
    assert "Có buổi đào tạo an toàn" not in payload
    assert "worker-demo-001" not in payload
    assert "Tôi có hộ chiếu" not in payload
    assert "translated_ko" not in payload
    assert "package_json" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload


def _assert_safe_payload(value: dict) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    assert "5월 10일 10시에 교육장에서 안전교육" not in payload
    assert "Có buổi đào tạo an toàn" not in payload
    assert "Tôi có hộ chiếu" not in payload
    assert "translated_ko" not in payload
    assert "package_json" not in payload
    assert "worker-demo-001" not in payload
    assert "worker_***" not in payload
    assert "passport_copy" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload
