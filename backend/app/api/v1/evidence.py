from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_sync_db
from backend.app.services.evidence_service import (
    EvidenceForbiddenError,
    list_evidence_logs_for_request,
)


router = APIRouter(prefix="/evidence", tags=["evidence"])


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


@router.get("", response_model=EvidenceListResponse)
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
