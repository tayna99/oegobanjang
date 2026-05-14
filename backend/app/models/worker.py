from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(80), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    visa_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    visa_expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contract_starts_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contract_ends_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
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
