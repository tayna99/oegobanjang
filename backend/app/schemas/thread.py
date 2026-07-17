"""GET /api/v1/threads · GET /api/v1/threads/{thread_id} 응답 스키마.

cases 도메인의 WorkerRefOut과는 별개로 ThreadWorkerOut을 이 파일 안에 따로 둔다 — 작은
중복은 의도적으로 허용한다(도메인 간 결합을 피하기 위해, plans/NEXT_ROADMAP_2026-07-16.md §R2.3).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class ThreadWorkerOut(BaseModel):
    display_name: str
    nationality: str
    team: str | None

    model_config = {"from_attributes": True}


class InterpretationOut(BaseModel):
    id: str
    summary_ko: str
    confidence: str
    status: str
    confirmed_at: dt.datetime | None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    direction: str
    channel: str
    lang: str | None
    body_original: str | None
    body_ko: str | None
    received_at: dt.datetime | None
    created_at: dt.datetime
    interpretation: InterpretationOut | None


class ThreadOut(BaseModel):
    """목록용 — 가벼운 요약(메시지 전체를 싣지 않는다)."""

    id: str
    worker: ThreadWorkerOut | None
    channel: str
    last_message_at: dt.datetime | None
    message_count: int


class ThreadDetailOut(BaseModel):
    """상세용 — 메시지 전체 + 각 메시지의 interpretation."""

    id: str
    worker: ThreadWorkerOut | None
    channel: str
    messages: list[MessageOut]
