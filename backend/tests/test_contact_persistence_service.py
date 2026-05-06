from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.services.contact_persistence_service import (
    save_message_draft_result,
    save_worker_reply_summary_result,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )
    return session_factory()


def _message_result() -> dict:
    return {
        "worker_id": "worker-demo-001",
        "language_code": "vi",
        "message_purpose": "safety_training_notice",
        "status": "SUCCESS",
        "korean_text": "5월 10일 10시에 교육장에서 안전교육이 있습니다.",
        "translated_text": "Có buổi đào tạo an toàn vào ngày 10 tháng 5 lúc 10 giờ.",
        "approval_required": True,
        "citations": [
            {
                "source_id": "mock_safety_source",
                "title": "Mock Safety Source",
                "publisher": "Mock Publisher",
                "evidence_grade": "B",
            }
        ],
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
        "summary_ko": "근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘",
        "status_update_candidates": [
            {
                "candidate_type": "passport_received_candidate",
                "field": "passport",
                "candidate_status": "available",
                "is_final": False,
            },
            {
                "candidate_type": "photo_pending_candidate",
                "field": "photo",
                "candidate_status": "pending_until_next_day",
                "is_final": False,
            },
        ],
        "approval_required": True,
        "manager_review_required": True,
        "evidence_events": [
            {
                "event_type": "worker_reply_summarized",
                "agent_name": "multilingual_contact_agent",
                "summary": "근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘",
                "source_ids": [],
                "approval_required": True,
            },
            {
                "event_type": "status_update_candidate_created",
                "agent_name": "multilingual_contact_agent",
                "summary": "서류 상태 업데이트 후보가 생성됨",
                "source_ids": [],
                "approval_required": True,
            },
        ],
        "risk_flags": ["MANAGER_REVIEW_REQUIRED"],
    }


def test_save_message_draft_creates_contact_message_pending_approval() -> None:
    db = _session()
    result = _message_result()

    message = save_message_draft_result(
        db,
        agent_result=result,
        created_by="manager-demo",
        request_id="request-demo",
    )
    db.commit()

    saved_message = db.get(ContactMessage, message.id)
    assert saved_message is not None
    assert saved_message.status == "PENDING_APPROVAL"
    assert saved_message.approval_required is True
    assert saved_message.sent_at is None
    assert saved_message.approval_id is not None
    assert json.loads(saved_message.citation_source_ids) == ["mock_safety_source"]
    assert json.loads(saved_message.risk_flags) == ["APPROVAL_REQUIRED_FOR_SEND"]

    approval = db.get(Approval, saved_message.approval_id)
    assert approval is not None
    assert approval.target_type == "contact_message"
    assert approval.target_id == saved_message.id
    assert approval.status == "PENDING"


def test_message_draft_evidence_log_does_not_store_message_body() -> None:
    db = _session()
    result = _message_result()

    message = save_message_draft_result(db, agent_result=result)
    db.commit()

    logs = db.scalars(select(EvidenceLog)).all()
    assert logs
    for log in logs:
        assert result["korean_text"] not in log.summary
        assert result["translated_text"] not in log.summary
        assert log.contact_message_id == message.id
        assert log.approval_id == message.approval_id


def test_save_worker_reply_summary_creates_candidate_level_approvals() -> None:
    db = _session()
    result = _worker_reply_result()
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    candidates = save_worker_reply_summary_result(
        db,
        agent_result=result,
        worker_id="worker-demo-001",
        request_id="request-demo",
        requested_by="manager-demo",
        worker_reply=worker_reply,
    )
    db.commit()

    saved_candidates = db.scalars(select(StatusUpdateCandidate)).all()
    approvals = db.scalars(select(Approval)).all()

    assert len(candidates) == 2
    assert len(saved_candidates) == 2
    assert len(approvals) == 2
    for candidate in saved_candidates:
        assert candidate.status == "PENDING_REVIEW"
        assert candidate.manager_review_required is True
        assert candidate.approval_id is not None
        assert candidate.status != "APPLIED"
        approval = db.get(Approval, candidate.approval_id)
        assert approval is not None
        assert approval.target_type == "status_update_candidate"
        assert approval.target_id == candidate.id
        assert approval.status == "PENDING"


def test_worker_reply_evidence_logs_do_not_store_raw_reply_or_finalize_status() -> None:
    db = _session()
    result = _worker_reply_result()
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    save_worker_reply_summary_result(
        db,
        agent_result=result,
        worker_id="worker-demo-001",
        worker_reply=worker_reply,
    )
    db.commit()

    logs = db.scalars(select(EvidenceLog)).all()
    assert logs
    for log in logs:
        assert worker_reply not in log.summary
        assert "SENT" not in log.summary
        assert "APPLIED" not in log.summary

    candidates = db.scalars(select(StatusUpdateCandidate)).all()
    assert all(candidate.status == "PENDING_REVIEW" for candidate in candidates)
