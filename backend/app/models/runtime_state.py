from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


RUNTIME_STATE_TARGET_TYPE = "agent_runtime_state_snapshot"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentRuntimeStateSnapshot(Base):
    __tablename__ = "agent_runtime_state_snapshots"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    final_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    structured_response_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_events_json: Mapped[str] = mapped_column(Text, nullable=False)
    approval_json: Mapped[str] = mapped_column(Text, nullable=False)
    interrupt_metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
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
