from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    desired_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    available_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    visa_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="E-9")
    arrival_due_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_workplace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    visa_issuance_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pre_entry_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    passport: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    health_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    understood_housing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    understood_shift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class CandidatePreEntryPackage(Base):
    __tablename__ = "candidate_pre_entry_packages"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )
