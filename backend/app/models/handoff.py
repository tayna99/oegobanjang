"""handoff_packages + package_exports — 행정사 패키지와 내보내기. docs/DB_SCHEMA.md §4.8.

ORM 쿼리 전용 모델 — 컬럼만 매핑한다(FK·CHECK·UNIQUE·Index·relationship 없음).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HandoffPackage(Base):
    __tablename__ = "handoff_packages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    package_type: Mapped[str] = mapped_column(Text, nullable=False)
    masked_payload: Mapped[dict | list] = mapped_column(JSONB, nullable=False)
    included_items: Mapped[dict | list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    approval_id: Mapped[str | None] = mapped_column(Text)
    # R2.6 — 무인증 열람 링크(`/link/:linkToken`) 발급/만료 시각 + 회전 토큰. 셋 다
    # NULL=링크 미발급. link_token은 발급/재발급마다 새로 생성한다(PR #20 P1 리뷰 —
    # case_id는 PK라 불변이라 비밀로 쓸 수 없다).
    link_token: Mapped[str | None] = mapped_column(Text)
    link_issued_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    link_expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PackageExport(Base):
    __tablename__ = "package_exports"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    package_id: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    exported_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_delivery_performed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
