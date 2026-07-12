from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CASE_TYPES = (
    "visa_expiry",
    "missing_document",
    "contract_visa_conflict",
    "reporting_deadline",
    "quota_review",
    "hiring",
    "onboarding",
    "other",
)
# 상태 전이 화이트리스트는 docs/DB_SCHEMA.md §5.1 — 이 목록은 값 집합만, 전이 검증은 서비스 계층.
CASE_STATES = ("draft", "risk_review", "approval_pending", "returned", "human_approved", "completed", "blocked")
AGENT_STAGES = ("detected", "collecting", "drafted", "awaiting_approval", "executed")
PREPARED_BY = ("agent", "rule")

NEXT_ACTION_KINDS = ("approve", "draft", "detail", "thread", "package", "confirm")
NEXT_ACTION_TYPES = (
    "request_document",
    "create_handoff",
    "send_message",
    "confirm_status",
    "export_package",
    "complete_case",
    "other",
)
NEXT_ACTION_STATES = ("ready", "locked", "scheduled", "waiting")
NEXT_ACTION_SLOTS = ("primary", "secondary")

# 케이스 재사용 규칙(레거시 PRD §15 승계) — 열린 상태 케이스 중복 생성 방지(§4.3)
_OPEN_CASE_STATES_SQL = "state IN ('draft','risk_review','approval_pending','returned')"


class Case(Base):
    """케이스(업무·요청 단위, 브리핑 카드와 1:1 — 결정 D2). docs/DB_SCHEMA.md §4.3."""

    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(f"case_type IN ({','.join(repr(v) for v in CASE_TYPES)})", name="ck_cases_case_type"),
        CheckConstraint(f"state IN ({','.join(repr(v) for v in CASE_STATES)})", name="ck_cases_state"),
        CheckConstraint(
            f"agent_stage IS NULL OR agent_stage IN ({','.join(repr(v) for v in AGENT_STAGES)})",
            name="ck_cases_agent_stage",
        ),
        CheckConstraint(f"prepared_by IN ({','.join(repr(v) for v in PREPARED_BY)})", name="ck_cases_prepared_by"),
        CheckConstraint(
            "checked_items IS NULL OR json_valid(checked_items)", name="ck_cases_checked_items_json"
        ),
        UniqueConstraint("company_id", "case_code", name="ux_cases_company_case_code"),
        Index("ix_cases_company_state", "company_id", "state"),
        Index("ix_cases_company_severity_due", "company_id", "severity", "due_date"),
        Index(
            "ux_cases_reuse",
            "company_id",
            "worker_id",
            "case_type",
            "due_date",
            unique=True,
            sqlite_where=text(_OPEN_CASE_STATES_SQL),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    case_code: Mapped[str] = mapped_column(Text, nullable=False)  # "case_002" — 회사별 발급(§9)
    worker_id: Mapped[str | None] = mapped_column(Text, ForeignKey("workers.id", ondelete="SET NULL"))
    case_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)  # 업무 단위 명칭(근로자명 미포함)
    summary: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    agent_stage: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[dt.date | None] = mapped_column(Date)  # D-day 앵커. dDay는 저장하지 않음(§6)
    assignee_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    approval_required: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="ck_cases_approval_required"), nullable=False, server_default="0"
    )
    prepared_by: Mapped[str] = mapped_column(Text, nullable=False, server_default="rule")
    # runs와 순환 참조 — Alembic 마이그레이션이 유일한 스키마 생성 경로라 위상정렬 문제 없음(README 참조)
    prepared_run_id: Mapped[str | None] = mapped_column(Text, ForeignKey("runs.id"))  # noqa: F821
    parent_case_id: Mapped[str | None] = mapped_column(Text, ForeignKey("cases.id"))  # 런 체이닝(9단계 P0-2)
    guard_note: Mapped[str | None] = mapped_column(Text)  # high risk 경고문(Rule Engine 산출)
    checked_items: Mapped[dict | list | None] = mapped_column(JSON)  # AICheckedBlock 스냅샷(마스킹 적용)
    next_wake_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    next_wake_condition: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="cases")  # noqa: F821
    next_actions: Mapped[list["NextAction"]] = relationship(back_populates="case")
    citation_links: Mapped[list["CaseCitation"]] = relationship(back_populates="case")  # noqa: F821


class NextAction(Base):
    """다음 행동(케이스에 붙는 실행 후보). docs/DB_SCHEMA.md §4.3."""

    __tablename__ = "next_actions"
    __table_args__ = (
        CheckConstraint(f"kind IN ({','.join(repr(v) for v in NEXT_ACTION_KINDS)})", name="ck_next_actions_kind"),
        CheckConstraint(
            f"action_type IN ({','.join(repr(v) for v in NEXT_ACTION_TYPES)})", name="ck_next_actions_action_type"
        ),
        CheckConstraint(f"state IN ({','.join(repr(v) for v in NEXT_ACTION_STATES)})", name="ck_next_actions_state"),
        CheckConstraint(
            f"slot IS NULL OR slot IN ({','.join(repr(v) for v in NEXT_ACTION_SLOTS)})", name="ck_next_actions_slot"
        ),
        Index("ix_next_actions_case", "case_id"),
        Index("ix_next_actions_company", "company_id", "state"),
        Index("ux_next_actions_slot", "case_id", "slot", unique=True, sqlite_where=text("slot IS NOT NULL")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(Text, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)  # "보내기 승인" 등 — 데이터 구동 CTA
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="ready")
    requires_approval: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="ck_next_actions_requires_approval"), nullable=False, server_default="0"
    )
    slot: Mapped[str | None] = mapped_column(Text)  # 카드 CTA 슬롯(primary/secondary)
    scheduled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # N13 발생 소스
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    case: Mapped["Case"] = relationship(back_populates="next_actions")
