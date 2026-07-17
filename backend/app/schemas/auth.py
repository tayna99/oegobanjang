from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class OtpRequestRequest(BaseModel):
    phone: str = Field(min_length=1)


class OtpRequestResponse(BaseModel):
    requested: bool
    expires_in_seconds: int
    debug_code: str | None = None  # local 환경에서만 채워짐(app.config.Settings.is_local)


class OtpVerifyRequest(BaseModel):
    phone: str = Field(min_length=1)
    code: str = Field(min_length=1)


class SessionUserOut(BaseModel):
    id: str
    name: str
    phone: str

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    company_id: str
    role: str

    model_config = {"from_attributes": True}


class OtpVerifyResponse(BaseModel):
    session_token: str
    expires_at: dt.datetime
    user: SessionUserOut
    # 코드리뷰 효율 지적(R2 리뷰): verify 직후 role 파생을 위해 프론트가 별도로 /me를 또
    # 부르던 왕복을 없애려고 여기 실어 보낸다 — get_me와 동일한 활성 멤버십만.
    memberships: list[MembershipOut]


class MeResponse(BaseModel):
    """GET /api/v1/auth/me — 프론트 roleStore가 새로고침 후에도 세션에서 role을 다시
    파생할 수 있게 하는 최소 read endpoint(R2.2, NEXT_ROADMAP M-6). memberships는
    status='active'인 것만 반환한다 — removed/invited 상태는 role 판단에서 제외."""

    user: SessionUserOut
    memberships: list[MembershipOut]
