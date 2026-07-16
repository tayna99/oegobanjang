from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    """POST /approvals/{id}/approve|reject 공통 바디.

    idempotency_key는 클라이언트가 이 결정 시도마다 새로 발급한다(재시도 시 재사용해
    멱등 replay를 유도) — docs/DB_SCHEMA.md §5.3-2. 결정자 신원(decided_by_user_id)은
    더 이상 바디로 받지 않는다 — 인증된 세션에서 도출한다(§13-11).
    """

    idempotency_key: str = Field(min_length=1)
    on_behalf_of_user_id: str | None = None  # 대리 승인 시 위임자(7단계 §5)
    identity_method: Literal["pin", "biometric"] | None = None  # approve일 때 필수(§5.3-6)
    reason: str | None = None  # reject일 때 필수(§5.3-8)


class ApprovalRequestCreate(BaseModel):
    """POST /approvals — 승인 요청 생성 바디."""

    action_id: str = Field(min_length=1)


class ApprovalOut(BaseModel):
    id: str
    company_id: str
    case_id: str
    action_id: str
    status: str
    idempotency_key: str | None
    reason: str | None
    requested_at: dt.datetime
    decided_at: dt.datetime | None
    decided_by_user_id: str | None

    model_config = {"from_attributes": True}


class ApprovalDecisionResponse(BaseModel):
    approval: ApprovalOut
    case_state: str
