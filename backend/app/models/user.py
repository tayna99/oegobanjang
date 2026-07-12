from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """사용자(휴대폰 로그인). docs/DB_SCHEMA.md §4.1."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    phone: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # 로그인 식별자. PII — 표시 시 마스킹
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    pin_hash: Mapped[str | None] = mapped_column(Text)  # 승인 본인확인 PIN(7단계 §4) — 해시만
    biometric_registered: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="ck_users_biometric_registered"), nullable=False, server_default="0"
    )
    terms_agreed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
