"""EmailAdapter — 행정사 패키지 전달 전용. MESSAGING_CHANNELS.md §2 "행정사 패키지 어댑터는
근로자 채널 어댑터 4종(Mock/Sms/Alimtalk/Zalo)과 분리한다."

근로자에게는 이메일 채널을 열지 않는다(§1 원칙) — 이 어댑터는 outbox(발송 대기열, sms/
alimtalk/zalo 전용)를 거치지 않고, 행정사 패키지 링크 발급 흐름(services/packages.py)에서
직접 호출되는 별도 경로다. `SMTP_HOST`/`SMTP_USER`/`SMTP_PASS`/`SMTP_FROM`이 전부 설정된
경우에만 실제로 SMTP 연결을 만든다 — 하나라도 비면(이 dev 환경 기본값) 스텁으로 처리하고
서버 연결을 시도하지 않는다(다른 어댑터와 동일한 자격 증명 게이팅 원칙).

SMTP는 `httpx` 기반이 아니라 표준 라이브러리 `smtplib`(동기)를 쓴다 — 이벤트 루프를 막지
않도록 `asyncio.to_thread`로 감싼다.
"""

from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.message import EmailMessage

from app.config import get_settings
from app.services.channels.base import AdapterResult, new_stub_id


def _send_sync(*, host: str, port: int, user: str, password: str, from_addr: str, to: str, subject: str, body: str) -> str:
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
    return str(message["Message-Id"] or uuid.uuid4())


class EmailAdapter:
    channel = "email"

    async def send(self, *, to: str, body: str, lang: str | None = None, subject: str = "외고반장 행정사 패키지 안내") -> AdapterResult:
        settings = get_settings()
        host, user, password, from_addr = (
            settings.smtp_host,
            settings.smtp_user,
            settings.smtp_pass,
            settings.smtp_from,
        )
        if not host or not user or not password or not from_addr:
            return AdapterResult(
                status="sent",
                external_id=new_stub_id(self.channel),
                detail="SMTP credentials unset — stub delivery, no SMTP connection made",
            )

        try:
            external_id = await asyncio.to_thread(
                _send_sync,
                host=host,
                port=settings.smtp_port,
                user=user,
                password=password,
                from_addr=from_addr,
                to=to,
                subject=subject,
                body=body,
            )
        except (smtplib.SMTPException, OSError) as exc:
            return AdapterResult(status="failed", external_id=None, detail=f"SMTP send failed: {exc}")
        return AdapterResult(status="sent", external_id=external_id)
