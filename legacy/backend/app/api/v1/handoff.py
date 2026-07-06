from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_sync_db
from backend.app.services.handoff_persistence_service import (
    HandoffApprovalConflictError,
    HandoffPackageDraftForbiddenError,
    HandoffPackageDraftNotFoundError,
    approve_handoff_package_draft,
    get_handoff_package_draft_detail,
    reject_handoff_package_draft,
)


router = APIRouter(prefix="/handoff-package-drafts", tags=["handoff"])


class HandoffWorkerSummary(BaseModel):
    masked_worker_id: str | None = None
    visa_type: str | None = None
    stay_expires_at: str | None = None
    contract_ends_at: str | None = None


class HandoffContactSummary(BaseModel):
    raw_worker_reply_included: bool = False
    full_translation_included: bool = False
    message_body_included: bool = False


class HandoffEvidenceSummary(BaseModel):
    citation_ids: list[str] = Field(default_factory=list)
    evidence_log_ids: list[str] = Field(default_factory=list)
    not_for_legal_judgment: bool = True


class HandoffPackageDraftDetailResponse(BaseModel):
    id: str
    package_type: str
    status: str
    approval_required: bool
    approval_id: str | None = None
    approval_status: str | None = None
    transferred_at: str | None = None
    not_for_legal_judgment: bool
    handoff_ready: bool
    handoff_blockers: list[str] = Field(default_factory=list)
    case_summary: dict[str, Any] = Field(default_factory=dict)
    worker_summary: HandoffWorkerSummary
    document_summary: dict[str, Any] = Field(default_factory=dict)
    contact_summary: HandoffContactSummary
    evidence: HandoffEvidenceSummary
    created_at: str
    updated_at: str


class HandoffReviewRequest(BaseModel):
    reviewed_by: str | None = None
    reason: str | None = None


class HandoffReviewResponse(BaseModel):
    draft_id: str
    approval_id: str
    status: str
    approval_status: str
    transferred_at: str | None = None


@router.get("/{draft_id}", response_model=HandoffPackageDraftDetailResponse)
def get_handoff_package_draft(
    draft_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return get_handoff_package_draft_detail(db, draft_id, x_company_id)
    except HandoffPackageDraftNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="handoff package draft not found",
        ) from exc
    except HandoffPackageDraftForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail="handoff package draft access forbidden",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{draft_id}/approve", response_model=HandoffReviewResponse)
def approve_handoff_package_draft_endpoint(
    draft_id: str,
    body: HandoffReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or HandoffReviewRequest()
    try:
        result = approve_handoff_package_draft(
            db,
            draft_id=draft_id,
            company_id=x_company_id,
            reviewed_by=request.reviewed_by,
            reason=request.reason,
        )
        db.commit()
        return result
    except HandoffPackageDraftNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="handoff package draft not found",
        ) from exc
    except HandoffPackageDraftForbiddenError as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="handoff package draft access forbidden",
        ) from exc
    except HandoffApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="handoff package draft approval conflict",
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{draft_id}/reject", response_model=HandoffReviewResponse)
def reject_handoff_package_draft_endpoint(
    draft_id: str,
    body: HandoffReviewRequest | None = None,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    request = body or HandoffReviewRequest()
    try:
        result = reject_handoff_package_draft(
            db,
            draft_id=draft_id,
            company_id=x_company_id,
            reviewed_by=request.reviewed_by,
            reason=request.reason,
        )
        db.commit()
        return result
    except HandoffPackageDraftNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="handoff package draft not found",
        ) from exc
    except HandoffPackageDraftForbiddenError as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="handoff package draft access forbidden",
        ) from exc
    except HandoffApprovalConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="handoff package draft approval conflict",
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
