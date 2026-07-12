from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 코어(src/types.ts EvidenceType과 동일) + 확장(스펙 요구 — 화면이 붙는 마일스톤에 프론트 타입에도 추가)
# docs/DB_SCHEMA.md §4.5
EVIDENCE_EVENT_TYPES = (
    "intent_classified",
    "plan_created",
    "tool_executed",
    "rag_retrieved",
    "risk_flagged",
    "approval_requested",
    "approval_decided",
    "review_started",
    "checklist_completed",
    "exported",
    "final_response_generated",
    "briefing_emitted",
    "notification_sent",
    "worker_reply_received",
    "worker_reply_summarized",
    "status_update_confirmed",
    "handoff_generated",
    "package_link_issued",
    "package_link_viewed",
    "delegation_granted",
    "delegation_revoked",
    "role_granted",
    "role_changed",
    "member_invited",
    "member_removed",
    "approval_escalated",
    "autonomy_changed",
    "worker_deleted",
)
EVIDENCE_ACTOR_TYPES = ("system", "user", "agent", "approver")


class EvidenceEvent(Base):
    """append-only 감사 스트림(M8·§2d·§3c의 정본). 수정·삭제는 DB 트리거가 차단(§5.2, 마이그레이션 참조).

    docs/DB_SCHEMA.md §4.5.
    """

    __tablename__ = "evidence_events"
    __table_args__ = (
        CheckConstraint(f"type IN ({','.join(repr(v) for v in EVIDENCE_EVENT_TYPES)})", name="ck_evidence_events_type"),
        CheckConstraint(
            f"actor_type IN ({','.join(repr(v) for v in EVIDENCE_ACTOR_TYPES)})", name="ck_evidence_events_actor_type"
        ),
        UniqueConstraint("company_id", "event_no", name="ux_evidence_events_company_event_no"),
        Index("ix_evidence_company_at", "company_id", "at"),
        Index("ix_evidence_case", "case_id"),
        Index("ix_evidence_request", "request_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    event_no: Mapped[int] = mapped_column(nullable=False)  # 회사별 단조 증가 — 표시 "#4789"(§9)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 발생 시각(주입 가능)
    case_id: Mapped[str | None] = mapped_column(Text, ForeignKey("cases.id"))
    action_id: Mapped[str | None] = mapped_column(Text, ForeignKey("next_actions.id"))
    approval_id: Mapped[str | None] = mapped_column(Text, ForeignKey("approvals.id"))
    run_id: Mapped[str | None] = mapped_column(Text, ForeignKey("runs.id"))
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    actor_display: Mapped[str | None] = mapped_column(Text)  # "김담당 (본인 확인 완료)" — 마스킹된 표시 문자열
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # PII 마스킹된 한 줄 요약만. 원문 전문 금지
    input_hash: Mapped[str | None] = mapped_column(Text)  # 'sha256:…'
    output_hash: Mapped[str | None] = mapped_column(Text)
    hash_algorithm: Mapped[str] = mapped_column(Text, nullable=False, server_default="sha256")
    trace_id: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(Text)
    payload_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
