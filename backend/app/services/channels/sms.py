"""SmsAdapter — Solapi(https://solapi.com) v4 메시지 발송 API. MESSAGING_CHANNELS.md §5 stage ②.

자격 증명(`SOLAPI_API_KEY`/`SOLAPI_API_SECRET`/`SOLAPI_SENDER`)이 전부 설정된 경우에만 실
HTTP 호출을 만든다 — 하나라도 비어 있으면(이 dev 환경 기본값) `httpx.AsyncClient`를 아예
생성하지 않고 스텁 결과를 반환한다(backend/app/api/v1/auth.py의
`debug_code=code if get_settings().is_local else None`과 동일한 자격 증명 게이팅 원칙).

실 발송 경로는 Solapi HMAC-SHA256 서명 인증 계약(date+salt+signature)을 따른다 — 이 저장소에
Solapi 실계정이 없어 실제 계정으로 검증된 적은 없다(구조적으로 불가능하다: 자격 증명 자체가
없다). httpx 요청 형태는 공개된 v4 계약을 따라 작성했고, 테스트는 respx로만 한다
(backend/app/services/rag_client.py의 기존 httpx 클라이언트 관례를 그대로 따름).
"""

from __future__ import annotations

import datetime as dt
import uuid

import httpx

from app.config import get_settings
from app.services.channels._solapi import SOLAPI_BASE_URL, SOLAPI_SEND_PATH, solapi_signature
from app.services.channels.base import AdapterResult, new_stub_id


class SmsAdapter:
    channel = "sms"

    async def send(self, *, to: str, body: str, lang: str | None = None) -> AdapterResult:
        settings = get_settings()
        api_key = settings.solapi_api_key
        api_secret = settings.solapi_api_secret
        sender = settings.solapi_sender
        if not api_key or not api_secret or not sender:
            return AdapterResult(
                status="sent",
                external_id=new_stub_id(self.channel),
                detail="SOLAPI credentials unset — stub delivery, no external HTTP call made",
            )

        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        salt = uuid.uuid4().hex
        signature = solapi_signature(api_secret, date, salt)
        headers = {
            "Authorization": f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}",
            "Content-Type": "application/json",
        }
        payload = {"message": {"to": to, "from": sender, "text": body}}

        async with httpx.AsyncClient(base_url=SOLAPI_BASE_URL, timeout=10.0) as client:
            try:
                response = await client.post(SOLAPI_SEND_PATH, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                return AdapterResult(status="failed", external_id=None, detail=f"SOLAPI unreachable: {exc}")

        if response.status_code >= 400:
            return AdapterResult(
                status="failed", external_id=None, detail=f"SOLAPI {response.status_code}: {response.text[:200]}"
            )
        data = response.json()
        external_id = str(data.get("messageId") or data.get("groupId") or uuid.uuid4())
        return AdapterResult(status="sent", external_id=external_id)
