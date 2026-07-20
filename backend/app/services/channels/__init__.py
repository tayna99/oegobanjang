"""ChannelAdapter 5종 — MESSAGING_CHANNELS.md §2.

`WORKER_CHANNEL_ADAPTERS`는 outbox(발송 대기열)가 다루는 근로자 채널 3종만 담는다 —
`EmailAdapter`는 근로자 채널이 아니라 행정사 패키지 전달 전용이라 이 레지스트리에 없다
(services/packages.py가 필요 시 직접 import한다).
"""

from __future__ import annotations

from app.services.channels.alimtalk import AlimtalkAdapter
from app.services.channels.base import AdapterResult, ChannelAdapter
from app.services.channels.email import EmailAdapter
from app.services.channels.sms import SmsAdapter
from app.services.channels.zalo import ZaloAdapter

WORKER_CHANNEL_ADAPTERS: dict[str, ChannelAdapter] = {
    "sms": SmsAdapter(),
    "alimtalk": AlimtalkAdapter(),
    "zalo": ZaloAdapter(),
}

__all__ = [
    "AdapterResult",
    "ChannelAdapter",
    "AlimtalkAdapter",
    "EmailAdapter",
    "SmsAdapter",
    "ZaloAdapter",
    "WORKER_CHANNEL_ADAPTERS",
]
