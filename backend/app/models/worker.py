from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PREFERRED_LANGUAGES = ("ko", "vi", "id", "en")
WORKER_SOURCES = ("manual", "ocr", "csv", "agency")
WORKER_STATUSES = ("active", "inactive", "left")


class Worker(Base):
    """근로자 — 케이스에 연결되는 프로필(결정 D2). docs/DB_SCHEMA.md §4.2."""

    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint(
            f"preferred_language IS NULL OR preferred_language IN ({','.join(repr(v) for v in PREFERRED_LANGUAGES)})",
            name="ck_workers_preferred_language",
        ),
        CheckConstraint(f"source IN ({','.join(repr(v) for v in WORKER_SOURCES)})", name="ck_workers_source"),
        CheckConstraint(f"status IN ({','.join(repr(v) for v in WORKER_STATUSES)})", name="ck_workers_status"),
        Index("ix_workers_company", "company_id", "status"),
        Index("ix_workers_stay_expiry", "company_id", "stay_expires_at"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)  # "Nguyen Van A"
    nationality: Mapped[str] = mapped_column(Text, nullable=False)  # 무채색 운영 정보로만(차별 금지)
    team: Mapped[str | None] = mapped_column(Text)  # "제조1팀"
    visa_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="E-9")
    stay_expires_at: Mapped[dt.date] = mapped_column(Date, nullable=False)  # D-day 계산의 필수 재료
    contract_ends_at: Mapped[dt.date | None] = mapped_column(Date)  # 있으면 충돌 감지 활성
    contact_channel: Mapped[str | None] = mapped_column(Text)
    preferred_language: Mapped[str | None] = mapped_column(Text)
    registration_no_masked: Mapped[str | None] = mapped_column(Text)  # 원문 컬럼은 존재하지 않음(§7)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="workers")  # noqa: F821
    documents: Mapped[list["WorkerDocument"]] = relationship(back_populates="worker")  # noqa: F821
