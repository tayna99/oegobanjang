"""threads + thread_messages — 컨택 스레드와 메시지. docs/DB_SCHEMA.md §4.7.

ORM 쿼리 전용 모델 — 컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    last_message_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ThreadMessage(Base):
    __tablename__ = "thread_messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    draft_id: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(Text)
    body_original: Mapped[str | None] = mapped_column(Text)
    body_ko: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # R3 stage ② — 응답 링크(MESSAGING_CHANNELS.md §3). direction='system' 발신 메시지에만 채워진다.
    response_token: Mapped[str | None] = mapped_column(Text)
    response_token_expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
