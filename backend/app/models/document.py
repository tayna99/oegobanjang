from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

WORKER_DOCUMENT_STATUSES = ("missing", "requested", "received", "expiring", "company_check", "pending")


class DocumentRequirement(Base):
    """필수 서류 정의(전역 참조 — company_id 없음). docs/DB_SCHEMA.md §4.2."""

    __tablename__ = "document_requirements"
    __table_args__ = (
        UniqueConstraint("case_type", "visa_type", "required_doc", name="ux_document_requirements_key"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_type: Mapped[str] = mapped_column(Text, nullable=False)
    visa_type: Mapped[str] = mapped_column(Text, nullable=False)
    required_doc: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="ck_document_requirements_required"), nullable=False, server_default="1"
    )
    citation_id: Mapped[str | None] = mapped_column(Text, ForeignKey("citations.id"))  # "왜 필요한지" 근거
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WorkerDocument(Base):
    """근로자 서류 상태. docs/DB_SCHEMA.md §4.2."""

    __tablename__ = "worker_documents"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({','.join(repr(v) for v in WORKER_DOCUMENT_STATUSES)})",
            name="ck_worker_documents_status",
        ),
        UniqueConstraint("worker_id", "doc_type", name="ux_worker_documents_worker_doc_type"),
        Index("ix_worker_documents_company", "company_id", "status"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    worker_id: Mapped[str] = mapped_column(Text, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="missing")
    due_date: Mapped[dt.date | None] = mapped_column(Date)
    expires_at: Mapped[dt.date | None] = mapped_column(Date)
    file_ref: Mapped[str | None] = mapped_column(Text)  # 암호화 저장소 키(경로 원문 아님)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    worker: Mapped["Worker"] = relationship(back_populates="documents")  # noqa: F821
