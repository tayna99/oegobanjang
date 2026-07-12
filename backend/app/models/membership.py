from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ROLES = ("owner", "manager", "viewer", "expert")
MEMBERSHIP_STATUSES = ("invited", "active", "removed")


class Membership(Base):
    """회사↔사용자 역할(테넌트 단위 부여). docs/DB_SCHEMA.md §4.1."""

    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint(f"role IN ({','.join(repr(v) for v in ROLES)})", name="ck_memberships_role"),
        CheckConstraint(
            f"status IN ({','.join(repr(v) for v in MEMBERSHIP_STATUSES)})", name="ck_memberships_status"
        ),
        UniqueConstraint("company_id", "user_id", name="ux_memberships_company_user"),
        Index("ix_memberships_company", "company_id", "role"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))  # 초대 수락 전 NULL
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    invite_phone: Mapped[str | None] = mapped_column(Text)
    invite_token: Mapped[str | None] = mapped_column(Text, unique=True)
    invite_expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # 만료 7일(3단계 §6)
    invited_by: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="memberships")  # noqa: F821
