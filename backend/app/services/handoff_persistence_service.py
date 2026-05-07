from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.approval import Approval
from backend.app.models.evidence import EvidenceLog
from backend.app.models.handoff import HandoffPackageDraft


HANDOFF_INITIAL_STATUS = "PENDING_APPROVAL"
APPROVAL_INITIAL_STATUS = "PENDING"
HANDOFF_APPROVED_STATUS = "APPROVED"
HANDOFF_REJECTED_STATUS = "REJECTED"
HANDOFF_TARGET_TYPE = "handoff_package_draft"
HANDOFF_DRAFT_CREATED_SUMMARY = "전문가 검토용 handoff package 초안이 생성되었습니다."
HANDOFF_DRAFT_APPROVED_SUMMARY = "전문가 검토용 handoff package 초안이 승인되었습니다."
HANDOFF_DRAFT_REJECTED_SUMMARY = "전문가 검토용 handoff package 초안이 반려되었습니다."

_ALIEN_REGISTRATION_RE = re.compile(r"\b\d{6}-[1-4]\d{6}\b")
_PHONE_RE = re.compile(r"\b(?:010-\d{4}-\d{4}|010\d{8})\b")
_PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")
_FORBIDDEN_KEYS = {
    "worker_id",
    "worker_name",
    "nationality",
    "worker_reply",
    "translated_ko",
    "message_body",
    "passport_number",
    "alien_registration_number",
    "phone",
    "address",
    "ocr_text",
    "document_raw_text",
}
_FORBIDDEN_TEXT_MARKERS = (
    "worker_reply 원문",
    "translated_ko 전문",
    "메시지 전문",
    "여권번호",
    "외국인등록번호",
    "전화번호 전체",
    "주소 전체",
    "OCR 원문",
    "비자 가능 여부 확정",
    "비자 승인 확정",
    "법률 판단 확정",
    "노무 판단 확정",
)


class HandoffPackageDraftNotFoundError(ValueError):
    pass


class HandoffPackageDraftForbiddenError(ValueError):
    pass


class HandoffApprovalConflictError(ValueError):
    pass


def save_handoff_package_draft(
    db: Session,
    *,
    request_id: str | None,
    handoff_package_draft: dict[str, Any],
    worker_id: str | None = None,
    company_id: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    _validate_handoff_draft_contract(handoff_package_draft)
    package_json = _safe_package_json(handoff_package_draft)
    risk_flags = [str(flag) for flag in handoff_package_draft.get("risk_flags", [])]
    evidence = handoff_package_draft.get("evidence") or {}
    source_ids = [str(source_id) for source_id in evidence.get("citation_ids", [])]
    worker_summary = handoff_package_draft.get("worker_summary") or {}

    draft = HandoffPackageDraft(
        request_id=request_id,
        company_id=company_id,
        package_type=str(handoff_package_draft["package_type"]),
        case_type=_optional_str(handoff_package_draft.get("case_type")),
        worker_id=worker_id,
        masked_worker_id=str(worker_summary.get("masked_worker_id") or "worker_***"),
        risk_level=_optional_str(
            (handoff_package_draft.get("case_summary") or {}).get("risk_level")
        ),
        handoff_ready=bool(handoff_package_draft.get("handoff_ready")),
        handoff_blockers=_json_dumps(handoff_package_draft.get("handoff_blockers") or []),
        package_json=package_json,
        approval_required=True,
        status=HANDOFF_INITIAL_STATUS,
        created_by=created_by,
        transferred_at=None,
    )
    db.add(draft)
    db.flush()

    approval = Approval(
        target_type=HANDOFF_TARGET_TYPE,
        target_id=draft.id,
        status=APPROVAL_INITIAL_STATUS,
        requested_by=created_by,
        reason="전문가 전달 전 담당자 승인이 필요합니다.",
    )
    db.add(approval)
    db.flush()
    draft.approval_id = approval.id

    log = EvidenceLog(
        event_type="handoff_package_draft_created",
        agent_name="handoff_package",
        tool_name=None,
        summary=HANDOFF_DRAFT_CREATED_SUMMARY,
        source_ids=_json_dumps(source_ids),
        approval_required=True,
        risk_flags=_json_dumps(risk_flags),
        request_id=request_id,
        worker_id=worker_id,
        approval_id=approval.id,
    )
    db.add(log)
    db.flush()

    return {
        "handoff_package_draft_id": draft.id,
        "approval_id": approval.id,
        "evidence_log_ids": [log.id],
        "status": draft.status,
    }


def mark_handoff_approval_reviewed(
    db: Session,
    *,
    approval: Approval,
    status: str,
) -> HandoffPackageDraft:
    if approval.target_type != HANDOFF_TARGET_TYPE:
        raise ValueError(f"Unsupported handoff approval target_type: {approval.target_type}")
    draft = db.get(HandoffPackageDraft, approval.target_id)
    if draft is None:
        raise ValueError(f"Handoff package draft not found: {approval.target_id}")
    if status not in {HANDOFF_APPROVED_STATUS, HANDOFF_REJECTED_STATUS}:
        raise ValueError(f"Unsupported handoff review status: {status}")
    draft.status = status
    # 승인/반려는 검토 상태만 바꾸며 실제 전문가 전달은 하지 않습니다.
    draft.transferred_at = None
    db.flush()
    return draft


def approve_handoff_package_draft(
    db: Session,
    *,
    draft_id: str,
    company_id: str | None,
    reviewed_by: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return _review_handoff_package_draft(
        db,
        draft_id=draft_id,
        company_id=company_id,
        reviewed_by=reviewed_by,
        reason=reason,
        approval_status=HANDOFF_APPROVED_STATUS,
        draft_status=HANDOFF_APPROVED_STATUS,
        event_type="handoff_package_draft_approved",
        summary=HANDOFF_DRAFT_APPROVED_SUMMARY,
    )


def reject_handoff_package_draft(
    db: Session,
    *,
    draft_id: str,
    company_id: str | None,
    reviewed_by: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return _review_handoff_package_draft(
        db,
        draft_id=draft_id,
        company_id=company_id,
        reviewed_by=reviewed_by,
        reason=reason,
        approval_status=HANDOFF_REJECTED_STATUS,
        draft_status=HANDOFF_REJECTED_STATUS,
        event_type="handoff_package_draft_rejected",
        summary=HANDOFF_DRAFT_REJECTED_SUMMARY,
    )


def get_handoff_package_draft_detail(
    db: Session,
    draft_id: str,
    company_id: str,
) -> dict[str, Any]:
    draft = get_handoff_draft_for_company(
        db,
        draft_id=draft_id,
        company_id=company_id,
    )
    try:
        package = json.loads(draft.package_json)
    except json.JSONDecodeError as exc:
        raise ValueError("handoff package_json is not valid JSON") from exc

    approval = db.get(Approval, draft.approval_id) if draft.approval_id else None
    detail = _safe_detail_view(draft, package, approval)
    _validate_no_forbidden_payload(detail)
    return detail


def _review_handoff_package_draft(
    db: Session,
    *,
    draft_id: str,
    company_id: str | None,
    reviewed_by: str | None,
    reason: str | None,
    approval_status: str,
    draft_status: str,
    event_type: str,
    summary: str,
) -> dict[str, Any]:
    draft = get_handoff_draft_for_company(
        db,
        draft_id=draft_id,
        company_id=company_id,
    )
    approval = _get_reviewable_handoff_approval(db, draft)
    if reason:
        _validate_safe_text(reason)
    if reviewed_by:
        _validate_safe_text(reviewed_by)

    approval.status = approval_status
    approval.reviewed_by = reviewed_by
    approval.reviewed_at = _now()
    if reason:
        approval.reason = reason
    draft.status = draft_status
    # 승인/반려는 review decision만 남기며 실제 전문가 전달은 하지 않습니다.
    draft.transferred_at = None

    log = EvidenceLog(
        event_type=event_type,
        agent_name="handoff_package",
        tool_name=None,
        summary=summary,
        source_ids=_json_dumps([]),
        approval_required=True,
        risk_flags=_json_dumps([]),
        request_id=draft.request_id,
        worker_id=draft.worker_id,
        approval_id=approval.id,
    )
    db.add(log)
    db.flush()

    return {
        "draft_id": draft.id,
        "approval_id": approval.id,
        "status": draft.status,
        "approval_status": approval.status,
        "transferred_at": _datetime_to_str(draft.transferred_at),
    }


def _get_reviewable_handoff_approval(
    db: Session,
    draft: HandoffPackageDraft,
) -> Approval:
    if draft.status != HANDOFF_INITIAL_STATUS:
        raise HandoffApprovalConflictError("handoff package draft is already reviewed")
    if not draft.approval_id:
        raise HandoffApprovalConflictError("handoff package draft approval is not linked")
    approval = db.get(Approval, draft.approval_id)
    if approval is None:
        raise HandoffApprovalConflictError("handoff package draft approval is not linked")
    if approval.target_type != HANDOFF_TARGET_TYPE or approval.target_id != draft.id:
        raise HandoffApprovalConflictError("handoff package draft approval is not linked")
    if approval.status != APPROVAL_INITIAL_STATUS:
        raise HandoffApprovalConflictError("handoff package draft approval is already reviewed")
    return approval


def get_handoff_draft_for_company(
    db: Session,
    *,
    draft_id: str,
    company_id: str | None,
) -> HandoffPackageDraft:
    draft = db.get(HandoffPackageDraft, draft_id)
    if draft is None:
        raise HandoffPackageDraftNotFoundError(
            f"Handoff package draft not found: {draft_id}"
        )
    _validate_company_scope(draft, company_id)
    return draft


def get_handoff_draft_by_approval_for_company(
    db: Session,
    *,
    approval_id: str,
    company_id: str | None,
) -> tuple[Approval, HandoffPackageDraft]:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HandoffPackageDraftNotFoundError(
            f"Handoff approval not found: {approval_id}"
        )
    if approval.target_type != HANDOFF_TARGET_TYPE:
        raise HandoffPackageDraftNotFoundError(
            f"Handoff approval not found: {approval_id}"
        )
    draft = get_handoff_draft_for_company(
        db,
        draft_id=approval.target_id,
        company_id=company_id,
    )
    return approval, draft


def _validate_company_scope(
    draft: HandoffPackageDraft,
    company_id: str | None,
) -> None:
    if not company_id:
        raise HandoffPackageDraftForbiddenError("handoff package draft access forbidden")
    if draft.company_id != company_id:
        raise HandoffPackageDraftForbiddenError("handoff package draft access forbidden")


def _validate_handoff_draft_contract(draft: dict[str, Any]) -> None:
    if draft.get("package_type") != "expert_handoff_draft":
        raise ValueError("handoff package must be expert_handoff_draft")
    if draft.get("approval_required") is not True:
        raise ValueError("handoff package must require approval")
    approval = draft.get("approval") or {}
    if approval.get("status") != APPROVAL_INITIAL_STATUS:
        raise ValueError("handoff package approval status must be PENDING")
    if draft.get("not_for_legal_judgment") is not True:
        raise ValueError("handoff package must not be for legal judgment")
    if draft.get("raw_worker_reply_included") is not False:
        raise ValueError("handoff package must not include raw worker reply")
    if draft.get("full_translation_included") is not False:
        raise ValueError("handoff package must not include full translation")
    if draft.get("message_body_included") is not False:
        raise ValueError("handoff package must not include message body")
    _validate_no_forbidden_payload(draft)


def _safe_package_json(draft: dict[str, Any]) -> str:
    worker_summary = draft.get("worker_summary") or {}
    contact_summary = draft.get("contact_summary") or {}
    evidence = draft.get("evidence") or {}
    approval = draft.get("approval") or {}
    package = {
        "package_type": draft.get("package_type"),
        "case_type": draft.get("case_type"),
        "case_summary": draft.get("case_summary") or {},
        "worker_summary": {
            "masked_worker_id": worker_summary.get("masked_worker_id"),
            "visa_type": worker_summary.get("visa_type"),
            "stay_expires_at": worker_summary.get("stay_expires_at"),
            "contract_ends_at": worker_summary.get("contract_ends_at"),
        },
        "document_summary": draft.get("document_summary") or {},
        "contact_summary": {
            "last_contact_summary": contact_summary.get("last_contact_summary"),
            "message_draft_exists": contact_summary.get("message_draft_exists"),
            "raw_worker_reply_included": False,
            "full_translation_included": False,
        },
        "evidence": {
            "citation_ids": evidence.get("citation_ids") or [],
            "evidence_log_ids": evidence.get("evidence_log_ids") or [],
            "not_for_legal_judgment": True,
        },
        "approval": {
            "approval_required": True,
            "status": approval.get("status") or APPROVAL_INITIAL_STATUS,
        },
        "handoff_ready": bool(draft.get("handoff_ready")),
        "handoff_blockers": draft.get("handoff_blockers") or [],
        "risk_flags": draft.get("risk_flags") or [],
    }
    _validate_no_forbidden_payload(package)
    return _json_dumps(package)


def _safe_detail_view(
    draft: HandoffPackageDraft,
    package: dict[str, Any],
    approval: Approval | None,
) -> dict[str, Any]:
    worker_summary = package.get("worker_summary") or {}
    contact_summary = package.get("contact_summary") or {}
    evidence = package.get("evidence") or {}
    return {
        "id": draft.id,
        "package_type": draft.package_type,
        "status": draft.status,
        "approval_required": draft.approval_required,
        "approval_id": draft.approval_id,
        "approval_status": approval.status if approval else None,
        "transferred_at": _datetime_to_str(draft.transferred_at),
        "not_for_legal_judgment": bool(package.get("not_for_legal_judgment", True))
        and bool(evidence.get("not_for_legal_judgment", True)),
        "handoff_ready": draft.handoff_ready,
        "handoff_blockers": _json_loads_list(draft.handoff_blockers),
        "case_summary": package.get("case_summary") or {},
        "worker_summary": {
            "masked_worker_id": worker_summary.get("masked_worker_id"),
            "visa_type": worker_summary.get("visa_type"),
            "stay_expires_at": worker_summary.get("stay_expires_at"),
            "contract_ends_at": worker_summary.get("contract_ends_at"),
        },
        "document_summary": package.get("document_summary") or {},
        "contact_summary": {
            "raw_worker_reply_included": bool(
                contact_summary.get("raw_worker_reply_included")
            ),
            "full_translation_included": bool(
                contact_summary.get("full_translation_included")
            ),
            "message_body_included": bool(
                contact_summary.get("message_body_included")
            ),
        },
        "evidence": {
            "citation_ids": [str(item) for item in evidence.get("citation_ids", [])],
            "evidence_log_ids": [
                str(item) for item in evidence.get("evidence_log_ids", [])
            ],
            "not_for_legal_judgment": bool(
                evidence.get("not_for_legal_judgment", True)
            ),
        },
        "created_at": _datetime_to_str(draft.created_at),
        "updated_at": _datetime_to_str(draft.updated_at),
    }


def _validate_no_forbidden_payload(value: Any) -> None:
    _walk_forbidden(value)


def _walk_forbidden(value: Any, key: str | None = None) -> None:
    if key and key in _FORBIDDEN_KEYS:
        raise ValueError(f"handoff package contains forbidden key: {key}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _walk_forbidden(child_value, str(child_key))
        return
    if isinstance(value, list):
        for item in value:
            _walk_forbidden(item, key=None)
        return
    if isinstance(value, str):
        _validate_safe_text(value)


def _validate_safe_text(text: str) -> None:
    for marker in _FORBIDDEN_TEXT_MARKERS:
        if marker in text:
            raise ValueError("handoff package contains forbidden text marker")
    if _ALIEN_REGISTRATION_RE.search(text):
        raise ValueError("handoff package contains raw alien registration number")
    if _PHONE_RE.search(text):
        raise ValueError("handoff package contains raw phone number")
    if _PASSPORT_RE.search(text):
        raise ValueError("handoff package contains raw passport number")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _datetime_to_str(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)
