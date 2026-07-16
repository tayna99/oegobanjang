"""phone+OTP 로그인 엔드포인트. docs/DB_SCHEMA.md §13-11."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import _bearer_scheme
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
from app.models.user import User
from app.schemas.auth import (
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


@router.post("/otp/verify", response_model=OtpVerifyResponse)
def verify_otp_endpoint(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> OtpVerifyResponse:
    try:
        raw_token, user_id, expires_at = verify_otp(db, payload.phone, payload.code)
    except AuthError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    user = db.get(User, user_id)
    return OtpVerifyResponse(
        session_token=raw_token,
        expires_at=expires_at,
        user=SessionUserOut.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> None:
    """세션 폐기. 이미 무효한 토큰으로 호출해도 204(로그아웃은 멱등) — 어드버서리얼 보안
    리뷰가 지적한 "30일 토큰을 즉시 무효화할 수단이 없다"는 갭을 닫는다."""
    if credentials is not None and credentials.credentials:
        revoke_session(db, credentials.credentials)
