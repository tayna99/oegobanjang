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


class PinSetRequest(BaseModel):
    """POST /auth/pin — 승인 본인확인 PIN 등록/변경. 6자리 숫자(docs/DB_SCHEMA.md §13-12).

    otp_code: 세션만으로는 등록/변경할 수 없다 — 방금 POST /otp/request로 받은 코드를
    함께 제출해야 한다(세션 탈취자의 PIN 재설정 우회를 막는다, 코드 리뷰 P1-2).
    """

    pin: str = Field(pattern=r"^\d{6}$")
    otp_code: str = Field(min_length=1)
