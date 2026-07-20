"""expert_accounts/expert_office_members/expert_grants/expert_login_otps/expert_sessions/
package_view_log/pii_field_policies — 행정사 화이트라벨 v1(R5.1). docs/DB_SCHEMA.md §4.8-1.

ORM 쿼리 전용 모델 — 실제 스키마(FK·CHECK·트리거)는 db/schema.sql 마이그레이션이 만든다.
컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExpertAccount(Base):
    __tablename__ = "expert_accounts"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    office_name: Mapped[str] = mapped_column(Text, nullable=False)
    brand_initial: Mapped[str] = mapped_column(Text, nullable=False)
    brand_color: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    business_registration_no: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExpertOfficeMember(Base):
    __tablename__ = "expert_office_members"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    expert_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    is_office_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExpertGrant(Base):
    __tablename__ = "expert_grants"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="invited")
    expert_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, server_default="package_review")
    granted_by: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False, server_default="processing_agreement")
    from_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    until_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    review_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="365")
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExpertLoginOtp(Base):
    __tablename__ = "expert_login_otps"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExpertSession(Base):
    __tablename__ = "expert_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    expert_office_member_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class PackageViewLog(Base):
    """열람 감사 로그(append-only) — evidence_events와 별도 테이블(spec §6.1/§6.2 목적 분리)."""

    __tablename__ = "package_view_log"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    package_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    expert_office_member_id: Mapped[str] = mapped_column(Text, nullable=False)
    viewed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ip: Mapped[str | None] = mapped_column(Text)


class PiiFieldPolicy(Base):
    """PII 노출 정책 테이블(결정 A의 구현, spec §2.4) — (field, role) 복합 PK."""

    __tablename__ = "pii_field_policies"

    field: Mapped[str] = mapped_column(Text, primary_key=True)
    role: Mapped[str] = mapped_column(Text, primary_key=True)
    exposure: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
