"""위임 조회 엔드포인트 — GET /api/v1/delegations/mine(R2.4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.delegation import DelegationOut
from app.services.delegations import get_my_delegation

router = APIRouter(prefix="/api/v1/delegations", tags=["delegations"])


@router.get("/mine", response_model=DelegationOut | None)
def get_mine(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> DelegationOut | None:
    return get_my_delegation(db, membership.company_id, membership.user_id)
