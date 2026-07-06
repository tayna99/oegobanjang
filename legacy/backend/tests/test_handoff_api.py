from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.db.session import get_sync_db
from backend.app.main import app
from backend.app.models.approval import Approval
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft
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


def _draft() -> dict:
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
        "document_summary": {
            "submitted_documents": ["alien_registration"],
            "missing_documents": ["passport_copy"],
        },
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


def _client_with_db(db: Session) -> TestClient:
    def override_db():
        return db

    app.dependency_overrides[get_sync_db] = override_db
    return TestClient(app)


def test_get_handoff_package_draft_success_returns_safe_detail() -> None:
    db = _db()
    worker_id = "worker-demo-001"
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == result["handoff_package_draft_id"]
    assert body["package_type"] == "expert_handoff_draft"
    assert body["status"] == "PENDING_APPROVAL"
    assert body["approval_required"] is True
    assert body["approval_id"] == result["approval_id"]
    assert body["approval_status"] == "PENDING"
    assert body["transferred_at"] is None
    assert body["not_for_legal_judgment"] is True
    assert body["worker_summary"]["masked_worker_id"] == "worker_***"
    assert body["worker_summary"]["visa_type"] == "E-9"
    assert body["contact_summary"]["raw_worker_reply_included"] is False
    assert body["contact_summary"]["full_translation_included"] is False
    assert body["contact_summary"]["message_body_included"] is False

    payload = json.dumps(body, ensure_ascii=False)
    assert worker_id not in payload
    assert "worker_name" not in payload
    assert "nationality" not in payload
    assert "Tôi có hộ chiếu" not in payload
    assert "translated_ko" not in payload
    assert "안녕하세요. 여권 사본" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload


def test_get_handoff_package_draft_missing_returns_404() -> None:
    db = _db()
    client = _client_with_db(db)

    try:
        response = client.get(
            "/api/v1/handoff-package-drafts/missing-draft",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 404


def test_get_handoff_package_draft_is_read_only() -> None:
    db = _db()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    draft_before = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval_before = db.get(Approval, result["approval_id"])
    before_status = draft_before.status
    before_transferred_at = draft_before.transferred_at
    before_approval_status = approval_before.status
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    draft_after = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval_after = db.get(Approval, result["approval_id"])
    assert draft_after.status == before_status
    assert draft_after.transferred_at == before_transferred_at
    assert approval_after.status == before_approval_status


def test_get_handoff_package_draft_wrong_company_returns_403_without_sensitive_data() -> None:
    db = _db()
    worker_id = "worker-demo-001"
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}",
            headers={"X-Company-Id": "company-other-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 403
    payload = json.dumps(response.json(), ensure_ascii=False)
    assert worker_id not in payload
    assert "worker_***" not in payload
    assert "체류만료" not in payload
    assert "passport_copy" not in payload


def test_get_handoff_package_draft_missing_company_header_returns_403() -> None:
    db = _db()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.get(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}"
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 403


def test_approve_handoff_package_draft_success_without_sensitive_response() -> None:
    db = _db()
    worker_id = "worker-demo-001"
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/approve",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo", "reason": "검토 완료"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["draft_id"] == result["handoff_package_draft_id"]
    assert body["approval_id"] == result["approval_id"]
    assert body["status"] == "APPROVED"
    assert body["approval_status"] == "APPROVED"
    assert body["transferred_at"] is None

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    logs = db.query(EvidenceLog).all()
    assert draft.status == "APPROVED"
    assert draft.transferred_at is None
    assert approval.status == "APPROVED"
    assert any(log.event_type == "handoff_package_draft_approved" for log in logs)
    assert any(
        log.summary == "전문가 검토용 handoff package 초안이 승인되었습니다."
        for log in logs
    )

    payload = json.dumps(body, ensure_ascii=False)
    assert "package_json" not in payload
    assert worker_id not in payload
    assert "M12345678" not in payload
    assert "worker_reply" not in payload
    assert "translated_ko" not in payload


def test_reject_handoff_package_draft_success_without_sensitive_response() -> None:
    db = _db()
    worker_id = "worker-demo-001"
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        response = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/reject",
            headers={"X-Company-Id": "company-demo-001"},
            json={"reviewed_by": "manager-demo", "reason": "보완 필요"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["draft_id"] == result["handoff_package_draft_id"]
    assert body["approval_id"] == result["approval_id"]
    assert body["status"] == "REJECTED"
    assert body["approval_status"] == "REJECTED"
    assert body["transferred_at"] is None

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    logs = db.query(EvidenceLog).all()
    assert draft.status == "REJECTED"
    assert draft.transferred_at is None
    assert approval.status == "REJECTED"
    assert approval.reason == "보완 필요"
    assert any(log.event_type == "handoff_package_draft_rejected" for log in logs)
    assert any(
        log.summary == "전문가 검토용 handoff package 초안이 반려되었습니다."
        for log in logs
    )

    payload = json.dumps(body, ensure_ascii=False)
    assert "package_json" not in payload
    assert worker_id not in payload
    assert "M12345678" not in payload
    assert "worker_reply" not in payload
    assert "translated_ko" not in payload


def test_handoff_review_wrong_or_missing_company_returns_403_without_sensitive_data() -> None:
    db = _db()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        wrong_scope = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/approve",
            headers={"X-Company-Id": "company-other-001"},
        )
        missing_scope = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/reject"
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert wrong_scope.status_code == 403
    assert missing_scope.status_code == 403
    for response in (wrong_scope, missing_scope):
        payload = json.dumps(response.json(), ensure_ascii=False)
        assert "worker-demo-001" not in payload
        assert "worker_***" not in payload
        assert "체류만료" not in payload
        assert "passport_copy" not in payload


def test_handoff_review_missing_draft_returns_404() -> None:
    db = _db()
    client = _client_with_db(db)

    try:
        response = client.post(
            "/api/v1/handoff-package-drafts/missing-draft/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert response.status_code == 404


def test_handoff_review_reprocessing_returns_409_without_sensitive_data() -> None:
    db = _db()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        first = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
        second = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/approve",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert first.status_code == 200, first.text
    assert second.status_code == 409
    payload = json.dumps(second.json(), ensure_ascii=False)
    assert "worker-demo-001" not in payload
    assert "worker_***" not in payload
    assert "체류만료" not in payload


def test_handoff_reject_reprocessing_returns_409() -> None:
    db = _db()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    client = _client_with_db(db)

    try:
        first = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/reject",
            headers={"X-Company-Id": "company-demo-001"},
        )
        second = client.post(
            f"/api/v1/handoff-package-drafts/{result['handoff_package_draft_id']}/reject",
            headers={"X-Company-Id": "company-demo-001"},
        )
    finally:
        app.dependency_overrides.pop(get_sync_db, None)

    assert first.status_code == 200, first.text
    assert second.status_code == 409
