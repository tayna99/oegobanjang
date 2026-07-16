"""companies — 사업장(테넌트 루트). docs/DB_SCHEMA.md §4.1.

ORM 쿼리 전용 모델 — 실제 스키마(FK·CHECK·트리거·뷰)는 db/schema.sql 마이그레이션이 만든다.
컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    business_number: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    worker_count_band: Mapped[str] = mapped_column(Text, nullable=False, server_default="5_20")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Asia/Seoul")
    briefing_time: Mapped[str] = mapped_column(Text, nullable=False, server_default="08:30")
    approval_policy: Mapped[str] = mapped_column(Text, nullable=False, server_default="owner_only")
    autonomy_level: Mapped[str] = mapped_column(Text, nullable=False, server_default="L2")
    onboarding_step: Mapped[str] = mapped_column(Text, nullable=False, server_default="O1")
    onboarding_path: Mapped[str | None] = mapped_column(Text)
    case_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    evidence_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
