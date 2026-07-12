from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

APPROVAL_STATUSES = ("pending", "approved", "rejected", "cancelled")
APPROVAL_REQUESTED_BY_ACTORS = ("agent", "rule", "user")
APPROVAL_IDENTITY_METHODS = ("pin", "biometric")


class Approval(Base):
    """승인 — 외부 발송의 유일한 관문. 다형 참조 없음(항상 케이스 액션 대상). docs/DB_SCHEMA.md §4.3."""

    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(f"status IN ({','.join(repr(v) for v in APPROVAL_STATUSES)})", name="ck_approvals_status"),
        CheckConstraint(
            f"requested_by_actor IN ({','.join(repr(v) for v in APPROVAL_REQUESTED_BY_ACTORS)})",
            name="ck_approvals_requested_by_actor",
        ),
        CheckConstraint(
            f"identity_method IS NULL OR identity_method IN ({','.join(repr(v) for v in APPROVAL_IDENTITY_METHODS)})",
            name="ck_approvals_identity_method",
        ),
        CheckConstraint("checklist IS NULL OR json_valid(checklist)", name="ck_approvals_checklist_json"),
        Index("ix_approvals_company_status", "company_id", "status"),
        Index("ix_approvals_case", "case_id"),
        # 액션당 살아있는 승인 요청은 1건 — 일괄 승인 테이블·컬럼은 만들지 않는다(GOTCHAS §3)
        Index("ux_approvals_one_pending", "action_id", unique=True, sqlite_where=text("status = 'pending'")),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(Text, ForeignKey("cases.id"), nullable=False)
    action_id: Mapped[str] = mapped_column(Text, ForeignKey("next_actions.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    # 중복 승인 차단(GOTCHAS §2). nullable — requestApproval() 시점엔 아직 결정 키가 없다
    # (decide()에서만 채워짐). NULL은 UNIQUE와 충돌하지 않아 pending 승인이 여러 건이어도
    # 안전하다(docs/DB_SCHEMA.md §4.3, 2026-07-12 API 구현 중 발견·정정).
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)
    requested_by_actor: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    decided_by_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    on_behalf_of_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))  # 대리 승인 위임자
    identity_method: Mapped[str | None] = mapped_column(Text)  # 승인 본인확인 수단
    checklist: Mapped[dict | list | None] = mapped_column(JSON)  # M2.6 §2c 4항목
    reason: Mapped[str | None] = mapped_column(Text)  # 반려 사유 — 서비스 계층 PII 패턴 차단
    requested_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    case: Mapped["Case"] = relationship()  # noqa: F821
