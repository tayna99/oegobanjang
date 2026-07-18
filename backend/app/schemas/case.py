"""cases 도메인 응답 스키마 — GET /api/v1/cases(R2.3). docs/DB_SCHEMA.md §4.3.

due_date는 date 그대로 노출한다 — dDay 계산은 프론트가 한다(cases 테이블 DDL 주석
"dDay는 저장하지 않음"과 동일 철학, §6). 서버는 날짜 계산을 하지 않는다.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class WorkerRefOut(BaseModel):
    display_name: str
    nationality: str
    team: str | None

    model_config = {"from_attributes": True}


class NextActionOut(BaseModel):
    """next_actions 1건의 최소 노출 필드. action_id는 next_actions.id의 별칭 —
    서비스 조립 함수(app.services.cases.get_case_out)가 채워 넣는다."""

    action_id: str
    label: str
    state: str
    requires_approval: bool
    kind: str


class CaseOut(BaseModel):
    id: str
    case_code: str
    title: str
    severity: str
    state: str
    agent_stage: str | None
    due_date: dt.date | None
    approval_required: bool
    prepared_by: str
    prepared_run_id: str | None
    worker: WorkerRefOut | None
    primary_action: NextActionOut | None
    secondary_action: NextActionOut | None


class ApprovalChecklistItemOut(BaseModel):
    key: str
    label: str
    checked: bool


class PendingApprovalOut(BaseModel):
    """이 케이스의 살아있는(pending) 승인 요청 — R2.4. 없으면 GET /cases/{id}가 null로 내린다."""

    id: str
    action_id: str
    checklist: list[ApprovalChecklistItemOut] | None
    requested_at: dt.datetime


class CaseDetailOut(CaseOut):
    """GET /api/v1/cases/{case_id} 전용 — 목록(CaseOut)에 승인 화면(ApprovePage)이 필요로
    하는 필드를 얹는다(R2.4). usable_citation_count는 services.approvals.usable_citation_count와
    동일 로직(F등급 제외 + 전역/자사 스코프)."""

    usable_citation_count: int
    guard_note: str | None
    pending_approval: PendingApprovalOut | None
