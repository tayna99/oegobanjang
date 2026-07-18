"""위임 조회 서비스 — GET /api/v1/delegations/mine(R2.4). docs/DB_SCHEMA.md §4.1, §13-10."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delegation import Delegation
from app.models.user import User
from app.schemas.delegation import DelegationOut


def get_my_delegation(db: Session, company_id: str, delegate_user_id: str) -> DelegationOut | None:
    """현재 세션 사용자가 delegate인 유효(기간 내·미철회·scope='approval') 위임 1건.

    복수 위임을 가정하지 않는다(현재 UI·시드가 1인 1위임 전제) — 여러 건이면 가장 최근
    시작한 것을 반환한다.
    """
    now = dt.datetime.now(dt.timezone.utc)
    delegation = db.execute(
        select(Delegation)
        .where(
            Delegation.company_id == company_id,
            Delegation.delegate_user_id == delegate_user_id,
            Delegation.scope == "approval",
            Delegation.revoked_at.is_(None),
            Delegation.starts_at <= now,
            Delegation.ends_at > now,
        )
        .order_by(Delegation.starts_at.desc())
    ).scalars().first()
    if delegation is None:
        return None
    delegator = db.get(User, delegation.delegator_user_id)
    return DelegationOut(
        delegation_id=delegation.id,
        delegator_user_id=delegation.delegator_user_id,
        delegator_name=delegator.name if delegator else delegation.delegator_user_id,
        ends_at=delegation.ends_at,
    )
