"""ZaloAdapter — Zalo OA(공식 계정) 고객센터 메시지 발송. MESSAGING_CHANNELS.md §5 stage ④.

`ZALO_OA_ACCESS_TOKEN`이 없으면(이 dev 환경 기본값) httpx 호출을 만들지 않고 스텁 처리한다
(SmsAdapter/AlimtalkAdapter와 동일 원칙). 실 발송 경로는 Zalo OA 공개 API 계약
(`POST https://openapi.zalo.me/v3.0/oa/message/cs`, 헤더 `access_token`)을 따라 작성했다 —
이 저장소에 Zalo OA 실계정이 없어 실계정으로 검증된 적은 없다.

인바운드(webhook)는 이 파일이 아니라 `app/services/webhooks.py`(ZaloAdapter가 다루는 것은
발신뿐 — MESSAGING_CHANNELS.md §3 "발신과 수신은 다른 문제다").
"""

from __future__ import annotations

import uuid

import httpx

from app.config import get_settings
from app.services.channels.base import AdapterResult, new_stub_id

ZALO_BASE_URL = "https://openapi.zalo.me"
ZALO_SEND_PATH = "/v3.0/oa/message/cs"


class ZaloAdapter:
    channel = "zalo"

    async def send(self, *, to: str, body: str, lang: str | None = None) -> AdapterResult:
        settings = get_settings()
        access_token = settings.zalo_oa_access_token
        if not access_token:
            return AdapterResult(
                status="sent",
                external_id=new_stub_id(self.channel),
                detail="ZALO_OA_ACCESS_TOKEN unset — stub delivery, no external HTTP call made",
            )

        headers = {"access_token": access_token, "Content-Type": "application/json"}
        payload = {"recipient": {"user_id": to}, "message": {"text": body}}

        async with httpx.AsyncClient(base_url=ZALO_BASE_URL, timeout=10.0) as client:
            try:
                response = await client.post(ZALO_SEND_PATH, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                return AdapterResult(status="failed", external_id=None, detail=f"Zalo OA unreachable: {exc}")

        if response.status_code >= 400:
            return AdapterResult(
                status="failed", external_id=None, detail=f"Zalo OA {response.status_code}: {response.text[:200]}"
            )
        data = response.json()
        # Zalo OA는 성공 시에도 error=0 봉투에 담아 200을 준다 — data.error가 0이 아니면 논리적 실패.
        if isinstance(data, dict) and data.get("error", 0) != 0:
            return AdapterResult(status="failed", external_id=None, detail=f"Zalo OA error: {data.get('message')}")
        external_id = str((data or {}).get("data", {}).get("message_id") or uuid.uuid4())
        return AdapterResult(status="sent", external_id=external_id)
