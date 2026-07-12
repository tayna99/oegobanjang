from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CITATION_GRADES = ("A", "B", "C", "E", "F")  # F=합성 데이터 — 근거 사용 불가(§5.3)
CITATION_STATUSES = ("official", "review_needed", "stale", "internal")
CASE_CITATION_ACTORS = ("agent", "rule", "user")


class Citation(Base):
    """근거 라이브러리(중앙 스토어). company_id NULL = 전역 공식 근거. docs/DB_SCHEMA.md §4.4."""

    __tablename__ = "citations"
    __table_args__ = (
        CheckConstraint(f"grade IN ({','.join(repr(v) for v in CITATION_GRADES)})", name="ck_citations_grade"),
        CheckConstraint(f"status IN ({','.join(repr(v) for v in CITATION_STATUSES)})", name="ck_citations_status"),
        Index("ix_citations_status", "status", "grade"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 'cit_001' 표시 코드 = PK(전역 시퀀스)
    company_id: Mapped[str | None] = mapped_column(Text, ForeignKey("companies.id"))
    grade: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[dt.date | None] = mapped_column(Date)
    ingest_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chroma_collection: Mapped[str | None] = mapped_column(Text)  # Chroma 청크 포인터(메타데이터 미러링만)
    chroma_document_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    case_links: Mapped[list["CaseCitation"]] = relationship(back_populates="citation")


class CaseCitation(Base):
    """케이스↔근거 연결. docs/DB_SCHEMA.md §4.3."""

    __tablename__ = "case_citations"
    __table_args__ = (
        CheckConstraint(
            f"added_by_actor IN ({','.join(repr(v) for v in CASE_CITATION_ACTORS)})",
            name="ck_case_citations_added_by_actor",
        ),
        Index("ix_case_citations_citation", "citation_id"),
    )

    case_id: Mapped[str] = mapped_column(
        Text, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    citation_id: Mapped[str] = mapped_column(Text, ForeignKey("citations.id"), primary_key=True)
    added_by_actor: Mapped[str] = mapped_column(Text, nullable=False)
    added_by_run_id: Mapped[str | None] = mapped_column(Text, ForeignKey("runs.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    citation: Mapped["Citation"] = relationship(back_populates="case_links")
    case: Mapped["Case"] = relationship(back_populates="citation_links")  # noqa: F821
