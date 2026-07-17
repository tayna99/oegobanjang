"""케이스 목록 조회 엔드포인트 — GET /api/v1/cases(R2.3). docs/DB_SCHEMA.md §4.3."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.case import CaseOut
from app.services.cases import list_cases_out

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[CaseOut]:
    return list_cases_out(db, membership.company_id)
