from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

DRAFT_STATUSES = ("draft", "revision_requested", "pending_approval", "approved", "rejected", "superseded")
DRAFT_LANGS = ("ko", "vi", "id", "en")


class Draft(Base):
    """메시지 초안(M3). docs/DB_SCHEMA.md §4.7.

    P1 스코프 주의: thread_id는 컬럼만 있고 FK 제약이 없다 — 참조 대상 threads가 P2 테이블이라
    아직 없다(backend/README.md "알려진 스코프 경계"). P2 마이그레이션에서 FK를 추가한다.
    """

    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint(f"status IN ({','.join(repr(v) for v in DRAFT_STATUSES)})", name="ck_drafts_status"),
        CheckConstraint("sent_at IS NULL", name="ck_drafts_sent_at_null"),  # MVP 발송 차단(§0-4·§5.4)
        CheckConstraint(
            "compliance_checks IS NULL OR json_valid(compliance_checks)", name="ck_drafts_compliance_checks_json"
        ),
        CheckConstraint(
            "expected_scenarios IS NULL OR json_valid(expected_scenarios)", name="ck_drafts_expected_scenarios_json"
        ),
        Index("ix_drafts_case", "case_id", "status"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(Text, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(Text)  # FK 없음 — P2에서 threads 도입 시 추가
    created_by_run_id: Mapped[str | None] = mapped_column(Text, ForeignKey("runs.id"))
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    approval_id: Mapped[str | None] = mapped_column(Text, ForeignKey("approvals.id"))
    compliance_checks: Mapped[dict | list | None] = mapped_column(JSON)  # 하나라도 false → 승인 locked(§5.3)
    expected_scenarios: Mapped[dict | list | None] = mapped_column(JSON)
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # 항상 NULL(CHECK)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    variants: Mapped[list["DraftVariant"]] = relationship(back_populates="draft")


class DraftVariant(Base):
    """초안 언어 변형. docs/DB_SCHEMA.md §4.7."""

    __tablename__ = "draft_variants"
    __table_args__ = (CheckConstraint(f"lang IN ({','.join(repr(v) for v in DRAFT_LANGS)})", name="ck_draft_variants_lang"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    draft_id: Mapped[str] = mapped_column(Text, ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False)
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)  # 전문 저장 — §7 접근 규칙, evidence 복사 금지
    is_revised: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="ck_draft_variants_is_revised"), nullable=False, server_default="0"
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    draft: Mapped["Draft"] = relationship(back_populates="variants")
