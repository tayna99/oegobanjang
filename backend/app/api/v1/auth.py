"""phone+OTP 로그인 엔드포인트. docs/DB_SCHEMA.md §13-11."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import _bearer_scheme, get_current_user_id
from app.config import get_settings
from app.db.session import get_db
from app.domain.auth_exceptions import (
    AuthError,
    OtpAttemptsExceededError,
    OtpCodeMismatchError,
    OtpExpiredError,
    OtpNotFoundError,
    UserNotFoundError,
)
from app.models.membership import Membership
from app.models.user import User
from app.schemas.auth import (
    MeResponse,
    MembershipOut,
    OtpRequestRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    SessionUserOut,
)
from app.services.auth import request_otp, revoke_session, verify_otp

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ERROR_STATUS: dict[type[AuthError], int] = {
    OtpNotFoundError: status.HTTP_404_NOT_FOUND,
    OtpExpiredError: status.HTTP_410_GONE,
    OtpAttemptsExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    OtpCodeMismatchError: status.HTTP_401_UNAUTHORIZED,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
}


@router.post("/otp/request", response_model=OtpRequestResponse)
def request_otp_endpoint(payload: OtpRequestRequest, db: Session = Depends(get_db)) -> OtpRequestResponse:
    code, ttl_seconds = request_otp(db, payload.phone)
    return OtpRequestResponse(
        requested=True,
        expires_in_seconds=ttl_seconds,
        debug_code=code if get_settings().is_local else None,
    )


def _load_user_with_memberships(db: Session, user_id: str) -> tuple[User, list[MembershipOut]]:
    """세션에 연결된 사용자 + 활성 멤버십을 조인 1회로 가져온다(코드리뷰 효율 지적 — 이전엔
    verify와 me가 각자 User 단건조회 + Membership 별도조회로 왕복을 2번씩 썼다).

    세션 자체는 유효했지만(만료·폐기 아님) 사용자 행이 없는 경우(예: 관리자가 계정을 삭제했지만
    세션은 아직 안 지운 경우) None 대신 401을 낸다 — get_current_user_id는 세션만 검증하고
    users 테이블 존재 여부는 보지 않으므로, 여기서 걸러주지 않으면 SessionUserOut.model_validate(None)이
    처리되지 않은 500으로 새는 것을 코드리뷰가 확인했다.
    """
    rows = db.execute(
        select(User, Membership)
        .outerjoin(Membership, (Membership.user_id == User.id) & (Membership.status == "active"))
        .where(User.id == user_id)
    ).all()
    if not rows:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "세션에 연결된 사용자를 찾을 수 없습니다")
    user = rows[0][0]
    memberships = [MembershipOut.model_validate(m) for _, m in rows if m is not None]
    return user, memberships


@router.post("/otp/verify", response_model=OtpVerifyResponse)
def verify_otp_endpoint(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> OtpVerifyResponse:
    try:
        raw_token, user_id, expires_at = verify_otp(db, payload.phone, payload.code)
    except AuthError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    user, memberships = _load_user_with_memberships(db, user_id)
    return OtpVerifyResponse(
        session_token=raw_token,
        expires_at=expires_at,
        user=SessionUserOut.model_validate(user),
        # 코드리뷰 효율 지적: 프론트가 role 파생을 위해 verify 직후 별도로 /me를 또 부르고
        # 있었다(로그인마다 왕복 2회) — verify 응답에 멤버십을 함께 실어 그 왕복을 없앤다.
        memberships=memberships,
    )


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MeResponse:
    """세션에서 신원 + 회사별 역할을 되돌려준다 — roleStore가 새로고침 후에도 세션에서
    다시 파생할 수 있는 최소 read endpoint(R2.2)."""
    user, memberships = _load_user_with_memberships(db, current_user_id)
    return MeResponse(user=SessionUserOut.model_validate(user), memberships=memberships)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> None:
    """세션 폐기. 이미 무효한 토큰으로 호출해도 204(로그아웃은 멱등) — 어드버서리얼 보안
    리뷰가 지적한 "30일 토큰을 즉시 무효화할 수단이 없다"는 갭을 닫는다."""
    if credentials is not None and credentials.credentials:
        revoke_session(db, credentials.credentials)
