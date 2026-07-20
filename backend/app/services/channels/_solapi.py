"""Solapi HMAC-SHA256 서명 계약 — sms.py·alimtalk.py 공유(둘 다 같은 발송사·같은 엔드포인트).

내부 전용 모듈(밑줄 접두) — 어댑터 계약(ChannelAdapter)이 아니라 두 실 발송 구현이 공유하는
서명 로직만 담는다.
"""

from __future__ import annotations

import hashlib
import hmac

SOLAPI_BASE_URL = "https://api.solapi.com"
SOLAPI_SEND_PATH = "/messages/v4/send"


def solapi_signature(api_secret: str, date: str, salt: str) -> str:
    return hmac.new(api_secret.encode(), f"{date}{salt}".encode(), hashlib.sha256).hexdigest()
