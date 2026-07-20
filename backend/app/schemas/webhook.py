from __future__ import annotations

from pydantic import BaseModel, Field


class ZaloWebhookPayload(BaseModel):
    thread_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    external_message_id: str | None = None
