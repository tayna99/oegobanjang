"""phone+OTP 로그인 서비스 — docs/DB_SCHEMA.md §13-11.

OTP 발송은 실제 SMS 연동이 없다(§13-7 notifications 선례와 동일) — local 환경에서만
API 응답에 코드를 노출해 로그인 플로우를 끝까지 구동할 수 있게 한다.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.auth_exceptions import (
    OtpAttemptsExceededError,
    OtpCodeMismatchError,
    OtpExpiredError,
    OtpNotFoundError,
    SessionInvalidError,
    UserNotFoundError,
)
from app.domain.auth_tokens import generate_otp_code, generate_session_token, hash_secret, secrets_match
from app.models.auth import LoginOtp, UserSession
from app.models.user import User

OTP_TTL = dt.timedelta(minutes=5)
OTP_REQUEST_COOLDOWN = dt.timedelta(seconds=30)
MAX_OTP_ATTEMPTS = 5
SESSION_TTL = dt.timedelta(days=30)


def request_otp(db: Session, phone: str) -> tuple[str | None, int]:
    """(원문 코드 또는 None, TTL/남은 초)를 반환한다. 계정 존재 여부와 무관하게 항상 발급
    "성공"으로 응답한다(§13-11).

    쿨다운(어드버서리얼 보안 리뷰 F1): verify_otp는 phone당 가장 최근의 미소비 코드만 유효로
    본다. 요청 빈도에 제한이 없으면 공격자가 피해자 번호로 반복 요청만 해도 정상 발급된 코드가
    계속 새 코드에 가려져 실제 사용자가 로그인하지 못하는 방해 공격이 성립한다. 같은 phone에
    아직 유효한(미소비·미만료) 코드가 30초 이내에 발급됐으면 새 코드를 만들지 않고 남은 시간만
    반환한다 — 원문을 재저장해두지 않으므로 이 경우 code는 없다(로컬 디버그 노출도 안 함).
    """
    now = dt.datetime.now(dt.timezone.utc)
    active = db.execute(
        select(LoginOtp)
        .where(LoginOtp.phone == phone, LoginOtp.consumed_at.is_(None), LoginOtp.expires_at > now)
        .order_by(LoginOtp.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active is not None and active.created_at > now - OTP_REQUEST_COOLDOWN:
        return None, max(int((active.expires_at - now).total_seconds()), 0)

    code = generate_otp_code()
    db.add(
        LoginOtp(
            id=new_id(),
            phone=phone,
            code_hash=hash_secret(code),
            expires_at=now + OTP_TTL,
        )
    )
    db.commit()
    return code, int(OTP_TTL.total_seconds())


def _consume_otp(db: Session, phone: str, code: str) -> None:
    """phone당 가장 최근 미소비 OTP를 code와 대조하고 소비 처리한다(공용 재확인 로직).

    로그인(verify_otp)뿐 아니라 PIN 등록(set_pin)도 재사용한다 — "방금 이 전화번호로
    받은 코드를 안다"는 것 자체가 재확인의 본질이라, 세션 발급이든 PIN 변경이든 같은
    검증으로 충분하다(코드 리뷰 지적 P1-2 대응, §13-12)."""
    otp = db.execute(
        select(LoginOtp)
        .where(LoginOtp.phone == phone, LoginOtp.consumed_at.is_(None))
        .order_by(LoginOtp.created_at.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()
    if otp is None:
        raise OtpNotFoundError()

    now = dt.datetime.now(dt.timezone.utc)
    if otp.expires_at < now:
        raise OtpExpiredError()
    if otp.attempt_count >= MAX_OTP_ATTEMPTS:
        raise OtpAttemptsExceededError()

    if not secrets_match(code, otp.code_hash):
        otp.attempt_count += 1
        db.commit()
        raise OtpCodeMismatchError()

    otp.consumed_at = now
    db.flush()


def verify_otp(db: Session, phone: str, code: str) -> tuple[str, str, dt.datetime]:
    """(원문 세션 토큰, user_id, 세션 만료시각)을 반환한다."""
    _consume_otp(db, phone, code)
    now = dt.datetime.now(dt.timezone.utc)

    user = db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()
    if user is None:
        db.rollback()
        raise UserNotFoundError()

    raw_token = generate_session_token()
    session_expires_at = now + SESSION_TTL
    db.add(
        UserSession(
            id=new_id(),
            user_id=user.id,
            token_hash=hash_secret(raw_token),
            expires_at=session_expires_at,
        )
    )
    db.commit()
    return raw_token, user.id, session_expires_at


def resolve_session_user_id(db: Session, raw_token: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_secret(raw_token))
    ).scalar_one_or_none()
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise SessionInvalidError()
    return session.user_id


def set_pin(db: Session, user_id: str, otp_code: str, pin: str) -> None:
    """승인 본인확인 PIN 등록/변경(§13-12). 원문은 저장하지 않는다 — hash_secret(HMAC pepper)만.

    세션만으로는 등록/변경할 수 없다 — 방금 발급받은 OTP로 전화 소지를 재확인해야 한다
    (코드 리뷰 지적 P1-2: 세션 탈취자가 재확인 없이 PIN을 덮어써 본인확인 게이트 전체를
    우회하는 경로를 막는다). phone은 클라이언트 입력이 아니라 세션 사용자 자신의 것만
    쓴다 — 남의 전화번호로 받은 OTP를 대신 제출할 수 없다.
    """
    user = db.get(User, user_id)
    _consume_otp(db, user.phone, otp_code)
    user.pin_hash = hash_secret(pin)
    db.commit()


def revoke_session(db: Session, raw_token: str) -> None:
    """로그아웃 — 세션을 폐기한다(어드버서리얼 보안 리뷰: 30일 TTL 토큰을 즉시 무효화할 수단이
    없다는 지적, F1/High). 이미 없거나 이미 폐기된 토큰은 조용히 무시한다(로그아웃은 멱등)."""
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_secret(raw_token))
    ).scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
