"""notifications — 알림. docs/DB_SCHEMA.md §4.10.

ORM 쿼리 전용 모델 — 컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deeplink_path: Mapped[str] = mapped_column(Text, nullable=False)
    notification_key: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    scheduled_for: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    case_id: Mapped[str | None] = mapped_column(Text)
    run_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # R5.4
