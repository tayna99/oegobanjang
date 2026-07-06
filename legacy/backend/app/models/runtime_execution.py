from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalAction(Base):
    __tablename__ = "approval_actions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id"),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        unique=True,
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DeliveryOutbox(Base):
    __tablename__ = "delivery_outbox"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id"),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    outbox_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_channel: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    idempotency_key: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        unique=True,
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    blocked_actions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class AgentCheckpoint(Base):
    __tablename__ = "agent_checkpoints"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id"),
        nullable=False,
    )
    checkpoint_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resume_token: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    allowed_actions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    blocked_actions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        unique=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class RuntimeMetric(Base):
    __tablename__ = "runtime_metrics"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(80), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    retrieval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
    )
