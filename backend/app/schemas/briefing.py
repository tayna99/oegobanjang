"""briefings 도메인 응답 스키마 — docs/DB_SCHEMA.md §4.9.

GET /api/v1/briefings/latest(R2.3): 최신 브리핑을 케이스와 함께 조립해 반환한다 — 케이스
조립 로직은 재사용(CaseOut을 다시 정의하지 않고 그대로 import, app.services.briefings가
채워 넣는다).
POST /api/v1/briefings/generate(G6): Risk Rule Engine 룰-only 생성 결과를 반환한다 — 두
엔드포인트가 같은 이름 BriefingOut을 두고 충돌해 생성 쪽을 BriefingGenerateOut으로 구분한다.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.schemas.case import CaseOut


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


class BriefingGenerateOut(BaseModel):
    id: str
    company_id: str
    briefing_date: dt.date
    generated_at: dt.datetime
    rerun_count: int
    items: list[BriefingItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BriefingOut(BaseModel):
    id: str
    briefing_date: dt.date
    generated_at: dt.datetime
    cases: list[CaseOut]
