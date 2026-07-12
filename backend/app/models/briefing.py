from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Briefing(Base):
    """일일 브리핑 실행(레거시 PRD §11 계약 승계). docs/DB_SCHEMA.md §4.9."""

    __tablename__ = "briefings"
    __table_args__ = (UniqueConstraint("company_id", "briefing_date", name="ux_briefings_company_date"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    briefing_date: Mapped[dt.date] = mapped_column(Date, nullable=False)  # 회사 timezone 기준
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # non-PII 운영 필드만으로 계산(§4.9) — 같으면 재실행 시 동일 결과, 다르면 같은 행 갱신
    source_snapshot_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rerun_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_refreshed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["BriefingItem"]] = relationship(back_populates="briefing", order_by="BriefingItem.rank")


class BriefingItem(Base):
    """브리핑 카드 구성. docs/DB_SCHEMA.md §4.9."""

    __tablename__ = "briefing_items"
    __table_args__ = (UniqueConstraint("briefing_id", "case_id", name="ux_briefing_items_briefing_case"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    briefing_id: Mapped[str] = mapped_column(Text, ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[str] = mapped_column(Text, ForeignKey("cases.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 발행 시점 정렬 스냅샷(hero=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    briefing: Mapped["Briefing"] = relationship(back_populates="items")
