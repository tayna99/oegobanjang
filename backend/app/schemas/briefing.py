"""briefings 도메인 응답 스키마 — GET /api/v1/briefings/latest(R2.3). docs/DB_SCHEMA.md §4.9.

cases 조립 로직은 재사용한다 — CaseOut을 다시 정의하지 않고 그대로 import한다
(app.services.briefings.get_latest_briefing_out이 채워 넣는다).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from app.schemas.case import CaseOut


class BriefingOut(BaseModel):
    id: str
    briefing_date: dt.date
    generated_at: dt.datetime
    cases: list[CaseOut]
