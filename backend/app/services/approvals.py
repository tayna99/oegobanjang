"""승인 결정 서비스 — docs/DB_SCHEMA.md §5.3 승인 게이트 불변식을 강제한다.

상태 전이 + evidence append는 같은 트랜잭션(§0-4, 레거시 PRD Transaction rule 승계) —
이 함수 안에서 커밋 하나로 묶는다. 실패하면 아무 것도 반영되지 않는다.

동시성(F1): 대상 approval 행을 `SELECT ... FOR UPDATE`로 잠근다(PostgreSQL 네이티브 행 잠금).
두 요청이 같은 pending 승인을 동시에 결정하면 하나는 잠금을 얻고, 다른 하나는 그 뒤에
직렬화되어 이미 결정된 승인을 보고 409로 떨어진다. `evidence_seq` 발급도 UPDATE ... RETURNING
으로 원자화한다. DB 트리거(approvals_update_guard·cases_state_transition 등)가 최종 방어선이며,
서비스 가드는 그 위반을 500이 아니라 친절한 4xx로 변환하는 계층이다.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.ids import new_id
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


def _usable_citation_count(db: Session, company_id: str, case_id: str) -> int:
    """사용 가능 근거 수 — F등급(합성) 제외 + 스코프(전역 또는 자사)만(§5.3-3, §4.4)."""
    return db.execute(
        select(func.count(CaseCitation.citation_id))
        .join(Citation, Citation.id == CaseCitation.citation_id)
        .where(
            CaseCitation.company_id == company_id,
            CaseCitation.case_id == case_id,
            Citation.grade != "F",
            (Citation.company_id.is_(None)) | (Citation.company_id == company_id),
        )
    ).scalar_one()


def _next_event_no(db: Session, company_id: str) -> int:
    """companies.evidence_seq를 원자적으로 증가시키고 새 값을 받는다(§9). 경합 안전(단문 UPDATE)."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(evidence_seq=Company.evidence_seq + 1)
        .returning(Company.evidence_seq)
    ).scalar_one()


def decide_approval(
    db: Session,
    approval_id: str,
    decision: Literal["approved", "rejected"],
    payload: ApprovalDecisionRequest,
) -> tuple[Approval, str]:
    """승인/반려 처리. 반환값은 (갱신된 Approval, 갱신된 case.state)."""
    # F1: 대상 행을 잠근다 — 동시 결정은 여기서 직렬화된다.
    approval = db.get(Approval, approval_id, with_for_update=True)
    if approval is None:
        raise ApprovalNotFoundError(approval_id)

    if approval.status != "pending":
        # 멱등 replay(GOTCHAS §2, §5.3-2): 같은 키 + 같은 결정 방향이어야 성립.
        # approve로 소진된 키로 reject를 재호출하는 등 방향이 다르면 409(F2).
        if (
            approval.idempotency_key is not None
            and approval.idempotency_key == payload.idempotency_key
            and approval.status == decision
        ):
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

    # F3: 자유 텍스트(반려 사유·승인 의견)에 PII 패턴이 있으면 저장 전에 차단(approve·reject 공통).
    if payload.reason and contains_pii(payload.reason):
        raise ApprovalReasonContainsPiiError()

    if decision == "approved":
        # 결정자 권한 세분화: manager는 approval_policy='manager_allowed'이고
        # 케이스 severity가 LOW일 때만(§5.3-6, docs/DB_SCHEMA.md §13-4).
        # 주의: 'low risk'를 severity=LOW로 근사한 것 — 실제 액션 위험도 모델은 §13-9 미결.
        if membership.role == "manager":
            company = db.get(Company, approval.company_id)
            if not (company.approval_policy == "manager_allowed" and case.severity == "LOW"):
                raise ApprovalForbiddenError("이 승인은 대표만 가능합니다")

        # high risk 케이스(기한 경과 등, state='blocked')는 handoff 계열 액션만 승인 가능(§5.3-7, GOTCHAS §1)
        if case.state == "blocked" and next_action.action_type != "create_handoff":
            raise ApprovalForbiddenError(
                "기한 경과 등 고위험 케이스는 행정사 전달 액션만 승인할 수 있습니다"
            )

        # citation-0 잠금: 사용 가능 근거 0건이면 승인 불가(§5.3-3, GOTCHAS §3)
        if _usable_citation_count(db, approval.company_id, approval.case_id) < 1:
            raise ApprovalBlockedByEvidenceError()

        # M2.6 체크리스트: 값이 있으면(=화면이 제출했으면) 전 항목 checked여야 함(§5.3-5)
        if approval.checklist is not None:
            items = approval.checklist if isinstance(approval.checklist, list) else []
            if not items or not all(item.get("checked") for item in items):
                raise ApprovalChecklistIncompleteError()

        # 본인확인 수단 필수 — 세션만으로 승인 불가(§5.3-6, 7단계 §4)
        if payload.identity_method not in ("pin", "biometric"):
            raise ApprovalIdentityRequiredError()
    else:
        if not payload.reason:
            raise ApprovalReasonRequiredError()
        # 반려도 사람 결정이므로 본인확인 필수(approve와 동일 — 스키마 approvals CHECK가 강제)
        if payload.identity_method not in ("pin", "biometric"):
            raise ApprovalIdentityRequiredError()

    # 케이스 상태 전이는 approval_pending 케이스에서만 일어난다. 그 외(예: blocked 고위험
    # handoff 승인)는 승인/연계 패키지만 결정되고 케이스 상태는 유지된다 — blocked는 종착이며
    # 작업은 행정사로 넘어간다(batbayar 플로우). approve→human_approved, reject→returned.
    if case.state == "approval_pending":
        target_state = "human_approved" if decision == "approved" else "returned"
    else:
        target_state = None

    if target_state is not None and not can_transition(case.state, target_state):
        raise CaseTransitionError(case.state, target_state)

    now = dt.datetime.now(dt.timezone.utc)

    approval.status = decision
    approval.idempotency_key = payload.idempotency_key
    approval.decided_by_user_id = payload.decided_by_user_id
    approval.on_behalf_of_user_id = payload.on_behalf_of_user_id
    approval.identity_method = payload.identity_method
    approval.reason = payload.reason
    approval.decided_at = now
    # 승인 UPDATE를 먼저 DB에 반영한다 — cases_state_transition 트리거가 human_approved 전이 시
    # '승인된 케이스 액션 존재'를 검사하므로, 케이스 UPDATE보다 approval UPDATE가 앞서야 한다.
    db.flush()

    if target_state is not None:
        case.state = target_state
        case.updated_at = now
        db.flush()

    decider = db.get(User, payload.decided_by_user_id)
    actor_display = f"{decider.name} (본인)" if payload.on_behalf_of_user_id is None else f"{decider.name} (대리 승인)"

    event_no = _next_event_no(db, approval.company_id)
    summary = "승인 완료" if decision == "approved" else f"반려: {payload.reason}"
    db.add(
        EvidenceEvent(
            id=new_id(),
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
