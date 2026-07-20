from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class NotificationOut(BaseModel):
    """GET /api/v1/notifications, POST .../read 공통 응답 — snake_case(기존 스키마 관례)."""

    id: str
    type: str
    priority: str
    title: str
    body: str
    deeplink_path: str
    channel: str
    status: str
    case_id: str | None
    run_id: str | None
    created_at: dt.datetime
    read_at: dt.datetime | None

    model_config = {"from_attributes": True}
