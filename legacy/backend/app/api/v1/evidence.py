from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.daily_briefing_service import (
    build_sqlalchemy_daily_briefing_service,
    resolve_daily_briefing_allowed_company_ids,
)
from backend.app.db.session import get_sync_db
from backend.app.services.evidence_service import (
    EvidenceForbiddenError,
    list_evidence_logs_for_request,
)


router = APIRouter(tags=["evidence"])


class EvidenceLogResponse(BaseModel):
    id: str
    event_type: str
    agent_name: str
    tool_name: str | None = None
    summary: str
    source_ids: list[str] = Field(default_factory=list)
    approval_required: bool
    risk_flags: list[str] = Field(default_factory=list)
    request_id: str | None = None
    company_id: str | None = None
    approval_id: str | None = None
    created_at: str | None = None


class EvidenceListResponse(BaseModel):
    request_id: str
    count: int
    items: list[EvidenceLogResponse] = Field(default_factory=list)


@router.get("/evidence", response_model=EvidenceListResponse)
def list_evidence(
    request_id: str = Query(..., min_length=1),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    try:
        return list_evidence_logs_for_request(
            db,
            request_id=request_id,
            company_id=x_company_id,
        )
    except EvidenceForbiddenError as exc:
        raise HTTPException(status_code=403, detail="evidence access forbidden") from exc


@router.get("/cases/{case_id}/evidence-events")
def get_case_evidence_events(
    case_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_sync_db),
) -> list[dict]:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
    )
    try:
        events = service.get_case_evidence_events(
            case_id,
            allowed_company_ids=allowed_company_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": str(exc.args[0]),
                "message": "Requested case is outside the allowed company scope.",
                "trace_id": "trace_unavailable",
            },
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": str(exc.args[0]),
                "message": "Case evidence events were not found.",
                "trace_id": "trace_unavailable",
            },
        ) from exc
    return [event.model_dump() for event in events]


@router.get("/cases/{case_id}/audit-review")
def get_case_audit_review(
    case_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
    )
    try:
        return service.get_case_audit_review(
            case_id,
            allowed_company_ids=allowed_company_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": str(exc.args[0]),
                "message": "Requested case is outside the allowed company scope.",
                "trace_id": "trace_unavailable",
            },
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": str(exc.args[0]),
                "message": "Case audit review was not found.",
                "trace_id": "trace_unavailable",
            },
        ) from exc
