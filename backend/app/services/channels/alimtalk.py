"""AlimtalkAdapter — 카카오 알림톡. MESSAGING_CHANNELS.md §5 stage ③.

알림톡은 SMS와 같은 발송사(Solapi)의 같은 엔드포인트(`/messages/v4/send`)를 `type: 'ATA'`로
호출하는 계약을 쓴다 — 단, 알림톡은 SMS 자격 증명만으로는 부족하다. 사전 심사된 발신
프로필(`KAKAO_ALIMTALK_SENDER_KEY`)과 템플릿 코드(`KAKAO_ALIMTALK_TEMPLATE_CODE`)가 별도로
필요하다(카카오 비즈메시지의 구조적 제약 — 임의 문구를 알림톡으로 보낼 수 없다). 이 셋 중
하나라도 없으면 스텁 처리한다(SmsAdapter와 동일 게이팅 원칙, backend/app/api/v1/auth.py 참조).

실패 시 SMS로 전환하는 로직("채널 중복 금지" — fallback만, 중복 발송 아님)은 이 어댑터의
책임이 아니다 — services/outbox.py가 이 어댑터의 `status='failed'` 결과를 보고 오케스트레이션한다.
"""

from __future__ import annotations

import datetime as dt
import uuid

import httpx

from app.config import get_settings
from app.services.channels._solapi import SOLAPI_BASE_URL, SOLAPI_SEND_PATH, solapi_signature
from app.services.channels.base import AdapterResult, new_stub_id


class AlimtalkAdapter:
    channel = "alimtalk"

    async def send(self, *, to: str, body: str, lang: str | None = None) -> AdapterResult:
        settings = get_settings()
        api_key = settings.solapi_api_key
        api_secret = settings.solapi_api_secret
        sender = settings.solapi_sender
        sender_key = settings.kakao_alimtalk_sender_key
        template_code = settings.kakao_alimtalk_template_code
        if not api_key or not api_secret or not sender or not sender_key or not template_code:
            return AdapterResult(
                status="sent",
                external_id=new_stub_id(self.channel),
                detail="Alimtalk credentials/template unset — stub delivery, no external HTTP call made",
            )

        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        salt = uuid.uuid4().hex
        signature = solapi_signature(api_secret, date, salt)
        headers = {
            "Authorization": f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}",
            "Content-Type": "application/json",
        }
        payload = {
            "message": {
                "to": to,
                "from": sender,
                "text": body,
                "type": "ATA",
                "kakaoOptions": {"pfId": sender_key, "templateId": template_code},
            }
        }

        async with httpx.AsyncClient(base_url=SOLAPI_BASE_URL, timeout=10.0) as client:
            try:
                response = await client.post(SOLAPI_SEND_PATH, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                return AdapterResult(status="failed", external_id=None, detail=f"Alimtalk unreachable: {exc}")

        if response.status_code >= 400:
            return AdapterResult(
                status="failed", external_id=None, detail=f"Alimtalk {response.status_code}: {response.text[:200]}"
            )
        data = response.json()
        external_id = str(data.get("messageId") or data.get("groupId") or uuid.uuid4())
        return AdapterResult(status="sent", external_id=external_id)
