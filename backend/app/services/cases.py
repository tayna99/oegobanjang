"""cases 도메인 읽기 서비스 — GET /api/v1/cases(R2.3). docs/DB_SCHEMA.md §4.3.

get_case_out은 다른 도메인(예: briefings)이 그대로 재사용할 수 있도록 이름·시그니처를
유지한다 — 변경 시 호출부가 깨진다.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approval import Approval
from app.models.case import Case, NextAction
from app.models.document import WorkerDocument
from app.models.worker import Worker
from app.schemas.case import (
    ApprovalChecklistItemOut,
    CaseDetailOut,
    CaseOut,
    CheckedItemOut,
    NextActionOut,
    PendingApprovalOut,
    WorkerDocumentOut,
    WorkerRefOut,
)
from app.services.approvals import usable_citation_count

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


def _pending_approval_out(approval: Approval | None) -> PendingApprovalOut | None:
    if approval is None:
        return None
    checklist = None
    if approval.checklist is not None and isinstance(approval.checklist, list):
        checklist = [ApprovalChecklistItemOut(**item) for item in approval.checklist]
    return PendingApprovalOut(
        id=approval.id, action_id=approval.action_id, checklist=checklist, requested_at=approval.requested_at
    )


def _checked_items_out(checked_items: object) -> list[CheckedItemOut]:
    if not isinstance(checked_items, list):
        return []
    return [CheckedItemOut(**item) for item in checked_items]


def _worker_documents_out(db: Session, company_id: str, worker_id: str | None) -> list[WorkerDocumentOut]:
    """worker_id가 없는 케이스(예: 커맨드 런 기원)는 워커 엔티티가 없으므로 빈 배열 —
    SD-6, mock CaseSheet.docs와 동일 개념."""
    if worker_id is None:
        return []
    documents = (
        db.execute(
            select(WorkerDocument)
            .where(WorkerDocument.company_id == company_id, WorkerDocument.worker_id == worker_id)
            .order_by(WorkerDocument.created_at, WorkerDocument.id)
        )
        .scalars()
        .all()
    )
    return [
        WorkerDocumentOut(doc_type=d.doc_type, status=d.status, due_date=d.due_date, expires_at=d.expires_at)
        for d in documents
    ]


def get_case_detail_out(db: Session, company_id: str, case: Case) -> CaseDetailOut:
    """GET /api/v1/cases/{case_id} 전용 조립 — get_case_out(목록용) 위에 승인 화면·케이스
    시트 화면(SD-6)이 필요로 하는 필드를 얹는다(R2.4 Blocker A+B 해소: 프론트가 mock
    CASE_SHEETS 대신 이 응답으로 체크리스트·근거수·가드노트·pending approval_id를 얻는다.
    SD-6은 여기에 checked_items·next_wake(컬럼 그대로 노출)·worker_documents를 더한다)."""
    base = get_case_out(db, company_id, case)
    pending = db.execute(
        select(Approval).where(
            Approval.company_id == company_id, Approval.case_id == case.id, Approval.status == "pending"
        )
    ).scalar_one_or_none()
    return CaseDetailOut(
        **base.model_dump(),
        usable_citation_count=usable_citation_count(db, company_id, case.id),
        guard_note=case.guard_note,
        pending_approval=_pending_approval_out(pending),
        checked_items=_checked_items_out(case.checked_items),
        next_wake=case.next_wake_condition,
        documents=_worker_documents_out(db, company_id, case.worker_id),
    )


def list_cases_out(db: Session, company_id: str) -> list[CaseOut]:
    """company_id로 스코프된 전체 케이스를 심각도·마감일 순으로 조립해 반환한다."""
    cases = db.execute(select(Case).where(Case.company_id == company_id)).scalars().all()
    cases_sorted = sorted(
        cases,
        key=lambda c: (_SEVERITY_ORDER.get(c.severity, 99), c.due_date or dt.date.max, c.created_at),
    )
    return [get_case_out(db, company_id, case) for case in cases_sorted]
