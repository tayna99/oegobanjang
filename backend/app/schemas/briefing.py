from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class BriefingGenerateRequest(BaseModel):
    company_id: str = Field(min_length=1)
    reference_date: str | None = None  # ISO 날짜. 생략 시 오늘(context_service 기본값)


class BriefingItemOut(BaseModel):
    case_id: str
    case_code: str
    rank: int
    risk_type: str
    severity: str
    title: str

    model_config = {"from_attributes": True}


class BriefingOut(BaseModel):
    id: str
    company_id: str
    briefing_date: dt.date
    generated_at: dt.datetime
    rerun_count: int
    items: list[BriefingItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
