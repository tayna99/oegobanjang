from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


if __name__ == "backend.app.models.worker":
    sys.modules.setdefault("app.models.worker", sys.modules[__name__])
elif __name__ == "app.models.worker":
    sys.modules.setdefault("backend.app.models.worker", sys.modules[__name__])


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
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_channel: Mapped[str | None] = mapped_column(String(40), nullable=True, default="email")
    visa_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    visa_expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contract_starts_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contract_ends_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    worker_type: Mapped[str] = mapped_column(String(40), nullable=False, default="foreign_worker")
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
