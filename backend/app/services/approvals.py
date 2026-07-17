"""승인 결정·요청 서비스 — docs/DB_SCHEMA.md §5.3 승인 게이트 불변식을 강제한다.

상태 전이 + evidence append는 같은 트랜잭션(§0-4, 레거시 PRD Transaction rule 승계) —
각 함수 안에서 커밋 하나로 묶는다. 실패하면 아무 것도 반영되지 않는다.

동시성(F1): decide_approval은 대상 approval 행을 `SELECT ... FOR UPDATE`로 잠근다(PostgreSQL
네이티브 행 잠금). 두 요청이 같은 pending 승인을 동시에 결정하면 하나는 잠금을 얻고, 다른
하나는 그 뒤에 직렬화되어 이미 결정된 승인을 보고 409로 떨어진다. `evidence_seq` 발급도
UPDATE ... RETURNING으로 원자화한다. request_approval은 잠글 기존 행이 없으므로
`ux_approvals_one_pending` 부분 유니크 인덱스가 동시성 방어선이다(동시 생성 시 하나만 성공).
DB 트리거(approvals_update_guard·cases_state_transition 등)가 최종 방어선이며, 서비스
가드는 그 위반을 500이 아니라 친절한 4xx로 변환하는 계층이다.

결정자·요청자 신원(decided_by_user_id/requested_by_user_id)은 더 이상 요청 바디로 받지
않는다 — 인증된 세션에서 도출한 값을 파라미터로 받는다(app/api/deps.py의
get_current_user_id, §13-11).
"""

from __future__ import annotations

import datetime as dt
import hashlib
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.auth_tokens import secrets_match
from app.domain.case_transitions import can_transition
from app.domain.exceptions import (
    ApprovalActionNotRequestableError,
    ApprovalAlreadyDecidedError,
    ApprovalAlreadyPendingError,
    ApprovalBlockedByEvidenceError,
    ApprovalChecklistIncompleteError,
    ApprovalDelegationInvalidError,
    ApprovalForbiddenError,
    ApprovalIdempotencyKeyReusedError,
    ApprovalIdentityRequiredError,
    ApprovalNotFoundError,
    ApprovalPinInvalidError,
    ApprovalReasonContainsPiiError,
    ApprovalReasonRequiredError,
    CaseTransitionError,
)
from app.domain.pii import contains_pii
from app.models.approval import Approval
from app.models.case import Case, NextAction
from app.models.citation import CaseCitation, Citation
from app.models.company import Company
from app.models.delegation import Delegation
from app.models.evidence import EvidenceEvent
from app.models.membership import Membership
from app.models.user import User
from app.schemas.approval import ApprovalDecisionRequest
from app.services.evidence import next_event_no as _next_event_no

APPROVER_ROLES = ("owner", "manager")
ALLOWED_REQUEST_ROLES = ("manager",)  # 7단계 권한 매트릭스: 케이스 진행(C/R/U)은 manager만(owner는 R)


def _verify_identity(db: Session, payload: ApprovalDecisionRequest, decided_by_user_id: str) -> None:
    """본인확인 수단 필수(§5.3-6, 7단계 §4) — approve·reject 공통. identity_method='pin'이면
    R2.4부터 users.pin_hash와 실제로 대조한다(이전엔 문자열 존재만 확인했다)."""
    if payload.identity_method not in ("pin", "biometric"):
        raise ApprovalIdentityRequiredError()
    if payload.identity_method == "pin":
        decider = db.get(User, decided_by_user_id)
        if decider is None or decider.pin_hash is None:
            raise ApprovalPinInvalidError("PIN이 등록되지 않았습니다")
        if not payload.pin or not secrets_match(payload.pin, decider.pin_hash):
            raise ApprovalPinInvalidError("PIN이 일치하지 않습니다")


def _validate_delegation(
    db: Session, payload: ApprovalDecisionRequest, company_id: str, decided_by_user_id: str, now: dt.datetime
) -> None:
    """on_behalf_of_user_id가 있으면 실제 위임 관계를 검증한다(§13-10, R2.4) — DB 트리거
    (trg_approvals_decider_role)가 최종 방어선이지만, 여기서 먼저 친절한 403으로 바꾼다."""
    if payload.on_behalf_of_user_id is None:
        return
    delegation = db.execute(
        select(Delegation).where(
            Delegation.company_id == company_id,
            Delegation.delegator_user_id == payload.on_behalf_of_user_id,
            Delegation.delegate_user_id == decided_by_user_id,
            Delegation.scope == "approval",
            Delegation.revoked_at.is_(None),
            Delegation.starts_at <= now,
            Delegation.ends_at > now,
        )
    ).scalar_one_or_none()
    delegator_membership = db.execute(
        select(Membership).where(
            Membership.company_id == company_id,
            Membership.user_id == payload.on_behalf_of_user_id,
            Membership.status == "active",
            Membership.role == "owner",
        )
    ).scalar_one_or_none()
    if delegation is None or delegator_membership is None:
        raise ApprovalDelegationInvalidError()


def usable_citation_count(db: Session, company_id: str, case_id: str) -> int:
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


def decide_approval(
    db: Session,
    approval_id: str,
    decision: Literal["approved", "rejected"],
    payload: ApprovalDecisionRequest,
    decided_by_user_id: str,
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
            Membership.user_id == decided_by_user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None or membership.role not in APPROVER_ROLES:
        raise ApprovalForbiddenError("승인 권한이 없습니다")

    now = dt.datetime.now(dt.timezone.utc)

    # 위임 유효성(§13-10, R2.4) — approve·reject 공통, 결정 시각(now) 기준.
    _validate_delegation(db, payload, approval.company_id, decided_by_user_id, now)

    # 화면이 체크리스트를 제출했으면 결정 게이트 평가에 그 값을 쓴다(R2.4) — approval.checklist에는
    # 아직 쓰지 않는다: ORM 속성을 지금 바꾸면 뒤이은 SELECT(usable_citation_count 등)의
    # autoflush가 status 변경 없이 checklist만 UPDATE하는 별도 문장을 내보내는데,
    # trg_approvals_update_guard가 "pending에서 승인/반려로 전이하는 UPDATE만" 허용해 그
    # 중간 UPDATE에서 예외가 난다 — 다른 approval.* 필드들과 한 번에(아래 db.flush() 직전) 쓴다.
    checklist_value = (
        [item.model_dump() for item in payload.checklist] if payload.checklist is not None else approval.checklist
    )

    # F3: 자유 텍스트(반려 사유·승인 의견)에 PII 패턴이 있으면 저장 전에 차단(approve·reject 공통).
    if payload.reason and contains_pii(payload.reason):
        raise ApprovalReasonContainsPiiError()

    if decision == "approved":
        # 결정자 권한 세분화: manager는 approval_policy='manager_allowed'이고
        # 케이스 severity가 LOW일 때만(§5.3-6, docs/DB_SCHEMA.md §13-9) — 단, 유효한 위임을
        # 받아 대리 승인하는 경우는 예외다(위 _validate_delegation이 이미 검증 완료, R2.4).
        # 주의: 'low risk'를 severity=LOW로 근사한 것 — 실제 액션 위험도 모델은 §13-9 미결.
        if membership.role == "manager" and payload.on_behalf_of_user_id is None:
            company = db.get(Company, approval.company_id)
            if not (company.approval_policy == "manager_allowed" and case.severity == "LOW"):
                raise ApprovalForbiddenError("이 승인은 대표만 가능합니다")

        # high risk 케이스(기한 경과 등, state='blocked')는 handoff 계열 액션만 승인 가능(§5.3-7, GOTCHAS §1)
        if case.state == "blocked" and next_action.action_type != "create_handoff":
            raise ApprovalForbiddenError(
                "기한 경과 등 고위험 케이스는 행정사 전달 액션만 승인할 수 있습니다"
            )

        # citation-0 잠금: 사용 가능 근거 0건이면 승인 불가(§5.3-3, GOTCHAS §3)
        if usable_citation_count(db, approval.company_id, approval.case_id) < 1:
            raise ApprovalBlockedByEvidenceError()

        # M2.6 체크리스트: 값이 있으면(=화면이 제출했으면) 전 항목 checked여야 함(§5.3-5)
        if checklist_value is not None:
            items = checklist_value if isinstance(checklist_value, list) else []
            if not items or not all(item.get("checked") for item in items):
                raise ApprovalChecklistIncompleteError()

        # 본인확인 수단 필수 — 세션만으로 승인 불가(§5.3-6, 7단계 §4). PIN이면 값도 검증한다.
        _verify_identity(db, payload, decided_by_user_id)
    else:
        if not payload.reason:
            raise ApprovalReasonRequiredError()
        # 반려도 사람 결정이므로 본인확인 필수(approve와 동일 — 스키마 approvals CHECK도 강제)
        _verify_identity(db, payload, decided_by_user_id)

    # 케이스 상태 전이는 approval_pending 케이스에서만 일어난다. 그 외(예: blocked 고위험
    # handoff 승인)는 승인/연계 패키지만 결정되고 케이스 상태는 유지된다 — blocked는 종착이며
    # 작업은 행정사로 넘어간다(batbayar 플로우). approve→human_approved, reject→returned.
    if case.state == "approval_pending":
        target_state = "human_approved" if decision == "approved" else "returned"
    else:
        target_state = None

    if target_state is not None and not can_transition(case.state, target_state):
        raise CaseTransitionError(case.state, target_state)

    approval.status = decision
    approval.idempotency_key = payload.idempotency_key
    approval.decided_by_user_id = decided_by_user_id
    approval.on_behalf_of_user_id = payload.on_behalf_of_user_id
    approval.identity_method = payload.identity_method
    approval.reason = payload.reason
    approval.checklist = checklist_value
    approval.decided_at = now
    # 승인 UPDATE를 먼저 DB에 반영한다 — cases_state_transition 트리거가 human_approved 전이 시
    # '승인된 케이스 액션 존재'를 검사하므로, 케이스 UPDATE보다 approval UPDATE가 앞서야 한다.
    db.flush()

    if target_state is not None:
        case.state = target_state
        case.updated_at = now
        db.flush()

    decider = db.get(User, decided_by_user_id)
    actor_display = f"{decider.name} (본인)" if payload.on_behalf_of_user_id is None else f"{decider.name} (대리 승인)"

    event_no = _next_event_no(db, approval.company_id)
    summary = "승인 완료" if decision == "approved" else "반려"
    # PII 보안 리뷰: 코드 리뷰 지적(PR #10) — reason 원문을 summary에 넣으면 append-only
    # evidence_events가 정규식(contains_pii)이 못 잡는 이름·이메일 등 자유형 PII까지 영구
    # 저장하게 된다. evidence_events.summary DDL 주석 "PII 마스킹된 한 줄 요약만. 원문 전문
    # 금지"를 지키기 위해 요약은 고정 문자열로 두고, 사유는 해시로만 남긴다(검증 가능하되
    # 원문은 복원 불가) — 원문 자체는 approvals.reason(§4.3, evidence_events가 아님)에 남는다.
    reason_hash = f"sha256:{hashlib.sha256(payload.reason.encode()).hexdigest()}" if payload.reason else None
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=approval.company_id,
            event_no=event_no,
            type="approval_decided" if decision == "approved" else "approval_rejected",
            at=now,
            case_id=approval.case_id,
            action_id=approval.action_id,
            approval_id=approval.id,
            actor_type="approver",
            actor_user_id=decided_by_user_id,
            actor_display=actor_display,
            summary=summary,
            output_hash=reason_hash,
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


def request_approval(db: Session, action_id: str, requested_by_user_id: str) -> tuple[Approval, str]:
    """승인 요청 생성. `requested_by_actor='user'`만 다룬다 — agent/rule 트리거(프로액티브 런)는
    별도 범위(9단계, backend/app/agent_runtime/ 이관 시점의 몫)."""
    next_action = db.get(NextAction, action_id)
    if next_action is None:
        raise ApprovalNotFoundError(action_id)

    membership = db.execute(
        select(Membership).where(
            Membership.company_id == next_action.company_id,
            Membership.user_id == requested_by_user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None or membership.role not in ALLOWED_REQUEST_ROLES:
        raise ApprovalForbiddenError("승인 요청 권한이 없습니다")

    if not next_action.requires_approval:
        raise ApprovalActionNotRequestableError("승인이 필요하지 않은 액션입니다")
    if next_action.state != "ready":
        raise ApprovalActionNotRequestableError(f"준비되지 않은 액션입니다 (state={next_action.state})")

    existing = db.execute(
        select(Approval).where(Approval.action_id == action_id, Approval.status == "pending")
    ).scalar_one_or_none()
    if existing is not None:
        raise ApprovalAlreadyPendingError(action_id)

    case = db.get(Case, next_action.case_id)
    if not can_transition(case.state, "approval_pending"):
        raise CaseTransitionError(case.state, "approval_pending")

    now = dt.datetime.now(dt.timezone.utc)
    approval = Approval(
        id=new_id(),
        company_id=next_action.company_id,
        case_id=next_action.case_id,
        action_id=action_id,
        status="pending",
        requested_by_actor="user",
        requested_by_user_id=requested_by_user_id,
        requested_at=now,
    )
    db.add(approval)
    db.flush()

    case.state = "approval_pending"
    case.updated_at = now
    db.flush()

    event_no = _next_event_no(db, next_action.company_id)
    requester = db.get(User, requested_by_user_id)
    db.add(
        EvidenceEvent(
            id=new_id(),
            company_id=next_action.company_id,
            event_no=event_no,
            type="approval_requested",
            at=now,
            case_id=next_action.case_id,
            action_id=action_id,
            approval_id=approval.id,
            actor_type="user",
            actor_user_id=requested_by_user_id,
            actor_display=f"{requester.name} (본인)",
            summary="승인 요청",
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApprovalAlreadyPendingError(action_id) from exc
    db.refresh(approval)
    db.refresh(case)
    return approval, case.state
