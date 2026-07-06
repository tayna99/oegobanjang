from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft
from backend.app.models.runtime_state import RUNTIME_STATE_TARGET_TYPE, AgentRuntimeStateSnapshot
from backend.app.services.contact_persistence_service import (
    resolve_approval_target_company_id,
)
from backend.app.services.handoff_persistence_service import HANDOFF_TARGET_TYPE
from backend.app.services.runtime_state_persistence_service import (
    mark_runtime_state_snapshot_reviewed,
    runtime_state_target_status,
)
from backend.app.services.runtime_resume_service import create_runtime_resume_plan


APPROVAL_PENDING_STATUS = "PENDING"
APPROVAL_APPROVED_STATUS = "APPROVED"
APPROVAL_REJECTED_STATUS = "REJECTED"

CONTACT_MESSAGE_TARGET_TYPE = "contact_message"
STATUS_UPDATE_TARGET_TYPE = "status_update_candidate"

CONTACT_MESSAGE_PENDING_STATUS = "PENDING_APPROVAL"
STATUS_UPDATE_PENDING_STATUS = "PENDING_REVIEW"
HANDOFF_PENDING_STATUS = "PENDING_APPROVAL"

TARGET_TYPES = {
    CONTACT_MESSAGE_TARGET_TYPE,
    STATUS_UPDATE_TARGET_TYPE,
    HANDOFF_TARGET_TYPE,
    RUNTIME_STATE_TARGET_TYPE,
}
LIST_APPROVAL_TARGET_TYPES = {
    CONTACT_MESSAGE_TARGET_TYPE,
    STATUS_UPDATE_TARGET_TYPE,
    HANDOFF_TARGET_TYPE,
}
LIST_APPROVAL_STATUSES = {
    APPROVAL_PENDING_STATUS,
    APPROVAL_APPROVED_STATUS,
    APPROVAL_REJECTED_STATUS,
}
_ALIEN_REGISTRATION_RE = re.compile(r"\b\d{6}-[1-4]\d{6}\b")
_PHONE_RE = re.compile(r"\b(?:010-\d{4}-\d{4}|010\d{8})\b")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")
_FORBIDDEN_TEXT_MARKERS = (
    "worker_reply 원문",
    "translated_ko 전문",
    "메시지 전문",
    "package_json 전문",
    "여권번호",
    "외국인등록번호",
    "전화번호 전체",
    "주소 전체",
)


class ApprovalNotFoundError(ValueError):
    pass


class ApprovalForbiddenError(ValueError):
    pass


class ApprovalConflictError(ValueError):
    pass


class ApprovalValidationError(ValueError):
    pass


def get_approval_detail_for_company(
    db: Session,
    *,
    approval_id: str,
    company_id: str,
) -> dict[str, Any]:
    approval = _get_approval_or_not_found(db, approval_id)
    target = _get_target_or_conflict(db, approval)
    _validate_company_scope(db, approval, company_id)
    return _safe_response(approval, target)


def list_approvals_for_company(
    db: Session,
    *,
    company_id: str,
    status: str = APPROVAL_PENDING_STATUS,
    target_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    if not company_id:
        raise ApprovalForbiddenError("approval access forbidden")
    normalized_status = str(status or APPROVAL_PENDING_STATUS).upper()
    if normalized_status not in LIST_APPROVAL_STATUSES:
        raise ApprovalValidationError("unsupported approval status")
    if target_type is not None and target_type not in LIST_APPROVAL_TARGET_TYPES:
        raise ApprovalValidationError("unsupported approval target_type")

    safe_limit = min(max(int(limit), 0), 100)
    safe_offset = max(int(offset), 0)
    query = select(Approval).where(Approval.status == normalized_status)
    if target_type is not None:
        query = query.where(Approval.target_type == target_type)
    else:
        query = query.where(Approval.target_type.in_(LIST_APPROVAL_TARGET_TYPES))
    query = query.order_by(Approval.created_at.desc(), Approval.id.desc())

    scoped_items: list[dict[str, Any]] = []
    for approval in db.scalars(query).all():
        try:
            target = _get_target_or_conflict(db, approval)
            _validate_company_scope(db, approval, company_id)
        except (ApprovalConflictError, ApprovalForbiddenError):
            continue
        scoped_items.append(_safe_list_item(approval, target))

    total = len(scoped_items)
    return {
        "items": scoped_items[safe_offset : safe_offset + safe_limit],
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
    }


def approve_approval_for_company(
    db: Session,
    *,
    approval_id: str,
    company_id: str,
    reviewed_by: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return _review_approval_for_company(
        db,
        approval_id=approval_id,
        company_id=company_id,
        reviewed_by=reviewed_by,
        reason=reason,
        approval_status=APPROVAL_APPROVED_STATUS,
    )


def reject_approval_for_company(
    db: Session,
    *,
    approval_id: str,
    company_id: str,
    reviewed_by: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return _review_approval_for_company(
        db,
        approval_id=approval_id,
        company_id=company_id,
        reviewed_by=reviewed_by,
        reason=reason,
        approval_status=APPROVAL_REJECTED_STATUS,
    )


def _review_approval_for_company(
    db: Session,
    *,
    approval_id: str,
    company_id: str,
    reviewed_by: str | None,
    reason: str | None,
    approval_status: str,
) -> dict[str, Any]:
    approval = _get_approval_or_not_found(db, approval_id)
    target = _get_target_or_conflict(db, approval)
    _validate_company_scope(db, approval, company_id)
    _validate_reviewable(approval, target)
    _validate_review_metadata(reviewed_by=reviewed_by, reason=reason)

    reviewed_at = _now()
    approval.status = approval_status
    approval.reviewed_by = reviewed_by
    approval.reviewed_at = reviewed_at
    if reason is not None:
        approval.reason = reason

    _set_target_review_status(
        target,
        approval=approval,
        target_type=approval.target_type,
        status=approval_status,
        reviewed_at=reviewed_at,
    )
    _save_review_evidence_log(db, approval=approval, target=target)
    if approval.target_type == RUNTIME_STATE_TARGET_TYPE:
        if approval.status == APPROVAL_APPROVED_STATUS:
            create_runtime_resume_plan(db, snapshot=target, approval=approval)
        _save_runtime_resume_evidence_logs(db, approval=approval, target=target)
    db.flush()
    return _safe_response(approval, target)


def _get_approval_or_not_found(db: Session, approval_id: str) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise ApprovalNotFoundError("approval not found")
    if approval.target_type not in TARGET_TYPES:
        raise ApprovalConflictError("approval target conflict")
    return approval


def _get_target_or_conflict(
    db: Session,
    approval: Approval,
) -> ContactMessage | StatusUpdateCandidate | HandoffPackageDraft | AgentRuntimeStateSnapshot:
    if approval.target_type == CONTACT_MESSAGE_TARGET_TYPE:
        target = db.get(ContactMessage, approval.target_id)
    elif approval.target_type == STATUS_UPDATE_TARGET_TYPE:
        target = db.get(StatusUpdateCandidate, approval.target_id)
    elif approval.target_type == HANDOFF_TARGET_TYPE:
        target = db.get(HandoffPackageDraft, approval.target_id)
    elif approval.target_type == RUNTIME_STATE_TARGET_TYPE:
        target = db.get(AgentRuntimeStateSnapshot, approval.target_id)
    else:
        raise ApprovalConflictError("approval target conflict")
    if target is None:
        raise ApprovalConflictError("approval target conflict")
    return target


def _validate_company_scope(
    db: Session,
    approval: Approval,
    company_id: str | None,
) -> None:
    if not company_id:
        raise ApprovalForbiddenError("approval access forbidden")
    try:
        target_company_id = resolve_approval_target_company_id(db, approval)
    except ValueError as exc:
        raise ApprovalConflictError("approval target conflict") from exc
    if target_company_id != company_id:
        raise ApprovalForbiddenError("approval access forbidden")


def _validate_reviewable(
    approval: Approval,
    target: ContactMessage
    | StatusUpdateCandidate
    | HandoffPackageDraft
    | AgentRuntimeStateSnapshot,
) -> None:
    if approval.status != APPROVAL_PENDING_STATUS:
        raise ApprovalConflictError("approval is not pending")
    expected_target_status = _pending_status_for_target_type(approval.target_type)
    target_status = (
        runtime_state_target_status(target)
        if approval.target_type == RUNTIME_STATE_TARGET_TYPE
        else target.status
    )
    if target_status != expected_target_status:
        raise ApprovalConflictError("approval target is not pending")


def _pending_status_for_target_type(target_type: str) -> str:
    if target_type == CONTACT_MESSAGE_TARGET_TYPE:
        return CONTACT_MESSAGE_PENDING_STATUS
    if target_type == STATUS_UPDATE_TARGET_TYPE:
        return STATUS_UPDATE_PENDING_STATUS
    if target_type == HANDOFF_TARGET_TYPE:
        return HANDOFF_PENDING_STATUS
    if target_type == RUNTIME_STATE_TARGET_TYPE:
        return APPROVAL_PENDING_STATUS
    raise ApprovalConflictError("approval target conflict")


def _set_target_review_status(
    target: ContactMessage
    | StatusUpdateCandidate
    | HandoffPackageDraft
    | AgentRuntimeStateSnapshot,
    *,
    approval: Approval,
    target_type: str,
    status: str,
    reviewed_at: datetime,
) -> None:
    if target_type == CONTACT_MESSAGE_TARGET_TYPE:
        target.status = status
        target.sent_at = None
    elif target_type == STATUS_UPDATE_TARGET_TYPE:
        target.status = status
        target.reviewed_at = reviewed_at
    elif target_type == HANDOFF_TARGET_TYPE:
        target.status = status
        target.transferred_at = None
    elif target_type == RUNTIME_STATE_TARGET_TYPE:
        mark_runtime_state_snapshot_reviewed(target, approval)
        _mark_hot_runtime_state_reviewed(approval)
    else:
        raise ApprovalConflictError("approval target conflict")


def _validate_review_metadata(
    *,
    reviewed_by: str | None,
    reason: str | None,
) -> None:
    for value in (reviewed_by, reason):
        if value is not None:
            _validate_safe_text(value)


def _mark_hot_runtime_state_reviewed(approval: Approval) -> None:
    """Best-effort hot-store sync only. Never resumes or executes an agent."""

    try:
        from app.agent_runtime.langchain_v1.state_store import runtime_state_store

        runtime_state_store.mark_approval_reviewed(
            approval.target_id,
            status=approval.status,
            reason=approval.reason,
        )
    except Exception:
        # DB snapshot is the durable source of truth; hot-store sync must not
        # block the review decision.
        return


def _validate_safe_text(text: str) -> None:
    for marker in _FORBIDDEN_TEXT_MARKERS:
        if marker in text:
            raise ApprovalValidationError("approval review input contains sensitive data")
    if _ALIEN_REGISTRATION_RE.search(text):
        raise ApprovalValidationError("approval review input contains sensitive data")
    if _PHONE_RE.search(text):
        raise ApprovalValidationError("approval review input contains sensitive data")
    if _PASSPORT_RE.search(text):
        raise ApprovalValidationError("approval review input contains sensitive data")


def _save_review_evidence_log(
    db: Session,
    *,
    approval: Approval,
    target: ContactMessage
    | StatusUpdateCandidate
    | HandoffPackageDraft
    | AgentRuntimeStateSnapshot,
) -> EvidenceLog:
    event_type, summary = _review_evidence_event(
        target_type=approval.target_type,
        approval_status=approval.status,
    )
    log = EvidenceLog(
        event_type=event_type,
        agent_name="approval_api",
        tool_name=None,
        summary=summary,
        source_ids=_json_dumps([]),
        approval_required=True,
        risk_flags=_json_dumps([]),
        request_id=getattr(target, "request_id", None),
        company_id=getattr(target, "company_id", None),
        worker_id=None,
        contact_message_id=target.id
        if approval.target_type == CONTACT_MESSAGE_TARGET_TYPE
        else None,
        status_update_candidate_id=target.id
        if approval.target_type == STATUS_UPDATE_TARGET_TYPE
        else None,
        approval_id=approval.id,
    )
    db.add(log)
    return log


def _save_runtime_resume_evidence_logs(
    db: Session,
    *,
    approval: Approval,
    target: AgentRuntimeStateSnapshot,
) -> None:
    reviewed_summary = (
        "Agent runtime approval was reviewed. No external action was executed."
    )
    events = [
        ("approval_reviewed", reviewed_summary),
    ]
    if approval.status == APPROVAL_APPROVED_STATUS:
        events.extend(
            [
                (
                    "resume_requested",
                    "Limited internal resume was requested after approval.",
                ),
                (
                    "resume_completed_or_blocked",
                    "Approved draft finalization and internal handoff readiness were marked; external delivery and government submission remain blocked.",
                ),
            ]
        )
    for event_type, summary in events:
        db.add(
            EvidenceLog(
                event_type=event_type,
                agent_name="approval_api",
                tool_name=None,
                summary=summary,
                source_ids=_json_dumps([]),
                approval_required=True,
                risk_flags=_json_dumps([]),
                request_id=target.request_id,
                company_id=target.company_id,
                worker_id=None,
                approval_id=approval.id,
            )
        )


def _review_evidence_event(
    *,
    target_type: str,
    approval_status: str,
) -> tuple[str, str]:
    if target_type == CONTACT_MESSAGE_TARGET_TYPE:
        if approval_status == APPROVAL_APPROVED_STATUS:
            return "contact_message_approved", "메시지 초안이 승인되었습니다."
        return "contact_message_rejected", "메시지 초안이 반려되었습니다."
    if target_type == STATUS_UPDATE_TARGET_TYPE:
        if approval_status == APPROVAL_APPROVED_STATUS:
            return "status_update_candidate_approved", "상태 업데이트 후보가 승인되었습니다."
        return "status_update_candidate_rejected", "상태 업데이트 후보가 반려되었습니다."
    if target_type == HANDOFF_TARGET_TYPE:
        if approval_status == APPROVAL_APPROVED_STATUS:
            return (
                "handoff_package_draft_approved",
                "전문가 검토용 handoff package 초안이 승인되었습니다.",
            )
        return (
            "handoff_package_draft_rejected",
            "전문가 검토용 handoff package 초안이 반려되었습니다.",
        )
    if target_type == RUNTIME_STATE_TARGET_TYPE:
        if approval_status == APPROVAL_APPROVED_STATUS:
            return (
                "agent_runtime_state_approved",
                "Agent runtime 결과가 담당자 승인 상태로 표시되었습니다.",
            )
        return (
            "agent_runtime_state_rejected",
            "Agent runtime 결과가 담당자 반려 상태로 표시되었습니다.",
        )
    raise ApprovalConflictError("approval target conflict")


def _safe_response(
    approval: Approval,
    target: ContactMessage
    | StatusUpdateCandidate
    | HandoffPackageDraft
    | AgentRuntimeStateSnapshot,
) -> dict[str, Any]:
    target_status = (
        runtime_state_target_status(target)
        if approval.target_type == RUNTIME_STATE_TARGET_TYPE
        else target.status
    )
    return {
        "approval_id": approval.id,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "approval_status": approval.status,
        "target_status": target_status,
        "approval_required": bool(getattr(target, "approval_required", True)),
        "reviewed_by": approval.reviewed_by,
        "reviewed_at": _datetime_to_str(approval.reviewed_at),
        "reason": approval.reason,
    }


def _safe_list_item(
    approval: Approval,
    target: ContactMessage | StatusUpdateCandidate | HandoffPackageDraft,
) -> dict[str, Any]:
    target_status = target.status
    return {
        "approval_id": approval.id,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "approval_status": approval.status,
        "target_status": target_status,
        "summary": _approval_list_summary(approval.target_type),
        "created_at": _datetime_to_str(approval.created_at),
        "reviewed_at": _datetime_to_str(approval.reviewed_at),
        "target": _safe_target_summary(approval, target),
    }


def _approval_list_summary(target_type: str) -> str:
    if target_type == CONTACT_MESSAGE_TARGET_TYPE:
        return "다국어 메시지 초안 승인 대기"
    if target_type == STATUS_UPDATE_TARGET_TYPE:
        return "상태 업데이트 후보 승인 대기"
    if target_type == HANDOFF_TARGET_TYPE:
        return "전문가 검토용 handoff package 초안 승인 대기"
    raise ApprovalConflictError("approval target conflict")


def _safe_target_summary(
    approval: Approval,
    target: ContactMessage | StatusUpdateCandidate | HandoffPackageDraft,
) -> dict[str, Any]:
    target_type = approval.target_type
    if target_type == CONTACT_MESSAGE_TARGET_TYPE:
        return {
            "message_purpose": target.message_purpose,
            "language_code": target.language_code,
            "status": target.status,
            "approval_status": approval.status,
            "created_at": _datetime_to_str(target.created_at),
        }
    if target_type == STATUS_UPDATE_TARGET_TYPE:
        return {
            "target_type": target.target_type,
            "target_key": target.target_key,
            "candidate_status": target.candidate_status,
            "confidence": target.confidence,
            "status": target.status,
            "approval_status": approval.status,
            "created_at": _datetime_to_str(target.created_at),
        }
    if target_type == HANDOFF_TARGET_TYPE:
        return {
            "package_type": target.package_type,
            "case_type": target.case_type,
            "risk_level": target.risk_level,
            "handoff_ready": target.handoff_ready,
            "status": target.status,
            "approval_status": approval.status,
            "created_at": _datetime_to_str(target.created_at),
        }
    raise ApprovalConflictError("approval target conflict")


def _datetime_to_str(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _now() -> datetime:
    return datetime.now(timezone.utc)
