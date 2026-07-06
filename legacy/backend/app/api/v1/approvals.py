from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import get_sync_db
from backend.app.services.approval_service import (
    ApprovalConflictError,
    ApprovalForbiddenError,
    ApprovalNotFoundError,
    ApprovalValidationError,
    approve_approval_for_company,
    get_approval_detail_for_company,
    list_approvals_for_company,
    reject_approval_for_company,
)
from app.services.daily_briefing_service import (
    build_sqlalchemy_daily_briefing_service,
    resolve_daily_briefing_allowed_company_ids,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalReviewRequest(BaseModel):
    reviewed_by: str | None = None
    reason: str | None = None


class ApprovalResponse(BaseModel):
    approval_id: str
    target_type: str
    target_id: str
    approval_status: str
    target_status: str
    approval_required: bool
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    reason: str | None = None


@router.get("")
def list_approvals(
    status: str = Query(default="PENDING"),
    target_type: str | None = Query(default=None),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return list_approvals_for_company(
            db,
            company_id=x_company_id or "",
            status=status,
            target_type=target_type,
            limit=limit,
            offset=offset,
        )
    except ApprovalForbiddenError as exc:
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _daily_error(error_code: str, message: str, trace_id: str = "trace_unavailable") -> dict[str, str]:
    return {"error_code": error_code, "message": message, "trace_id": trace_id}


def _is_daily_briefing_approval_id(approval_id: str) -> bool:
    return approval_id.startswith("approval_")


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    if _is_daily_briefing_approval_id(approval_id):
        raise HTTPException(status_code=404, detail="approval not found")
    try:
        return get_approval_detail_for_company(
            db,
            approval_id=approval_id,
            company_id=x_company_id or "",
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail="approval not found") from exc
    except ApprovalForbiddenError as exc:
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalConflictError as exc:
        raise HTTPException(status_code=409, detail="approval conflict") from exc


@router.post("/{approval_id}/approve")
def approve_approval(
    approval_id: str,
    body: ApprovalReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    x_user_id: str = Header(default="user_unknown", alias="X-User-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or ApprovalReviewRequest()
    if _is_daily_briefing_approval_id(approval_id):
        return _approve_daily_briefing_action(
            db,
            approval_id=approval_id,
            x_company_id=x_company_id,
            x_user_role=x_user_role,
            x_user_id=x_user_id,
        )
    try:
        result = approve_approval_for_company(
            db,
            approval_id=approval_id,
            company_id=x_company_id or "",
            reviewed_by=request.reviewed_by,
            reason=request.reason,
        )
        db.commit()
        return result
    except ApprovalNotFoundError:
        db.rollback()
    except ApprovalForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="approval conflict") from exc
    except ApprovalValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="approval review input invalid") from exc

    return _approve_daily_briefing_action(
        db,
        approval_id=approval_id,
        x_company_id=x_company_id,
        x_user_role=x_user_role,
        x_user_id=x_user_id,
    )


@router.post("/{approval_id}/reject")
def reject_approval(
    approval_id: str,
    body: ApprovalReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    x_user_id: str = Header(default="user_unknown", alias="X-User-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or ApprovalReviewRequest()
    if _is_daily_briefing_approval_id(approval_id):
        return _reject_daily_briefing_action(
            db,
            approval_id=approval_id,
            reason=request.reason or "",
            x_company_id=x_company_id,
            x_user_role=x_user_role,
            x_user_id=x_user_id,
        )
    try:
        result = reject_approval_for_company(
            db,
            approval_id=approval_id,
            company_id=x_company_id or "",
            reviewed_by=request.reviewed_by,
            reason=request.reason,
        )
        db.commit()
        return result
    except ApprovalNotFoundError:
        db.rollback()
    except ApprovalForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="approval conflict") from exc
    except ApprovalValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="approval review input invalid") from exc

    return _reject_daily_briefing_action(
        db,
        approval_id=approval_id,
        reason=request.reason or "",
        x_company_id=x_company_id,
        x_user_role=x_user_role,
        x_user_id=x_user_id,
    )


@router.post("/{approval_id}/request-revision")
def request_revision(
    approval_id: str,
    body: ApprovalReviewRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    x_user_id: str = Header(default="user_unknown", alias="X-User-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
    )
    try:
        response = service.request_revision(
            approval_id,
            approver_id=x_user_id,
            user_role=x_user_role,
            reason=body.reason or "",
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail=_daily_error(str(exc.args[0]), "Only manager or admin can request a revision."),
        ) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=_daily_error(str(exc.args[0]), "Approval target was not found."),
        ) from exc
    return response.model_dump()


def _approve_daily_briefing_action(
    db: Session,
    *,
    approval_id: str,
    x_company_id: str | None,
    x_user_role: str,
    x_user_id: str,
) -> dict[str, Any]:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
    )
    try:
        response = service.approve_action(
            approval_id,
            approver_id=x_user_id,
            user_role=x_user_role,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail=_daily_error(str(exc.args[0]), "Only manager or admin can approve this action."),
        ) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=_daily_error(str(exc.args[0]), "Approval target was not found."),
        ) from exc

    action_id = response.action_id
    action = service.repository.actions.get(action_id)
    if action is not None:
        try:
            _create_contact_threads_for_action(
                db=db,
                action_id=action_id,
                action_type=action.action_type,
                subject_id=action.subject_id,
                company_id=x_company_id or (allowed_company_ids[0] if allowed_company_ids else None),
                user_id=x_user_id,
            )
        except Exception as exc:
            logger.warning("contact thread creation failed after approval: %s", exc)

    return response.model_dump()


def _create_contact_threads_for_action(
    *,
    db: Session,
    action_id: str,
    action_type: str,
    subject_id: str,
    company_id: str | None,
    user_id: str,
) -> None:
    from app.services.contact_thread_service import create_message_draft
    from app.services.auth_service import SCRIVENER_WORKER_ID

    if action_type == "request_document":
        create_message_draft(
            worker_id=subject_id,
            company_id=company_id,
            message_purpose="missing_document_request",
            due_date=None,
            user_id=user_id,
            db=db,
            source_action_id=action_id,
        )
    elif action_type == "create_handoff":
        create_message_draft(
            worker_id=SCRIVENER_WORKER_ID,
            company_id=company_id,
            message_purpose="handoff_notification",
            due_date=None,
            user_id=user_id,
            db=db,
            source_action_id=action_id,
        )


def _reject_daily_briefing_action(
    db: Session,
    *,
    approval_id: str,
    reason: str,
    x_company_id: str | None,
    x_user_role: str,
    x_user_id: str,
) -> dict[str, Any]:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
    )
    try:
        response = service.reject_action(
            approval_id,
            approver_id=x_user_id,
            user_role=x_user_role,
            reason=reason,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail=_daily_error(str(exc.args[0]), "Only manager or admin can reject this action."),
        ) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=_daily_error(str(exc.args[0]), "Approval target was not found."),
        ) from exc
    return response.model_dump()
