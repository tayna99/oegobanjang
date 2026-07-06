from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HandoffPackageDraft(Base):
    __tablename__ = "handoff_package_drafts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    package_type: Mapped[str] = mapped_column(String(80), nullable=False)
    case_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    masked_worker_id: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    handoff_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handoff_blockers: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_json: Mapped[str] = mapped_column(Text, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("approvals.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="PENDING_APPROVAL",
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    transferred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
