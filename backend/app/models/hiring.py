from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )
    nationality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    desired_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    available_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
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
