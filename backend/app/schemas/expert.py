from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field


class ExpertGrantIssueRequest(BaseModel):
    """POST /api/v1/expert/grants — spec §7.2 "행정사 관리" 탭의 초대 입력.

    office_name/business_registration_no로 기존 사무소를 찾거나(business_registration_no
    일치) 새로 만든다. office_contact_email/name은 신규 사무소일 때만 쓰인다(spec §3.2
    "사무소 담당자 이메일 입력" — 최초 ExpertOfficeMember 부트스트랩, isOfficeAdmin=true).
    """

    office_name: str = Field(min_length=1)
    business_registration_no: str | None = None
    office_contact_email: EmailStr
    office_contact_name: str = Field(min_length=1)
    brand_initial: str = Field(min_length=1, max_length=2)
    brand_color: str = Field(min_length=1)
    until: dt.date  # 필수 — 무기한 위탁 금지(결정 C)
    from_: dt.date | None = Field(default=None, alias="from")
    review_interval_days: int | None = None

    model_config = {"populate_by_name": True}


class ExpertGrantOut(BaseModel):
    id: str
    status: str
    expert_account_id: str
    tenant_id: str
    scope: str
    granted_by: str
    basis: str
    from_date: dt.date
    until_date: dt.date
    review_interval_days: int
    revoked_reason: str | None = None

    model_config = {"from_attributes": True}


class ExpertOfficeMemberCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1)
    is_office_admin: bool = False


class ExpertOfficeMemberUpdateRequest(BaseModel):
    status: str | None = None  # 'active' | 'suspended'
    is_office_admin: bool | None = None


class ExpertOfficeMemberOut(BaseModel):
    id: str
    expert_account_id: str
    name: str
    email: str
    status: str
    is_office_admin: bool

    model_config = {"from_attributes": True}


class ExpertOtpRequestRequest(BaseModel):
    email: EmailStr


class ExpertOtpRequestResponse(BaseModel):
    requested: bool
    expires_in_seconds: int
    debug_code: str | None = None  # local 환경 전용(app.config.Settings.is_local)


class ExpertOtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1)


class ExpertOtpVerifyResponse(BaseModel):
    session_token: str
    expires_at: dt.datetime
    member: ExpertOfficeMemberOut


class ExpertPackageViewOut(BaseModel):
    """GET /api/v1/expert/packages/{package_id} — spec §4.2/§6. PackageLinkStatus(R2.6)와
    동일한 스코프 노트: 문서 콘텐츠는 포함하지 않는다. 이 응답 자체가 "3중 체크를
    통과했다"는 신호이자 PackageViewLog 1행이 기록됐다는 확인이다."""

    package_id: str
    tenant_id: str
    viewed_at: dt.datetime
