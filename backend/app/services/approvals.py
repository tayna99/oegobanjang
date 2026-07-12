"""승인 결정 서비스 — docs/DB_SCHEMA.md §5.3 승인 게이트 불변식을 강제한다.

상태 전이 + evidence append는 같은 트랜잭션(§0-4, 레거시 PRD Transaction rule 승계) —
이 함수 안에서 커밋 하나로 묶는다. 실패하면 아무 것도 반영되지 않는다.

SQLite 동시성 주의: 이 MVP 단계는 SQLite의 파일 수준 쓰기 직렬화에 기댄다(진짜
`SELECT ... FOR UPDATE` 행 잠금은 없음) — PostgreSQL 전환 시(docs/DB_SCHEMA.md §1)
이 함수에 `with_for_update()`를 추가해야 한다.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.case_transitions import can_transition
from app.domain.exceptions import (
    ApprovalAlreadyDecidedError,
    ApprovalBlockedByEvidenceError,
    ApprovalChecklistIncompleteError,
    ApprovalForbiddenError,
    ApprovalIdempotencyKeyReusedError,
    ApprovalIdentityRequiredError,
    ApprovalNotFoundError,
    ApprovalReasonContainsPiiError,
    ApprovalReasonRequiredError,
    CaseTransitionError,
)
from app.domain.pii import contains_pii
from app.models.approval import Approval
from app.models.case import Case, NextAction
from app.models.citation import CaseCitation, Citation
from app.models.company import Company
from app.models.evidence import EvidenceEvent
from app.models.membership import Membership
from app.models.user import User
from app.schemas.approval import ApprovalDecisionRequest

APPROVER_ROLES = ("owner", "manager")


def _usable_citation_count(db: Session, case_id: str) -> int:
    return db.execute(
        select(func.count(CaseCitation.citation_id))
        .join(Citation, Citation.id == CaseCitation.citation_id)
        .where(CaseCitation.case_id == case_id, Citation.grade != "F")
    ).scalar_one()


def _next_event_no(db: Session, company_id: str) -> int:
    """companies.evidence_seq를 트랜잭션 내에서 원자적으로 증가시키고 새 값을 받는다(§9)."""
    company = db.get(Company, company_id)
    company.evidence_seq += 1
    db.flush()
    return company.evidence_seq


def decide_approval(
    db: Session,
    approval_id: str,
    decision: Literal["approved", "rejected"],
    payload: ApprovalDecisionRequest,
) -> tuple[Approval, str]:
    """승인/반려 처리. 반환값은 (갱신된 Approval, 갱신된 case.state)."""
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise ApprovalNotFoundError(approval_id)

    if approval.status != "pending":
        # 같은 idempotency_key로 재호출 — 멱등 replay(GOTCHAS §2, §5.3-2)
        if approval.idempotency_key is not None and approval.idempotency_key == payload.idempotency_key:
            case = db.get(Case, approval.case_id)
            return approval, case.state
        raise ApprovalAlreadyDecidedError(approval.status)

    case = db.get(Case, approval.case_id)
    next_action = db.get(NextAction, approval.action_id)

    membership = db.execute(
        select(Membership).where(
            Membership.company_id == approval.company_id,
            Membership.user_id == payload.decided_by_user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None or membership.role not in APPROVER_ROLES:
        raise ApprovalForbiddenError("승인 권한이 없습니다")

    if decision == "approved":
        # 결정자 권한 세분화: manager는 approval_policy='manager_allowed'이고
        # 케이스 severity가 LOW일 때만(§5.3-6, docs/DB_SCHEMA.md §13-4)
        if membership.role == "manager":
            company = db.get(Company, approval.company_id)
            if not (company.approval_policy == "manager_allowed" and case.severity == "LOW"):
                raise ApprovalForbiddenError("이 승인은 대표만 가능합니다")

        # high risk 케이스(기한 경과 등, state='blocked')는 handoff 계열 액션만 승인 가능(§5.3-7, GOTCHAS §1)
        if case.state == "blocked" and next_action.action_type != "create_handoff":
            raise ApprovalForbiddenError(
                "기한 경과 등 고위험 케이스는 행정사 전달 액션만 승인할 수 있습니다"
            )

        # citation-0 잠금: 사용 가능 근거(grade != 'F') 0건이면 승인 불가(§5.3-3, GOTCHAS §3)
        if _usable_citation_count(db, approval.case_id) < 1:
            raise ApprovalBlockedByEvidenceError()

        # M2.6 체크리스트: 값이 있으면(=화면이 제출했으면) 4항목 전부 checked여야 함(§5.3-5)
        if approval.checklist is not None:
            items = approval.checklist if isinstance(approval.checklist, list) else []
            if not items or not all(item.get("checked") for item in items):
                raise ApprovalChecklistIncompleteError()

        # 본인확인 수단 필수 — 세션만으로 승인 불가(§5.3-6, 7단계 §4)
        if payload.identity_method not in ("pin", "biometric"):
            raise ApprovalIdentityRequiredError()

        target_state = "human_approved"
    else:
        if not payload.reason:
            raise ApprovalReasonRequiredError()
        if contains_pii(payload.reason):
            raise ApprovalReasonContainsPiiError()
        target_state = "returned"

    if not can_transition(case.state, target_state):
        raise CaseTransitionError(case.state, target_state)

    now = dt.datetime.now(dt.timezone.utc)

    approval.status = decision
    approval.idempotency_key = payload.idempotency_key
    approval.decided_by_user_id = payload.decided_by_user_id
    approval.on_behalf_of_user_id = payload.on_behalf_of_user_id
    approval.identity_method = payload.identity_method
    approval.reason = payload.reason
    approval.decided_at = now

    case.state = target_state
    case.updated_at = now

    decider = db.get(User, payload.decided_by_user_id)
    actor_display = f"{decider.name} (본인)" if payload.on_behalf_of_user_id is None else f"{decider.name} (대리 승인)"

    event_no = _next_event_no(db, approval.company_id)
    summary = "승인 완료" if decision == "approved" else f"반려: {payload.reason}"
    db.add(
        EvidenceEvent(
            id=str(uuid.uuid4()),
            company_id=approval.company_id,
            event_no=event_no,
            type="approval_decided",
            at=now,
            case_id=approval.case_id,
            action_id=approval.action_id,
            approval_id=approval.id,
            actor_type="approver",
            actor_user_id=payload.decided_by_user_id,
            actor_display=actor_display,
            summary=summary,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApprovalIdempotencyKeyReusedError() from exc
    db.refresh(approval)
    db.refresh(case)
    return approval, case.state
