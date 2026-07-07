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
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.services.contact_persistence_service import (
    SOURCE_MESSAGE_COMPANY_MISMATCH,
    SOURCE_MESSAGE_NOT_FOUND,
    SOURCE_MESSAGE_WORKER_MISMATCH,
    SourceMessageValidationError,
    approve_approval,
    reject_approval,
    resolve_approval_target_company_id,
    resolve_source_message_for_status_update,
    save_evidence_events,
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
        "translated_ko": "여권은 보유한 것으로 보이며 사진은 내일 제출 가능하다는 답변입니다.",
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
        company_id="company-demo-001",
        created_by="manager-demo",
        request_id="request-demo",
    )
    db.commit()

    saved_message = db.get(ContactMessage, message.id)
    assert saved_message is not None
    assert saved_message.company_id == "company-demo-001"
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
    assert resolve_approval_target_company_id(db, approval) == "company-demo-001"


def test_message_draft_evidence_log_does_not_store_message_body() -> None:
    db = _session()
    result = _message_result()

    message = save_message_draft_result(
        db,
        agent_result=result,
        company_id="company-demo-001",
    )
    db.commit()

    logs = db.scalars(select(EvidenceLog)).all()
    assert logs
    for log in logs:
        assert result["korean_text"] not in log.summary
        assert result["translated_text"] not in log.summary
        assert log.company_id == "company-demo-001"
        assert log.contact_message_id == message.id
        assert log.approval_id == message.approval_id


def test_message_draft_evidence_log_rejects_message_body() -> None:
    db = _session()
    result = _message_result()
    result["evidence_events"][0]["summary"] = result["korean_text"]

    with pytest.raises(ValueError, match="original text"):
        save_message_draft_result(db, agent_result=result)


def test_save_worker_reply_summary_creates_candidate_level_approvals() -> None:
    db = _session()
    result = _worker_reply_result()
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    candidates = save_worker_reply_summary_result(
        db,
        agent_result=result,
        worker_id="worker-demo-001",
        company_id="company-demo-001",
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
        assert candidate.company_id == "company-demo-001"
        assert candidate.manager_review_required is True
        assert candidate.approval_id is not None
        assert candidate.status != "APPLIED"
        approval = db.get(Approval, candidate.approval_id)
        assert approval is not None
        assert approval.target_type == "status_update_candidate"
        assert approval.target_id == candidate.id
        assert approval.status == "PENDING"
        assert resolve_approval_target_company_id(db, approval) == "company-demo-001"


def test_save_worker_reply_summary_links_valid_source_message_id() -> None:
    db = _session()
    message = save_message_draft_result(
        db,
        agent_result=_message_result(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )

    candidates = save_worker_reply_summary_result(
        db,
        agent_result=_worker_reply_result(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
        source_message_id=message.id,
    )
    db.commit()

    assert candidates
    assert all(candidate.source_message_id == message.id for candidate in candidates)


def test_resolve_source_message_for_status_update_allows_unsent_message() -> None:
    db = _session()
    message = save_message_draft_result(
        db,
        agent_result=_message_result(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()

    resolved = resolve_source_message_for_status_update(
        db,
        source_message_id=message.id,
        company_id="company-demo-001",
        worker_id="worker-demo-001",
    )

    assert resolved.id == message.id
    assert resolved.sent_at is None


@pytest.mark.parametrize(
    ("source_message_id", "company_id", "worker_id", "expected_reason"),
    [
        (
            "missing-message",
            "company-demo-001",
            "worker-demo-001",
            SOURCE_MESSAGE_NOT_FOUND,
        ),
        (
            "valid-message",
            "other-company",
            "worker-demo-001",
            SOURCE_MESSAGE_COMPANY_MISMATCH,
        ),
        (
            "valid-message",
            "company-demo-001",
            "other-worker",
            SOURCE_MESSAGE_WORKER_MISMATCH,
        ),
    ],
)
def test_resolve_source_message_for_status_update_rejects_invalid_scope(
    source_message_id: str,
    company_id: str,
    worker_id: str,
    expected_reason: str,
) -> None:
    db = _session()
    message = save_message_draft_result(
        db,
        agent_result=_message_result(),
        worker_id="worker-demo-001",
        company_id="company-demo-001",
    )
    db.commit()
    if source_message_id == "valid-message":
        source_message_id = message.id

    with pytest.raises(SourceMessageValidationError) as exc_info:
        resolve_source_message_for_status_update(
            db,
            source_message_id=source_message_id,
            company_id=company_id,
            worker_id=worker_id,
        )

    assert exc_info.value.reason == expected_reason


def test_worker_reply_evidence_logs_do_not_store_raw_reply_or_finalize_status() -> None:
    db = _session()
    result = _worker_reply_result()
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."

    save_worker_reply_summary_result(
        db,
        agent_result=result,
        worker_id="worker-demo-001",
        company_id="company-demo-001",
        worker_reply=worker_reply,
    )
    db.commit()

    logs = db.scalars(select(EvidenceLog)).all()
    assert logs
    for log in logs:
        assert log.company_id == "company-demo-001"
        assert worker_reply not in log.summary
        assert result["translated_ko"] not in log.summary
        assert "SENT" not in log.summary
        assert "APPLIED" not in log.summary

    candidates = db.scalars(select(StatusUpdateCandidate)).all()
    assert all(candidate.status == "PENDING_REVIEW" for candidate in candidates)


def test_worker_reply_evidence_log_rejects_raw_reply_and_translation() -> None:
    db = _session()
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    result = _worker_reply_result()
    result["evidence_events"][0]["summary"] = worker_reply

    with pytest.raises(ValueError, match="original text"):
        save_worker_reply_summary_result(
            db,
            agent_result=result,
            worker_id="worker-demo-001",
            worker_reply=worker_reply,
        )

    db = _session()
    result = _worker_reply_result()
    result["evidence_events"][0]["summary"] = result["translated_ko"]
    with pytest.raises(ValueError, match="original text"):
        save_worker_reply_summary_result(
            db,
            agent_result=result,
            worker_id="worker-demo-001",
            worker_reply=worker_reply,
        )


@pytest.mark.parametrize(
    "summary",
    [
        "여권번호 M12345678 확인됨",
        "외국인등록번호 900101-1234567 확인됨",
        "전화번호 010-1234-5678 확인됨",
    ],
)
def test_evidence_log_rejects_raw_pii_patterns(summary: str) -> None:
    db = _session()

    with pytest.raises(ValueError):
        save_evidence_events(
            db,
            evidence_events=[
                {
                    "event_type": "risk_flagged",
                    "agent_name": "test_agent",
                    "summary": summary,
                    "source_ids": ["safe_source"],
                    "approval_required": True,
                }
            ],
        )


def test_evidence_log_rejects_raw_text_in_risk_flags_and_source_ids() -> None:
    db = _session()
    forbidden = "근로자가 보낸 원문 답변입니다"

    with pytest.raises(ValueError, match="original text"):
        save_evidence_events(
            db,
            evidence_events=[
                {
                    "event_type": "risk_flagged",
                    "agent_name": "test_agent",
                    "summary": "원문 없는 요약",
                    "source_ids": ["safe_source"],
                    "approval_required": True,
                }
            ],
            risk_flags=[forbidden],
            forbidden_texts=[forbidden],
        )

    with pytest.raises(ValueError, match="source_id"):
        save_evidence_events(
            db,
            evidence_events=[
                {
                    "event_type": "risk_flagged",
                    "agent_name": "test_agent",
                    "summary": "원문 없는 요약",
                    "source_ids": [forbidden],
                    "approval_required": True,
                }
            ],
            forbidden_texts=[forbidden],
        )


def test_approve_contact_message_approval_marks_message_approved_without_sending() -> None:
    db = _session()
    message = save_message_draft_result(db, agent_result=_message_result())
    db.commit()

    approval = approve_approval(
        db,
        message.approval_id,
        reviewed_by="manager-demo",
    )
    db.commit()

    saved_message = db.get(ContactMessage, message.id)
    assert approval.status == "APPROVED"
    assert approval.reviewed_by == "manager-demo"
    assert approval.reviewed_at is not None
    assert saved_message.status == "APPROVED"
    assert saved_message.sent_at is None


def test_reject_contact_message_approval_marks_message_rejected() -> None:
    db = _session()
    message = save_message_draft_result(db, agent_result=_message_result())
    db.commit()

    approval = reject_approval(
        db,
        message.approval_id,
        reviewed_by="manager-demo",
        reason="문구 수정 필요",
    )
    db.commit()

    saved_message = db.get(ContactMessage, message.id)
    assert approval.status == "REJECTED"
    assert approval.reviewed_by == "manager-demo"
    assert approval.reason == "문구 수정 필요"
    assert saved_message.status == "REJECTED"
    assert saved_message.sent_at is None


def test_approve_status_update_candidate_marks_candidate_approved_without_apply() -> None:
    db = _session()
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=_worker_reply_result(),
        worker_id="worker-demo-001",
    )
    db.commit()

    candidate = candidates[0]
    approval = approve_approval(
        db,
        candidate.approval_id,
        reviewed_by="manager-demo",
    )
    db.commit()

    saved_candidate = db.get(StatusUpdateCandidate, candidate.id)
    assert approval.status == "APPROVED"
    assert saved_candidate.status == "APPROVED"
    assert saved_candidate.reviewed_at is not None
    assert saved_candidate.candidate_status == candidate.candidate_status


def test_reject_status_update_candidate_marks_candidate_rejected() -> None:
    db = _session()
    candidates = save_worker_reply_summary_result(
        db,
        agent_result=_worker_reply_result(),
        worker_id="worker-demo-001",
    )
    db.commit()

    candidate = candidates[0]
    approval = reject_approval(
        db,
        candidate.approval_id,
        reviewed_by="manager-demo",
    )
    db.commit()

    saved_candidate = db.get(StatusUpdateCandidate, candidate.id)
    assert approval.status == "REJECTED"
    assert saved_candidate.status == "REJECTED"
    assert saved_candidate.reviewed_at is not None


def test_approval_cannot_be_reviewed_twice() -> None:
    db = _session()
    message = save_message_draft_result(db, agent_result=_message_result())
    db.commit()

    approve_approval(db, message.approval_id)
    db.commit()

    try:
        reject_approval(db, message.approval_id)
    except ValueError as exc:
        assert "must be PENDING" in str(exc)
    else:
        raise AssertionError("reviewed approval must not be reviewed again")
