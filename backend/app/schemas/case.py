from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class CaseListItemOut(BaseModel):
    """GET /cases 읽기 모델 v1 — CaseCard 전체가 아니라 목록 화면 최소 계약(§8, §13-14).

    d_day는 서비스 계층에서 기준일 주입으로 계산한다(§6) — v_case_derived는 CURRENT_DATE
    고정이라 여기서는 쓰지 않는다.
    """

    id: str
    case_code: str
    title: str
    case_type: str
    severity: str
    state: str
    agent_stage: str | None
    due_date: dt.date | None
    d_day: int | None
    approval_required: bool
    worker_display_name: str | None
    worker_nationality: str | None
    stay_expires_at: dt.date | None

    model_config = {"from_attributes": True}


class CaseListOut(BaseModel):
    cases: list[CaseListItemOut]
    base_date: dt.date
