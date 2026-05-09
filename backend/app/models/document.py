from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkerDocument(Base):
    __tablename__ = "worker_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )
    worker_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workers.id"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="MISSING")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    visa_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    required_doc: Mapped[str] = mapped_column(String(120), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
