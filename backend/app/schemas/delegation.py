from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class DelegationOut(BaseModel):
    """GET /api/v1/delegations/mine 응답 — 현재 세션 사용자가 delegate인 유효한 위임(R2.4)."""

    delegation_id: str
    delegator_user_id: str
    delegator_name: str
    ends_at: dt.datetime
