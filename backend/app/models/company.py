from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


if __name__ == "backend.app.models.company":
    sys.modules.setdefault("app.models.company", sys.modules[__name__])
elif __name__ == "app.models.company":
    sys.modules.setdefault("backend.app.models.company", sys.modules[__name__])


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    current_foreign_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    housing_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shift_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requested_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_start_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
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
