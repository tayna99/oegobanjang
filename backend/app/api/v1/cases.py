"""GET /api/v1/cases — 케이스 목록 읽기 모델 v1 + 기준일 주입(§6, §13-14).

docs/DB_SCHEMA.md:727 "기준일은 요청 시각(회사 timezone) 또는 브리핑 날짜 주입" 공식을
서비스 계층에서 처음 소비하는 엔드포인트다. v_case_derived 뷰는 CURRENT_DATE 고정이라
기준일 주입과 맞지 않아 여기서는 쓰지 않는다(뷰는 DBeaver 조회 편의용으로 남김).
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.case import Case
from app.models.company import Company
from app.models.membership import Membership
from app.models.worker import Worker
from app.schemas.case import CaseListItemOut, CaseListOut

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def _resolve_base_date(company: Company, base_date: dt.date | None) -> dt.date:
    if base_date is not None:
        return base_date
    return dt.datetime.now(ZoneInfo(company.timezone)).date()


@router.get("", response_model=CaseListOut)
def list_cases(
    base_date: dt.date | None = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> CaseListOut:
    company = db.get(Company, membership.company_id)
    base = _resolve_base_date(company, base_date)

    rows = db.execute(
        select(Case, Worker)
        .join(Worker, Worker.id == Case.worker_id, isouter=True)
        .where(Case.company_id == membership.company_id)
        .order_by(Case.due_date.is_(None), Case.due_date, Case.case_code)
    ).all()

    items = [
        CaseListItemOut(
            id=case.id,
            case_code=case.case_code,
            title=case.title,
            case_type=case.case_type,
            severity=case.severity,
            state=case.state,
            agent_stage=case.agent_stage,
            due_date=case.due_date,
            d_day=(case.due_date - base).days if case.due_date is not None else None,
            approval_required=case.approval_required,
            worker_display_name=worker.display_name if worker is not None else None,
            worker_nationality=worker.nationality if worker is not None else None,
            stay_expires_at=worker.stay_expires_at if worker is not None else None,
        )
        for case, worker in rows
    ]
    return CaseListOut(cases=items, base_date=base)
