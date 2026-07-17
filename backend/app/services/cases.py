"""cases 도메인 읽기 서비스 — GET /api/v1/cases(R2.3). docs/DB_SCHEMA.md §4.3.

get_case_out은 다른 도메인(예: briefings)이 그대로 재사용할 수 있도록 이름·시그니처를
유지한다 — 변경 시 호출부가 깨진다.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case, NextAction
from app.models.worker import Worker
from app.schemas.case import CaseOut, NextActionOut, WorkerRefOut

# 목록 정렬 기준: 심각도(높을수록 먼저) → 마감일(빠를수록 먼저) → 생성순.
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _next_action_out(next_action: NextAction | None) -> NextActionOut | None:
    if next_action is None:
        return None
    return NextActionOut(
        action_id=next_action.id,
        label=next_action.label,
        state=next_action.state,
        requires_approval=next_action.requires_approval,
        kind=next_action.kind,
    )


def get_case_out(db: Session, company_id: str, case: Case) -> CaseOut:
    """이미 로드된 Case ORM 객체 1건을 worker + primary/secondary next_action과 조립한다.

    worker는 case.worker_id(있는 경우)로, next_action은 slot='primary'/'secondary'로
    각 1건 조회한다 — 둘 다 company_id로 스코프한다.
    """
    worker = None
    if case.worker_id is not None:
        worker = db.execute(
            select(Worker).where(Worker.company_id == company_id, Worker.id == case.worker_id)
        ).scalar_one_or_none()

    primary = db.execute(
        select(NextAction).where(
            NextAction.company_id == company_id,
            NextAction.case_id == case.id,
            NextAction.slot == "primary",
        )
    ).scalar_one_or_none()
    secondary = db.execute(
        select(NextAction).where(
            NextAction.company_id == company_id,
            NextAction.case_id == case.id,
            NextAction.slot == "secondary",
        )
    ).scalar_one_or_none()

    return CaseOut(
        id=case.id,
        case_code=case.case_code,
        title=case.title,
        severity=case.severity,
        state=case.state,
        agent_stage=case.agent_stage,
        due_date=case.due_date,
        approval_required=case.approval_required,
        prepared_by=case.prepared_by,
        prepared_run_id=case.prepared_run_id,
        worker=WorkerRefOut.model_validate(worker) if worker is not None else None,
        primary_action=_next_action_out(primary),
        secondary_action=_next_action_out(secondary),
    )


def list_cases_out(db: Session, company_id: str) -> list[CaseOut]:
    """company_id로 스코프된 전체 케이스를 심각도·마감일 순으로 조립해 반환한다."""
    cases = db.execute(select(Case).where(Case.company_id == company_id)).scalars().all()
    cases_sorted = sorted(
        cases,
        key=lambda c: (_SEVERITY_ORDER.get(c.severity, 99), c.due_date or dt.date.max, c.created_at),
    )
    return [get_case_out(db, company_id, case) for case in cases_sorted]
