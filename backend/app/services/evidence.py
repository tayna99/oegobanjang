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

# db/schema.sql evidence_events.type CHECK과 동일 목록(R2.5) 중 위 3종을 제외한 것 — 이
# 엔드포인트로 POST 가능한 타입 전체. CHECK와 어긋나면 DB가 최종 방어선이지만, 여기서 먼저
# 걸러야 사용자에게 500이 아니라 422를 준다.
ALLOWED_EVIDENCE_TYPES = frozenset(
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
) - PACKAGE_LINK_EVIDENCE_TYPES


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
    if contains_pii(payload.summary):
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
