"""approvals — 외부 발송의 유일한 관문. docs/DB_SCHEMA.md §4.3.

ORM 쿼리 전용 모델 — 컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    requested_by_actor: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_user_id: Mapped[str | None] = mapped_column(Text)
    decided_by_user_id: Mapped[str | None] = mapped_column(Text)
    on_behalf_of_user_id: Mapped[str | None] = mapped_column(Text)
    identity_method: Mapped[str | None] = mapped_column(Text)
    checklist: Mapped[dict | list | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
