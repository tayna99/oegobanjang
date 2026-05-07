from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.services.handoff_persistence_service import (
    HANDOFF_APPROVED_STATUS,
    HANDOFF_REJECTED_STATUS,
    HANDOFF_TARGET_TYPE,
    mark_handoff_approval_reviewed,
)


MESSAGE_INITIAL_STATUS = "PENDING_APPROVAL"
APPROVAL_INITIAL_STATUS = "PENDING"
CANDIDATE_INITIAL_STATUS = "PENDING_REVIEW"
APPROVAL_APPROVED_STATUS = "APPROVED"
APPROVAL_REJECTED_STATUS = "REJECTED"
MESSAGE_APPROVED_STATUS = "APPROVED"
MESSAGE_REJECTED_STATUS = "REJECTED"
CANDIDATE_APPROVED_STATUS = "APPROVED"
CANDIDATE_REJECTED_STATUS = "REJECTED"
FORBIDDEN_EVIDENCE_MARKERS = (
    "여권번호",
    "외국인등록번호",
    "전화번호 전체",
    "주소 전체",
    "worker_reply 원문",
    "translated_ko 전문",
    "메시지 전문",
    "OCR 원문",
)
_ALIEN_REGISTRATION_RE = re.compile(r"\b\d{6}-[1-4]\d{6}\b")
_PHONE_RE = re.compile(r"\b(?:010-\d{4}-\d{4}|010\d{8})\b")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")


def approve_approval(
    db: Session,
    approval_id: str,
    *,
    reviewed_by: str | None = None,
) -> Approval:
    approval = _get_pending_approval(db, approval_id)
    approval.status = APPROVAL_APPROVED_STATUS
    approval.reviewed_by = reviewed_by
    approval.reviewed_at = _now()

    if approval.target_type == "contact_message":
        message = _get_contact_message(db, approval.target_id)
        message.status = MESSAGE_APPROVED_STATUS
    elif approval.target_type == "status_update_candidate":
        candidate = _get_status_update_candidate(db, approval.target_id)
        candidate.status = CANDIDATE_APPROVED_STATUS
        candidate.reviewed_at = approval.reviewed_at
    elif approval.target_type == HANDOFF_TARGET_TYPE:
        mark_handoff_approval_reviewed(
            db,
            approval=approval,
            status=HANDOFF_APPROVED_STATUS,
        )
    else:
        raise ValueError(f"Unsupported approval target_type: {approval.target_type}")

    db.flush()
    return approval


def reject_approval(
    db: Session,
    approval_id: str,
    *,
    reviewed_by: str | None = None,
    reason: str | None = None,
) -> Approval:
    approval = _get_pending_approval(db, approval_id)
    approval.status = APPROVAL_REJECTED_STATUS
    approval.reviewed_by = reviewed_by
    approval.reviewed_at = _now()
    if reason:
        approval.reason = reason

    if approval.target_type == "contact_message":
        message = _get_contact_message(db, approval.target_id)
        message.status = MESSAGE_REJECTED_STATUS
    elif approval.target_type == "status_update_candidate":
        candidate = _get_status_update_candidate(db, approval.target_id)
        candidate.status = CANDIDATE_REJECTED_STATUS
        candidate.reviewed_at = approval.reviewed_at
    elif approval.target_type == HANDOFF_TARGET_TYPE:
        mark_handoff_approval_reviewed(
            db,
            approval=approval,
            status=HANDOFF_REJECTED_STATUS,
        )
    else:
        raise ValueError(f"Unsupported approval target_type: {approval.target_type}")

    db.flush()
    return approval


def save_message_draft_result(
    db: Session,
    *,
    agent_result: dict[str, Any],
    worker_id: str | None = None,
    created_by: str | None = None,
    request_id: str | None = None,
) -> ContactMessage:
    _validate_message_draft_result(agent_result)
    source_ids = _citation_source_ids(agent_result.get("citations") or [])
    risk_flags = _as_list(agent_result.get("risk_flags"))

    message = ContactMessage(
        worker_id=worker_id or agent_result.get("worker_id"),
        message_purpose=agent_result["message_purpose"],
        language_code=agent_result["language_code"],
        korean_text=agent_result["korean_text"],
        translated_text=agent_result.get("translated_text"),
        status=MESSAGE_INITIAL_STATUS,
        approval_required=True,
        citation_source_ids=_json_dumps(source_ids),
        risk_flags=_json_dumps(risk_flags),
        created_by=created_by,
        sent_at=None,
    )
    db.add(message)
    db.flush()

    approval = create_approval_for_contact_message(
        db,
        message,
        requested_by=created_by,
    )
    message.approval_id = approval.id

    save_evidence_events(
        db,
        evidence_events=agent_result.get("evidence_events") or [],
        request_id=request_id,
        worker_id=message.worker_id,
        contact_message_id=message.id,
        approval_id=approval.id,
        risk_flags=risk_flags,
        default_source_ids=source_ids,
        forbidden_texts=[
            agent_result.get("korean_text"),
            agent_result.get("translated_text"),
        ],
    )
    db.flush()
    return message


def save_worker_reply_summary_result(
    db: Session,
    *,
    agent_result: dict[str, Any],
    worker_id: str,
    request_id: str | None = None,
    source_message_id: str | None = None,
    requested_by: str | None = None,
    worker_reply: str | None = None,
) -> list[StatusUpdateCandidate]:
    _validate_worker_reply_summary_result(agent_result)
    candidates: list[StatusUpdateCandidate] = []
    risk_flags = _as_list(agent_result.get("risk_flags"))

    for item in agent_result.get("status_update_candidates") or []:
        _validate_status_update_candidate(item)
        candidate = StatusUpdateCandidate(
            worker_id=worker_id,
            target_type=item.get("target_type") or "worker_document",
            target_key=item["field"],
            candidate_status=item["candidate_status"],
            confidence=item.get("confidence"),
            manager_review_required=True,
            status=CANDIDATE_INITIAL_STATUS,
            source_message_id=source_message_id,
        )
        db.add(candidate)
        db.flush()

        approval = create_approval_for_status_update_candidate(
            db,
            candidate,
            requested_by=requested_by,
        )
        candidate.approval_id = approval.id
        candidates.append(candidate)

        save_evidence_events(
            db,
            evidence_events=agent_result.get("evidence_events") or [],
            request_id=request_id,
            worker_id=worker_id,
            status_update_candidate_id=candidate.id,
            approval_id=approval.id,
            risk_flags=risk_flags,
            forbidden_texts=[worker_reply, agent_result.get("translated_ko")],
        )

    db.flush()
    return candidates


def save_evidence_events(
    db: Session,
    *,
    evidence_events: list[dict[str, Any]],
    request_id: str | None = None,
    worker_id: str | None = None,
    contact_message_id: str | None = None,
    status_update_candidate_id: str | None = None,
    approval_id: str | None = None,
    risk_flags: list[str] | None = None,
    default_source_ids: list[str] | None = None,
    forbidden_texts: list[str | None] | None = None,
) -> list[EvidenceLog]:
    logs: list[EvidenceLog] = []
    for event in evidence_events:
        summary = str(event.get("summary") or "").strip()
        source_ids = event.get("source_ids") or default_source_ids or []
        _validate_evidence_payload(
            summary=summary,
            source_ids=_as_list(source_ids),
            risk_flags=risk_flags or [],
            forbidden_texts=forbidden_texts or [],
        )
        log = EvidenceLog(
            event_type=str(event.get("event_type") or "unknown"),
            agent_name=str(event.get("agent_name") or "unknown"),
            tool_name=event.get("tool_name"),
            summary=summary,
            source_ids=_json_dumps(_as_list(source_ids)),
            approval_required=bool(event.get("approval_required", False)),
            risk_flags=_json_dumps(risk_flags or []),
            request_id=request_id,
            worker_id=worker_id,
            contact_message_id=contact_message_id,
            status_update_candidate_id=status_update_candidate_id,
            approval_id=approval_id,
        )
        db.add(log)
        logs.append(log)

    db.flush()
    return logs


def create_approval_for_contact_message(
    db: Session,
    contact_message: ContactMessage,
    *,
    requested_by: str | None = None,
) -> Approval:
    approval = Approval(
        target_type="contact_message",
        target_id=contact_message.id,
        status=APPROVAL_INITIAL_STATUS,
        requested_by=requested_by,
        reason="다국어 메시지 발송 전 담당자 승인이 필요합니다.",
    )
    db.add(approval)
    db.flush()
    return approval


def create_approval_for_status_update_candidate(
    db: Session,
    candidate: StatusUpdateCandidate,
    *,
    requested_by: str | None = None,
) -> Approval:
    approval = Approval(
        target_type="status_update_candidate",
        target_id=candidate.id,
        status=APPROVAL_INITIAL_STATUS,
        requested_by=requested_by,
        reason="상태 업데이트 후보 반영 전 담당자 승인이 필요합니다.",
    )
    db.add(approval)
    db.flush()
    return approval


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_pending_approval(db: Session, approval_id: str) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise ValueError(f"Approval not found: {approval_id}")
    if approval.status != APPROVAL_INITIAL_STATUS:
        raise ValueError(
            f"Approval must be PENDING before review: {approval_id} is {approval.status}"
        )
    return approval


def _get_contact_message(db: Session, message_id: str) -> ContactMessage:
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise ValueError(f"Contact message not found: {message_id}")
    return message


def _get_status_update_candidate(
    db: Session,
    candidate_id: str,
) -> StatusUpdateCandidate:
    candidate = db.get(StatusUpdateCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Status update candidate not found: {candidate_id}")
    return candidate


def _validate_message_draft_result(agent_result: dict[str, Any]) -> None:
    if agent_result.get("status") != "SUCCESS":
        raise ValueError("Only successful message draft results can be saved")
    if not agent_result.get("korean_text"):
        raise ValueError("korean_text is required")
    if agent_result.get("approval_required") is not True:
        raise ValueError("message draft must require approval")
    if agent_result.get("sent_at") is not None:
        raise ValueError("message draft cannot have sent_at")
    if str(agent_result.get("status", "")).upper() in {"SENT", "APPROVED"}:
        raise ValueError("message draft cannot start as SENT or APPROVED")


def _validate_worker_reply_summary_result(agent_result: dict[str, Any]) -> None:
    if agent_result.get("status") != "SUCCESS":
        raise ValueError("Only successful worker reply summary results can be saved")
    if agent_result.get("approval_required") is not True:
        raise ValueError("worker reply summary must require approval")
    if agent_result.get("manager_review_required") is not True:
        raise ValueError("worker reply summary must require manager review")


def _validate_status_update_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("is_final") is True:
        raise ValueError("status update candidate cannot be final")
    if str(candidate.get("status", "")).upper() == "APPLIED":
        raise ValueError("status update candidate cannot start as APPLIED")
    if not candidate.get("field") or not candidate.get("candidate_status"):
        raise ValueError("candidate field and candidate_status are required")


def _validate_evidence_summary(
    summary: str,
    forbidden_texts: list[str | None],
) -> None:
    _validate_evidence_payload(
        summary=summary,
        source_ids=[],
        risk_flags=[],
        forbidden_texts=forbidden_texts,
    )


def _validate_evidence_payload(
    *,
    summary: str,
    source_ids: list[Any],
    risk_flags: list[Any],
    forbidden_texts: list[str | None],
) -> None:
    if not summary:
        raise ValueError("evidence summary is required")
    _validate_sensitive_text(summary, forbidden_texts)
    for flag in risk_flags:
        _validate_sensitive_text(str(flag), forbidden_texts)
    for source_id in source_ids:
        _validate_source_id(str(source_id), forbidden_texts)


def _validate_sensitive_text(
    text: str,
    forbidden_texts: list[str | None],
) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        if marker in text:
            raise ValueError("evidence summary contains forbidden personal data marker")
    for forbidden in forbidden_texts:
        if forbidden and forbidden in text:
            raise ValueError("evidence summary must not contain original text")
    if _ALIEN_REGISTRATION_RE.search(text):
        raise ValueError("evidence summary contains raw alien registration number")
    if _PHONE_RE.search(text):
        raise ValueError("evidence summary contains raw phone number")
    if _PASSPORT_RE.search(text):
        raise ValueError("evidence summary contains raw passport number")


def _validate_source_id(
    source_id: str,
    forbidden_texts: list[str | None],
) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        if marker in source_id:
            raise ValueError("evidence source_id contains forbidden personal data marker")
    for forbidden in forbidden_texts:
        if forbidden and forbidden in source_id:
            raise ValueError("evidence source_id must not contain original text")


def _citation_source_ids(citations: list[dict[str, Any]]) -> list[str]:
    return [
        str(citation["source_id"])
        for citation in citations
        if citation.get("source_id")
    ]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
