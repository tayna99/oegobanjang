"""OTP 코드·세션 토큰 생성/해시. 원문은 저장하지 않는다(§13-11, users.pin_hash와 동일 원칙).

HMAC-SHA256(pepper, secret)을 쓴다 — 6자리 OTP는 저엔트로피라 pepper 없는 단순 해시로는
탈취된 code_hash 테이블에서 오프라인 무차별 대입이 밀리초 단위로 끝난다. pepper가 없으면
방어 의미가 없다. 32바이트 세션 토큰은 고엔트로피라 pepper 없이도 안전하지만 동일 함수로
일관되게 처리한다. bcrypt/argon2 같은 느린 해시는 쓰지 않는다 — 여기서 지연시키려는 것은
비밀번호가 아니라 짧은 검증 루프(OTP 검증)이며, pepper가 실제 방어선이다.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import get_settings


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    pepper = get_settings().auth_pepper.encode()
    return hmac.new(pepper, secret.encode(), hashlib.sha256).hexdigest()


def secrets_match(secret: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), hashed)
