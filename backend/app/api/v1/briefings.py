"""최신 브리핑 조회 엔드포인트 — GET /api/v1/briefings/latest(R2.3). docs/DB_SCHEMA.md §4.9."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.briefing import BriefingOut
from app.services.briefings import get_latest_briefing_out

router = APIRouter(prefix="/api/v1/briefings", tags=["briefings"])


@router.get("/latest", response_model=BriefingOut)
def get_latest_briefing(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> BriefingOut:
    briefing = get_latest_briefing_out(db, membership.company_id)
    if briefing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "브리핑이 없습니다")
    return briefing
