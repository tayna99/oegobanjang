from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft
from backend.app.services.contact_persistence_service import approve_approval
from backend.app.services.handoff_persistence_service import (
    HandoffApprovalConflictError,
    HandoffPackageDraftForbiddenError,
    approve_handoff_package_draft,
    get_handoff_package_draft_detail,
    get_handoff_draft_by_approval_for_company,
    reject_handoff_package_draft,
    save_handoff_package_draft,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
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
            "risk_reasons": ["D-30 임박"],
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
        "approval": {
            "approval_required": True,
            "status": "PENDING",
        },
        "approval_required": True,
        "not_for_legal_judgment": True,
        "raw_worker_reply_included": False,
        "full_translation_included": False,
        "message_body_included": False,
        "handoff_ready": True,
        "handoff_blockers": [],
        "risk_flags": ["D-30 임박"],
    }


def test_save_handoff_package_draft_creates_pending_row_approval_and_evidence() -> None:
    db = _session()
    worker_id = "worker-demo-001"

    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
        created_by="manager-demo",
    )
    db.commit()

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    logs = db.scalars(select(EvidenceLog)).all()

    assert draft is not None
    assert draft.status == "PENDING_APPROVAL"
    assert draft.approval_required is True
    assert draft.transferred_at is None
    assert draft.worker_id == worker_id
    assert draft.company_id == "company-demo-001"
    assert draft.masked_worker_id == "worker_***"
    assert draft.approval_id == approval.id

    assert approval is not None
    assert approval.target_type == "handoff_package_draft"
    assert approval.target_id == draft.id
    assert approval.status == "PENDING"

    assert logs
    assert logs[0].summary == "전문가 검토용 handoff package 초안이 생성되었습니다."
    assert logs[0].approval_id == approval.id
    assert logs[0].company_id == "company-demo-001"
    assert logs[0].worker_id == worker_id

    package_json = draft.package_json
    assert worker_id not in package_json
    assert "Tôi có hộ chiếu" not in package_json
    assert "translated_ko" not in package_json
    assert "안녕하세요. 여권 사본" not in package_json
    assert "M12345678" not in package_json
    assert "900101-1234567" not in package_json
    assert "010-1234-5678" not in package_json
    package = json.loads(package_json)
    assert package["worker_summary"]["masked_worker_id"] == "worker_***"
    assert package["approval"]["status"] == "PENDING"
    assert package["evidence"]["not_for_legal_judgment"] is True


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("worker_reply",), "Tôi có hộ chiếu, ảnh mai gửi."),
        (("translated_ko",), "여권이 있고 사진은 내일 보내겠다는 답변입니다."),
        (("message_body",), "안녕하세요. 여권 사본을 제출해주세요."),
        (("worker_summary", "worker_id"), "worker-demo-001"),
        (("worker_summary", "nationality"), "Vietnam"),
        (("case_summary", "summary"), "여권번호 M12345678 확인됨"),
        (("case_summary", "summary"), "외국인등록번호 900101-1234567 확인됨"),
        (("case_summary", "summary"), "전화번호 010-1234-5678 확인됨"),
        (("case_summary", "summary"), "비자 가능 여부 확정"),
    ],
)
def test_save_handoff_package_draft_rejects_forbidden_package_content(
    path: tuple[str, ...],
    value: str,
) -> None:
    db = _session()
    draft = _draft()
    target = draft
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value

    with pytest.raises(ValueError):
        save_handoff_package_draft(
            db,
            request_id="request-demo",
            handoff_package_draft=draft,
            worker_id="worker-demo-001",
        )


def test_approve_handoff_approval_does_not_transfer_package() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
    )
    db.commit()

    approval = approve_approval(db, result["approval_id"], reviewed_by="manager-demo")
    db.commit()

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    assert approval.status == "APPROVED"
    assert draft.status == "APPROVED"
    assert draft.transferred_at is None


def test_get_handoff_package_draft_detail_returns_safe_detail_only() -> None:
    db = _session()
    worker_id = "worker-demo-001"
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id=worker_id,
        company_id="company-demo-001",
    )
    db.commit()

    detail = get_handoff_package_draft_detail(
        db,
        result["handoff_package_draft_id"],
        "company-demo-001",
    )

    assert detail["id"] == result["handoff_package_draft_id"]
    assert detail["package_type"] == "expert_handoff_draft"
    assert detail["approval_required"] is True
    assert detail["approval_status"] == "PENDING"
    assert detail["transferred_at"] is None
    assert detail["worker_summary"]["masked_worker_id"] == "worker_***"
    assert "worker_id" not in detail["worker_summary"]

    payload = json.dumps(detail, ensure_ascii=False)
    assert worker_id not in payload
    assert "worker_name" not in payload
    assert "nationality" not in payload
    assert "Tôi có hộ chiếu" not in payload
    assert "translated_ko" not in payload
    assert "안녕하세요. 여권 사본" not in payload
    assert "M12345678" not in payload
    assert "900101-1234567" not in payload
    assert "010-1234-5678" not in payload


def test_get_handoff_package_draft_detail_rejects_corrupted_package_json() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    draft.package_json = "{not-valid-json"
    db.commit()

    with pytest.raises(ValueError):
        get_handoff_package_draft_detail(
            db,
            result["handoff_package_draft_id"],
            "company-demo-001",
        )


def test_get_handoff_package_draft_detail_rejects_unsafe_package_json() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    package = json.loads(draft.package_json)
    package["case_summary"]["summary"] = "여권번호 M12345678 확인됨"
    draft.package_json = json.dumps(package, ensure_ascii=False)
    db.commit()

    with pytest.raises(ValueError):
        get_handoff_package_draft_detail(
            db,
            result["handoff_package_draft_id"],
            "company-demo-001",
        )


def test_get_handoff_package_draft_detail_rejects_wrong_company_scope() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    with pytest.raises(HandoffPackageDraftForbiddenError):
        get_handoff_package_draft_detail(
            db,
            result["handoff_package_draft_id"],
            "company-other-001",
        )


def test_get_handoff_package_draft_detail_rejects_missing_company_scope() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    with pytest.raises(HandoffPackageDraftForbiddenError):
        get_handoff_package_draft_detail(db, result["handoff_package_draft_id"], "")


def test_handoff_approval_scope_helper_blocks_other_company() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    approval, draft = get_handoff_draft_by_approval_for_company(
        db,
        approval_id=result["approval_id"],
        company_id="company-demo-001",
    )
    assert approval.id == result["approval_id"]
    assert draft.id == result["handoff_package_draft_id"]

    with pytest.raises(HandoffPackageDraftForbiddenError):
        get_handoff_draft_by_approval_for_company(
            db,
            approval_id=result["approval_id"],
            company_id="company-other-001",
        )


def test_approve_handoff_package_draft_updates_review_status_without_transfer() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    response = approve_handoff_package_draft(
        db,
        draft_id=result["handoff_package_draft_id"],
        company_id="company-demo-001",
        reviewed_by="manager-demo",
        reason="검토 완료",
    )
    db.commit()

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    logs = db.scalars(select(EvidenceLog)).all()

    assert response == {
        "draft_id": draft.id,
        "approval_id": approval.id,
        "status": "APPROVED",
        "approval_status": "APPROVED",
        "transferred_at": None,
    }
    assert draft.status == "APPROVED"
    assert draft.transferred_at is None
    assert approval.status == "APPROVED"
    assert approval.reviewed_by == "manager-demo"
    assert approval.reason == "검토 완료"
    assert any(log.event_type == "handoff_package_draft_approved" for log in logs)
    assert any(
        log.event_type == "handoff_package_draft_approved"
        and log.company_id == "company-demo-001"
        for log in logs
    )
    assert any(
        log.summary == "전문가 검토용 handoff package 초안이 승인되었습니다."
        for log in logs
    )


def test_reject_handoff_package_draft_updates_review_status_without_transfer() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    response = reject_handoff_package_draft(
        db,
        draft_id=result["handoff_package_draft_id"],
        company_id="company-demo-001",
        reviewed_by="manager-demo",
        reason="보완 필요",
    )
    db.commit()

    draft = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    logs = db.scalars(select(EvidenceLog)).all()

    assert response == {
        "draft_id": draft.id,
        "approval_id": approval.id,
        "status": "REJECTED",
        "approval_status": "REJECTED",
        "transferred_at": None,
    }
    assert draft.status == "REJECTED"
    assert draft.transferred_at is None
    assert approval.status == "REJECTED"
    assert approval.reviewed_by == "manager-demo"
    assert approval.reason == "보완 필요"
    assert any(log.event_type == "handoff_package_draft_rejected" for log in logs)
    assert any(
        log.event_type == "handoff_package_draft_rejected"
        and log.company_id == "company-demo-001"
        for log in logs
    )
    assert any(
        log.summary == "전문가 검토용 handoff package 초안이 반려되었습니다."
        for log in logs
    )


def test_approve_handoff_package_draft_blocks_reprocessing() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    approve_handoff_package_draft(
        db,
        draft_id=result["handoff_package_draft_id"],
        company_id="company-demo-001",
    )
    db.commit()

    with pytest.raises(HandoffApprovalConflictError):
        approve_handoff_package_draft(
            db,
            draft_id=result["handoff_package_draft_id"],
            company_id="company-demo-001",
        )


def test_reject_handoff_package_draft_blocks_reprocessing() -> None:
    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id="request-demo",
        handoff_package_draft=_draft(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    reject_handoff_package_draft(
        db,
        draft_id=result["handoff_package_draft_id"],
        company_id="company-demo-001",
    )
    db.commit()

    with pytest.raises(HandoffApprovalConflictError):
        reject_handoff_package_draft(
            db,
            draft_id=result["handoff_package_draft_id"],
            company_id="company-demo-001",
        )
