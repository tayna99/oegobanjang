"""citations + case_citations — 근거 라이브러리와 케이스 연결. docs/DB_SCHEMA.md §4.2·§4.3.

ORM 쿼리 전용 모델 — 컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[dt.date | None] = mapped_column(Date)
    ingest_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chroma_collection: Mapped[str | None] = mapped_column(Text)
    chroma_document_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CaseCitation(Base):
    __tablename__ = "case_citations"

    company_id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(Text, primary_key=True)
    citation_id: Mapped[str] = mapped_column(Text, primary_key=True)
    added_by_actor: Mapped[str] = mapped_column(Text, nullable=False)
    added_by_run_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
