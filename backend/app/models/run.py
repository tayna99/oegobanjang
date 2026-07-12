from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

RUN_STARTED_BY = ("user", "event")
RUN_AUTONOMY = ("low", "medium", "high")
RUN_STATUSES = ("queued", "running", "waiting_question", "waiting_approval", "completed", "failed", "cancelled")
RUN_STEP_KINDS = ("thinking", "tool_call", "guardrail", "handoff", "replan")  # 공식 5종(GLOSSARY)
RUN_STEP_TOOL_STATUSES = ("running", "done", "failed", "blocked")


class Run(Base):
    """에이전트 런(툴콜링 루프 1회). docs/DB_SCHEMA.md §4.6."""

    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(f"started_by IN ({','.join(repr(v) for v in RUN_STARTED_BY)})", name="ck_runs_started_by"),
        CheckConstraint(f"autonomy IN ({','.join(repr(v) for v in RUN_AUTONOMY)})", name="ck_runs_autonomy"),
        CheckConstraint(f"status IN ({','.join(repr(v) for v in RUN_STATUSES)})", name="ck_runs_status"),
        CheckConstraint("question IS NULL OR json_valid(question)", name="ck_runs_question_json"),
        Index("ix_runs_company", "company_id", "status"),
        Index("ix_runs_case", "case_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    company_id: Mapped[str] = mapped_column(Text, ForeignKey("companies.id"), nullable=False)
    case_id: Mapped[str | None] = mapped_column(Text, ForeignKey("cases.id"))  # 커맨드 런 초기엔 NULL 가능
    started_by: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_event: Mapped[str | None] = mapped_column(Text)  # "D-30 진입" 등
    started_by_user_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    autonomy: Mapped[str] = mapped_column(Text, nullable=False, server_default="medium")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    goal_text: Mapped[str | None] = mapped_column(Text)  # 사용자 명령(저장 전 PII 스크럽)
    question: Mapped[dict | list | None] = mapped_column(JSON)  # interrupt QuestionCard
    result_summary: Mapped[str | None] = mapped_column(Text)
    anchor_event_no: Mapped[int | None] = mapped_column(Integer)  # "런 1건 = 판단 기록 # 1건"(§9)
    parent_run_id: Mapped[str | None] = mapped_column(Text, ForeignKey("runs.id"))
    priority_hint: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    steps: Mapped[list["RunStep"]] = relationship(back_populates="run", order_by="RunStep.seq")


class RunStep(Base):
    """런 스텝(스트리밍 타임라인의 정본). 가드레일 스텝은 숨기지 않고 저장. docs/DB_SCHEMA.md §4.6."""

    __tablename__ = "run_steps"
    __table_args__ = (
        CheckConstraint(f"kind IN ({','.join(repr(v) for v in RUN_STEP_KINDS)})", name="ck_run_steps_kind"),
        CheckConstraint(
            f"tool_status IS NULL OR tool_status IN ({','.join(repr(v) for v in RUN_STEP_TOOL_STATUSES)})",
            name="ck_run_steps_tool_status",
        ),
        UniqueConstraint("run_id", "seq", name="ux_run_steps_run_seq"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 표시 순서
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)  # 한국어 표시 라벨
    detail: Mapped[str | None] = mapped_column(Text)  # 마스킹된 상세
    tool_name: Mapped[str | None] = mapped_column(Text)
    tool_status: Mapped[str | None] = mapped_column(Text)
    handoff_from: Mapped[str | None] = mapped_column(Text)
    handoff_to: Mapped[str | None] = mapped_column(Text)
    payload_hash: Mapped[str | None] = mapped_column(Text)  # 입출력 해시(원문 미저장)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run: Mapped["Run"] = relationship(back_populates="steps")
