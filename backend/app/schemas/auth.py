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


class OtpVerifyResponse(BaseModel):
    session_token: str
    expires_at: dt.datetime
    user: SessionUserOut


class MembershipOut(BaseModel):
    """R2.2 — 프론트 roleStore를 세션에서 파생시키기 위한 최소 정보(company_id·role)만."""

    company_id: str
    role: str

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: SessionUserOut
    membership: MembershipOut | None  # 활성 소속이 없으면 None(초대 대기 등)
