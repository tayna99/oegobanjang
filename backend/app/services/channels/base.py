"""ChannelAdapter 공용 계약 — MESSAGING_CHANNELS.md §2 의사코드의 실구현.

핵심 규칙(모든 어댑터 공통, GOTCHAS §1 "직접 발송 함수 금지"의 실연동 버전):
자격 증명이 하나라도 비어 있으면(이 dev 환경·CI·리뷰어 환경 전부 해당) 어댑터는 실 채널사로
어떤 HTTP 요청도 만들지 않는다 — `httpx.AsyncClient`를 아예 생성하지 않는다. 대신
`external_id`에 `stub:` 접두 값을 붙여 "성공처럼 보이지만 실제로는 아무것도 나가지 않았다"를
DB에서 항상 구분 가능하게 남긴다(실 발송의 `external_id`는 채널사가 발급한 값이라 이 접두를
쓸 수 없다 — 접두 충돌 가능성은 구조적으로 없다).
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import Literal, Protocol

AdapterStatus = Literal["sent", "failed"]

STUB_PREFIX = "stub:"


@dataclasses.dataclass(frozen=True)
class AdapterResult:
    """어댑터 1회 호출의 결과. `is_stub`은 `external_id`의 `stub:` 접두에서 파생되므로
    별도 필드로 이중 저장하지 않는다 — 호출부는 `result.is_stub` 프로퍼티를 쓴다."""

    status: AdapterStatus
    external_id: str | None  # 'sent'면 항상 not-None(실 ID 또는 stub:...). 'failed'면 보통 None
    detail: str | None = None  # 실패 사유 또는 스텁 사유(로그·failed_reason용 — PII 없는 운영 문구만)

    @property
    def is_stub(self) -> bool:
        return self.external_id is not None and self.external_id.startswith(STUB_PREFIX)


def new_stub_id(channel: str) -> str:
    return f"{STUB_PREFIX}{channel}:{uuid.uuid4()}"


class ChannelAdapter(Protocol):
    """MESSAGING_CHANNELS.md §2 의사코드:
    `interface ChannelAdapter { channel: Channel; send(msg): Promise<{externalId?, deliveryStatus}> }`
    을 그대로 옮긴 백엔드 계약. `to`는 채널별 수신처 식별자(전화번호/Zalo 사용자ID/이메일) —
    이 스키마엔 근로자 연락처 원문 컬럼이 없으므로(§7 PII 최소화) 호출부가 매 호출마다
    최선의 표시용 식별자를 만들어 전달한다(services/outbox.py 참조)."""

    channel: str

    async def send(self, *, to: str, body: str, lang: str | None = None) -> AdapterResult: ...
