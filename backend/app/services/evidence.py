"""판단 기록(evidence_events) 일반 기록/조회 서비스 — R2.5. docs/DB_SCHEMA.md §4.5.

`next_event_no`는 원래 services/approvals.py에 사적으로 있던 것을 여기로 옮겨 공유한다
(companies.evidence_seq 원자 증가는 어느 도메인이 이벤트를 남기든 같은 채번 규칙을 써야
한다 — §9 "전 도메인이 한 번호대 공유").
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.ids import new_id
from app.domain.evidence_exceptions import (
    EvidenceCaseNotFoundError,
    EvidenceInvalidTypeError,
    EvidenceReasonContainsPiiError,
)
from app.domain.pii import contains_pii
from app.models.case import Case
from app.models.company import Company
from app.models.evidence import EvidenceEvent
from app.models.membership import Membership
from app.models.user import User
from app.schemas.evidence import EvidenceEventCreate

# 무인증(패키지 링크) 전용 타입 — 세션이 없는 화면(ExpertLinkPage)에서 나오므로 이 인증
# 필요 엔드포인트로는 절대 기록할 수 없다. app/services/packages.py가 자기 트랜잭션 안에서
# 직접 기록한다(docs/DB_SCHEMA.md §4.5 R2.5 노트).
PACKAGE_LINK_EVIDENCE_TYPES = frozenset({"package_link_issued", "package_link_viewed", "package_reply"})

# 코드리뷰 지적(PR #20 P1): 이 엔드포인트는 세션만 있으면(회사 소속 여부만) 통과하는
# get_current_membership 뒤에 있다 — role 검사도, "실제로 그 행위를 했는가" 검사도 없다.
# 이전에는 ALLOWED_EVIDENCE_TYPES가 approval_decided/role_changed/dispatch_executed 같은
# "결정·특권 행위의 결과"까지 그대로 받아, 아무 구성원이나 존재하지 않는 승인·역할변경·
# 발송완료를 감사 로그에 위조해 넣을 수 있었다(GlobalEvidencePage가 그 행을 실제 서버
# 기록과 구분 없이 보여준다). 이런 타입은 반드시 해당 행위를 실제로 처리하는 서버 로직
# 안에서만(같은 DB 트랜잭션으로) 기록돼야 한다 — approval_decided/approval_requested는
# 이미 services/approvals.py가 그렇게 한다(decide_approval/request_approval). 나머지
# (role/delegation/dispatch/worker 생애주기)는 아직 전용 백엔드가 없는데, 그렇다고 이
# 범용 엔드포인트로 받아주면 "감사됐다"는 거짓 신호만 남기므로 여기서도 거부한다 — 전용
# 백엔드가 생기기 전까지는 그 행위들에 대한 감사 기록 자체가 없는 것이 위조된 기록이
# 있는 것보다 안전하다.
PRIVILEGED_EVIDENCE_TYPES = frozenset(
    {
        "approval_requested",
        "approval_decided",
        "approval_rejected",
        "approval_escalated",
        "role_granted",
        "role_changed",
        "member_invited",
        "member_removed",
        "delegation_granted",
        "delegation_revoked",
        "autonomy_changed",
        "worker_deleted",
        "dispatch_executed",
        "delivery_confirmed",
    }
)

# db/schema.sql evidence_events.type CHECK과 동일 목록(R2.5) 중 무인증 전용 3종 +
# PRIVILEGED_EVIDENCE_TYPES를 제외한 것 — 이 엔드포인트로 POST 가능한(순수 관찰·정보성)
# 타입 전체. CHECK와 어긋나면 DB가 최종 방어선이지만, 여기서 먼저 걸러야 사용자에게 500이
# 아니라 422를 준다.
ALLOWED_EVIDENCE_TYPES = (
    frozenset(
        {
            "intent_classified",
            "plan_created",
            "tool_executed",
            "rag_retrieved",
            "risk_flagged",
            "approval_requested",
            "approval_decided",
            "approval_rejected",
            "review_started",
            "checklist_completed",
            "exported",
            "final_response_generated",
            "briefing_emitted",
            "worker_reply_received",
            "worker_reply_summarized",
            "status_update_confirmed",
            "handoff_generated",
            "delegation_granted",
            "delegation_revoked",
            "role_granted",
            "role_changed",
            "member_invited",
            "member_removed",
            "approval_escalated",
            "autonomy_changed",
            "worker_deleted",
            "interpretation_confirmed",
            "dispatch_executed",
            "delivery_confirmed",
        }
    )
    - PACKAGE_LINK_EVIDENCE_TYPES
    - PRIVILEGED_EVIDENCE_TYPES
)


def next_event_no(db: Session, company_id: str) -> int:
    """companies.evidence_seq를 원자적으로 증가시키고 새 값을 받는다(§9). 경합 안전(단문 UPDATE)."""
    return db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(evidence_seq=Company.evidence_seq + 1)
        .returning(Company.evidence_seq)
    ).scalar_one()


def create_evidence_event(db: Session, membership: Membership, payload: EvidenceEventCreate) -> EvidenceEvent:
    if payload.type not in ALLOWED_EVIDENCE_TYPES:
        raise EvidenceInvalidTypeError(payload.type)
    # 코드리뷰 지적(PR #20 P1): summary만 PII 패턴을 검사해, input_hash/output_hash/
    # trace_id/request_id/payload_ref 같은 나머지 자유 텍스트 필드로 원문 PII를 그대로
    # 우회 저장할 수 있었다 — 필드 이름이 "해시"/"참조"를 암시할 뿐 실제로는 클라이언트가
    # 임의 문자열을 보낼 수 있는 필드이므로, 이 엔드포인트가 받는 모든 자유 텍스트 필드를
    # 검사한다.
    free_text_fields = (
        payload.summary,
        payload.input_hash,
        payload.output_hash,
        payload.trace_id,
        payload.request_id,
        payload.payload_ref,
    )
    if any(contains_pii(value) for value in free_text_fields):
        raise EvidenceReasonContainsPiiError()

    if payload.case_id is not None:
        case = db.execute(
            select(Case).where(Case.company_id == membership.company_id, Case.id == payload.case_id)
        ).scalar_one_or_none()
        if case is None:
            raise EvidenceCaseNotFoundError(payload.case_id)

    now = dt.datetime.now(dt.timezone.utc)
    event_no = next_event_no(db, membership.company_id)
    user = db.get(User, membership.user_id)
    event = EvidenceEvent(
        id=new_id(),
        company_id=membership.company_id,
        event_no=event_no,
        type=payload.type,
        at=now,
        case_id=payload.case_id,
        actor_type="user",
        actor_user_id=membership.user_id,
        actor_display=user.name if user else None,
        summary=payload.summary,
        input_hash=payload.input_hash,
        output_hash=payload.output_hash,
        trace_id=payload.trace_id,
        request_id=payload.request_id,
        payload_ref=payload.payload_ref,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_evidence_events(db: Session, company_id: str, case_id: str | None = None) -> list[EvidenceEvent]:
    stmt = select(EvidenceEvent).where(EvidenceEvent.company_id == company_id)
    if case_id is not None:
        stmt = stmt.where(EvidenceEvent.case_id == case_id)
    stmt = stmt.order_by(EvidenceEvent.event_no.asc())
    return list(db.execute(stmt).scalars())
