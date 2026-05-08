from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
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
    reject_approval_for_company,
)


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


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
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


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_approval(
    approval_id: str,
    body: ApprovalReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or ApprovalReviewRequest()
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
    except ApprovalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="approval not found") from exc
    except ApprovalForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="approval conflict") from exc
    except ApprovalValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="approval review input invalid",
        ) from exc


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_approval(
    approval_id: str,
    body: ApprovalReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or ApprovalReviewRequest()
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
    except ApprovalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="approval not found") from exc
    except ApprovalForbiddenError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="approval access forbidden") from exc
    except ApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="approval conflict") from exc
    except ApprovalValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="approval review input invalid",
        ) from exc
