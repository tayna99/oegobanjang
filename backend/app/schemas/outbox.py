from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class OutboxDispatchRequest(BaseModel):
    """POST /outbox — "실행 확인"(§1 각주²) 바디. 기본값은 최초 발송(dispatch) — reminder/resend는
    threshold(임계값)로 idempotency 단위를 구분한다(§2 "같은 case+event_type+임계값은 1회만")."""

    action_id: str = Field(min_length=1)
    event_type: Literal["dispatch", "reminder", "resend"] = "dispatch"
    threshold: str | None = None


class OutboxOut(BaseModel):
    id: str
    company_id: str
    case_id: str
    action_id: str
    approval_id: str
    thread_id: str | None
    channel: str
    event_type: str
    status: str
    external_id: str | None
    attempt_count: int
    fallback_from_id: str | None
    scheduled_for: dt.datetime | None
    sent_at: dt.datetime | None
    failed_reason: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
