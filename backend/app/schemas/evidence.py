from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class EvidenceEventCreate(BaseModel):
    """POST /api/v1/evidence 바디 — 일반 판단 기록 기록.

    action_id/approval_id/run_id는 받지 않는다: DB 트리거(trg_evidence_context_match)가
    "제공되면 같은 케이스 소속 행이 실제로 존재해야 함"을 강제하는데, 이 엔드포인트를 쓰는
    화면(RBAC·해석 확인·발송 실행 등)은 아직 그 참조 도메인(승인 결정·런)이 백엔드에
    배선되지 않아 실제 행을 보장할 수 없다(docs/DB_SCHEMA.md §4.5 R2.5 노트) — case_id만 받는다.
    actor(누가)는 세션에서 도출한다(요청 바디로 신뢰하지 않음, approvals.py와 동일 원칙).
    """

    type: str = Field(min_length=1)
    case_id: str | None = None
    summary: str = Field(min_length=1)
    input_hash: str | None = None
    output_hash: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    payload_ref: str | None = None


class EvidenceEventOut(BaseModel):
    id: str
    company_id: str
    event_no: int
    type: str
    at: dt.datetime
    case_id: str | None
    action_id: str | None
    approval_id: str | None
    run_id: str | None
    actor_type: str
    actor_user_id: str | None
    actor_display: str | None
    summary: str
    input_hash: str | None
    output_hash: str | None
    trace_id: str | None
    request_id: str | None
    payload_ref: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
