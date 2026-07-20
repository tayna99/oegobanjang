"""행정사 화이트라벨 v1 API(R5.1) — 위탁 발급/승인/철회·목록, 사무소 구성원 CRUD,
email+OTP 세션 로그인, 패키지 조회(3중 체크 + PackageViewLog).

spec: reference/specs/7-1_행정사_화이트라벨_v1.md. 두 개의 서로 다른 인증 스킴이 이
라우터 안에 공존한다 — /grants, /auth/otp/*는 내부 세션(get_current_membership, 고객사
담당자), 나머지(/office-members/*, /packages/*)는 화이트라벨 세션(get_current_expert_member,
행정사무소 구성원)이다. 패키지 조회 자체의 로직(3중 체크 + PackageViewLog 기록)은
services/packages.py에 있다(중복 구현 금지 — task 지시).
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.api.expert_deps import get_current_expert_member
from app.config import get_settings
from app.db.session import get_db
from app.domain.expert_exceptions import (
    ExpertAuthError,
    ExpertError,
    ExpertGrantForbiddenError,
    ExpertGrantInvalidTransitionError,
    ExpertGrantNotFoundError,
    ExpertGrantUnboundedError,
    ExpertMemberNotRegisteredError,
    ExpertMemberSuspendedError,
    ExpertOfficeMemberForbiddenError,
    ExpertOfficeMemberNotFoundError,
    ExpertOtpAttemptsExceededError,
    ExpertOtpCodeMismatchError,
    ExpertOtpExpiredError,
    ExpertOtpNotFoundError,
    ExpertPackageNotFoundError,
)
from app.models.expert import ExpertOfficeMember
from app.models.membership import Membership
from app.schemas.expert import (
    ExpertGrantIssueRequest,
    ExpertGrantOut,
    ExpertOfficeMemberCreateRequest,
    ExpertOfficeMemberOut,
    ExpertOfficeMemberUpdateRequest,
    ExpertOtpRequestRequest,
    ExpertOtpRequestResponse,
    ExpertOtpVerifyRequest,
    ExpertOtpVerifyResponse,
    ExpertPackageViewOut,
)
from app.services.expert import (
    authorize_grant,
    create_office_member,
    issue_grant,
    list_grants,
    list_office_members,
    request_expert_otp,
    revoke_grant,
    update_office_member,
    verify_expert_otp_and_login,
)
from app.services.packages import view_expert_package

router = APIRouter(prefix="/api/v1/expert", tags=["expert"])

_GRANT_ERROR_STATUS: dict[type[ExpertError], int] = {
    ExpertGrantForbiddenError: status.HTTP_403_FORBIDDEN,
    ExpertGrantNotFoundError: status.HTTP_404_NOT_FOUND,
    ExpertGrantInvalidTransitionError: status.HTTP_409_CONFLICT,
    ExpertGrantUnboundedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}
_OFFICE_MEMBER_ERROR_STATUS: dict[type[ExpertError], int] = {
    ExpertOfficeMemberForbiddenError: status.HTTP_403_FORBIDDEN,
    ExpertOfficeMemberNotFoundError: status.HTTP_404_NOT_FOUND,
}
_AUTH_ERROR_STATUS: dict[type[ExpertAuthError], int] = {
    ExpertOtpNotFoundError: status.HTTP_404_NOT_FOUND,
    ExpertOtpExpiredError: status.HTTP_410_GONE,
    ExpertOtpAttemptsExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    ExpertOtpCodeMismatchError: status.HTTP_401_UNAUTHORIZED,
    ExpertMemberNotRegisteredError: status.HTTP_404_NOT_FOUND,
    ExpertMemberSuspendedError: status.HTTP_403_FORBIDDEN,
}


def _raise(exc: ExpertError, table: dict[type[ExpertError], int]) -> NoReturn:
    raise HTTPException(table.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc


# ---------------------------------------------------------------------------
# 위탁(Grant) — 내부 세션(owner/manager). spec §7.2
# ---------------------------------------------------------------------------


@router.post("/grants", response_model=ExpertGrantOut, status_code=status.HTTP_201_CREATED)
def issue_grant_endpoint(
    payload: ExpertGrantIssueRequest,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> ExpertGrantOut:
    try:
        grant = issue_grant(db, membership, payload)
    except ExpertError as exc:
        _raise(exc, _GRANT_ERROR_STATUS)
    return ExpertGrantOut.model_validate(grant)


@router.post("/grants/{grant_id}/authorize", response_model=ExpertGrantOut)
def authorize_grant_endpoint(
    grant_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> ExpertGrantOut:
    try:
        grant = authorize_grant(db, membership, grant_id)
    except ExpertError as exc:
        _raise(exc, _GRANT_ERROR_STATUS)
    return ExpertGrantOut.model_validate(grant)


@router.post("/grants/{grant_id}/revoke", response_model=ExpertGrantOut)
def revoke_grant_endpoint(
    grant_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> ExpertGrantOut:
    try:
        grant = revoke_grant(db, membership, grant_id)
    except ExpertError as exc:
        _raise(exc, _GRANT_ERROR_STATUS)
    return ExpertGrantOut.model_validate(grant)


@router.get("/grants", response_model=list[ExpertGrantOut])
def list_grants_endpoint(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[ExpertGrantOut]:
    try:
        grants = list_grants(db, membership)
    except ExpertError as exc:
        _raise(exc, _GRANT_ERROR_STATUS)
    return [ExpertGrantOut.model_validate(g) for g in grants]


# ---------------------------------------------------------------------------
# 화이트라벨 세션 로그인(spec §3, email+OTP) — 공개 엔드포인트
# ---------------------------------------------------------------------------


@router.post("/auth/otp/request", response_model=ExpertOtpRequestResponse)
def request_expert_otp_endpoint(payload: ExpertOtpRequestRequest, db: Session = Depends(get_db)) -> ExpertOtpRequestResponse:
    code, ttl_seconds = request_expert_otp(db, payload.email)
    return ExpertOtpRequestResponse(
        requested=True, expires_in_seconds=ttl_seconds, debug_code=code if get_settings().is_local else None
    )


@router.post("/auth/otp/verify", response_model=ExpertOtpVerifyResponse)
def verify_expert_otp_endpoint(payload: ExpertOtpVerifyRequest, db: Session = Depends(get_db)) -> ExpertOtpVerifyResponse:
    try:
        raw_token, member, expires_at = verify_expert_otp_and_login(db, payload.email, payload.code)
    except ExpertAuthError as exc:
        _raise(exc, _AUTH_ERROR_STATUS)
    return ExpertOtpVerifyResponse(
        session_token=raw_token, expires_at=expires_at, member=ExpertOfficeMemberOut.model_validate(member)
    )


# ---------------------------------------------------------------------------
# 사무소 구성원 CRUD(spec §5.6) — 화이트라벨 세션(사무소 자체 오너십)
# ---------------------------------------------------------------------------


@router.get("/office-members", response_model=list[ExpertOfficeMemberOut])
def list_office_members_endpoint(
    member: ExpertOfficeMember = Depends(get_current_expert_member),
    db: Session = Depends(get_db),
) -> list[ExpertOfficeMemberOut]:
    return [ExpertOfficeMemberOut.model_validate(m) for m in list_office_members(db, member)]


@router.post("/office-members", response_model=ExpertOfficeMemberOut, status_code=status.HTTP_201_CREATED)
def create_office_member_endpoint(
    payload: ExpertOfficeMemberCreateRequest,
    member: ExpertOfficeMember = Depends(get_current_expert_member),
    db: Session = Depends(get_db),
) -> ExpertOfficeMemberOut:
    try:
        created = create_office_member(db, member, payload)
    except ExpertError as exc:
        _raise(exc, _OFFICE_MEMBER_ERROR_STATUS)
    return ExpertOfficeMemberOut.model_validate(created)


@router.patch("/office-members/{member_id}", response_model=ExpertOfficeMemberOut)
def update_office_member_endpoint(
    member_id: str,
    payload: ExpertOfficeMemberUpdateRequest,
    member: ExpertOfficeMember = Depends(get_current_expert_member),
    db: Session = Depends(get_db),
) -> ExpertOfficeMemberOut:
    try:
        updated = update_office_member(db, member, member_id, payload)
    except ExpertError as exc:
        _raise(exc, _OFFICE_MEMBER_ERROR_STATUS)
    return ExpertOfficeMemberOut.model_validate(updated)


# ---------------------------------------------------------------------------
# 패키지 조회(spec §4.2/§6) — 화이트라벨 세션, 3중 체크 + PackageViewLog
# ---------------------------------------------------------------------------


@router.get("/packages/{package_id}", response_model=ExpertPackageViewOut)
def view_expert_package_endpoint(
    package_id: str,
    member: ExpertOfficeMember = Depends(get_current_expert_member),
    db: Session = Depends(get_db),
) -> ExpertPackageViewOut:
    try:
        pkg, viewed_at = view_expert_package(db, member, package_id)
    except ExpertPackageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ExpertPackageViewOut(package_id=pkg.id, tenant_id=pkg.company_id, viewed_at=viewed_at)
