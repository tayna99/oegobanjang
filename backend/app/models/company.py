from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

WORKER_COUNT_BANDS = ("lt5", "5_20", "20_50", "gt50")
APPROVAL_POLICIES = ("owner_only", "manager_allowed")
AUTONOMY_LEVELS = ("L1", "L2", "L3")
ONBOARDING_STEPS = ("O1", "O2", "O3", "O4", "O5", "done")
ONBOARDING_PATHS = ("ocr", "manual", "csv", "agency")


class Company(Base):
    """사업장(테넌트 루트). docs/DB_SCHEMA.md §4.1."""

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            f"worker_count_band IN ({','.join(repr(v) for v in WORKER_COUNT_BANDS)})",
            name="ck_companies_worker_count_band",
        ),
        CheckConstraint(
            f"approval_policy IN ({','.join(repr(v) for v in APPROVAL_POLICIES)})",
            name="ck_companies_approval_policy",
        ),
        CheckConstraint(
            f"autonomy_level IN ({','.join(repr(v) for v in AUTONOMY_LEVELS)})",
            name="ck_companies_autonomy_level",
        ),
        CheckConstraint(
            f"onboarding_step IN ({','.join(repr(v) for v in ONBOARDING_STEPS)})",
            name="ck_companies_onboarding_step",
        ),
        CheckConstraint(
            f"onboarding_path IS NULL OR onboarding_path IN ({','.join(repr(v) for v in ONBOARDING_PATHS)})",
            name="ck_companies_onboarding_path",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    business_number: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    worker_count_band: Mapped[str] = mapped_column(Text, nullable=False, server_default="5_20")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Asia/Seoul")
    briefing_time: Mapped[str] = mapped_column(Text, nullable=False, server_default="08:30")
    approval_policy: Mapped[str] = mapped_column(Text, nullable=False, server_default="owner_only")
    autonomy_level: Mapped[str] = mapped_column(Text, nullable=False, server_default="L2")
    onboarding_step: Mapped[str] = mapped_column(Text, nullable=False, server_default="O1")
    onboarding_path: Mapped[str | None] = mapped_column(Text)
    # case_code·판단 기록 번호(#NNNN) 발급 카운터 — docs/DB_SCHEMA.md §9
    case_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    evidence_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workers: Mapped[list["Worker"]] = relationship(back_populates="company")  # noqa: F821
    cases: Mapped[list["Case"]] = relationship(back_populates="company")  # noqa: F821
    memberships: Mapped[list["Membership"]] = relationship(back_populates="company")  # noqa: F821
