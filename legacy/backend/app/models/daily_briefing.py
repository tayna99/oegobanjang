from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DailyBriefingResultRow(Base):
    __tablename__ = "daily_briefing_results"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingCase(Base):
    __tablename__ = "daily_briefing_cases"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingAction(Base):
    __tablename__ = "daily_briefing_actions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingApproval(Base):
    __tablename__ = "daily_briefing_approvals"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingEvidenceEvent(Base):
    __tablename__ = "daily_briefing_evidence_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class DailyBriefingHandoffPreview(Base):
    __tablename__ = "daily_briefing_handoff_previews"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingDocumentRequestDraft(Base):
    __tablename__ = "daily_briefing_document_request_drafts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingExternalDeliveryJob(Base):
    __tablename__ = "daily_briefing_external_delivery_jobs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    external_send_performed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingHandoffExportArtifact(Base):
    __tablename__ = "daily_briefing_handoff_export_artifacts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(40), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(120), nullable=False)
    external_delivery_performed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingSchedulerRunHistory(Base):
    __tablename__ = "daily_briefing_scheduler_run_history"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    run_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    company_ids: Mapped[str] = mapped_column(Text, nullable=False)
    total_companies: Mapped[str] = mapped_column(String(20), nullable=False)
    succeeded_count: Mapped[str] = mapped_column(String(20), nullable=False)
    failed_count: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class DailyBriefingMetricsSnapshot(Base):
    __tablename__ = "daily_briefing_metrics_snapshots"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    snapshot_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class DailyBriefingPilotFeedback(Base):
    __tablename__ = "daily_briefing_pilot_feedback"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    case_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    feedback_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class DailyBriefingCitationRefreshQueue(Base):
    __tablename__ = "daily_briefing_citation_refresh_queue"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    citation_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingUserCompanyAccess(Base):
    __tablename__ = "daily_briefing_user_company_access"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingCompanySource(Base):
    __tablename__ = "daily_briefing_source_companies"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="Asia/Seoul")
    quota_limit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_foreign_worker_count: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingWorkerSource(Base):
    __tablename__ = "daily_briefing_source_workers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name_masked: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(120), nullable=False)
    visa_expiry_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contract_end_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingCandidateSource(Base):
    __tablename__ = "daily_briefing_source_candidates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name_masked: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingDocumentSource(Base):
    __tablename__ = "daily_briefing_source_documents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingCandidateDocumentSource(Base):
    __tablename__ = "daily_briefing_source_candidate_documents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingReportingEventSource(Base):
    __tablename__ = "daily_briefing_source_reporting_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(40), nullable=False)
    discovered_at: Mapped[str] = mapped_column(String(40), nullable=False)
    reporting_due_date: Mapped[str] = mapped_column(String(20), nullable=False)
    reported_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )


class DailyBriefingCitationSource(Base):
    __tablename__ = "daily_briefing_source_citations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    ingest_at: Mapped[str] = mapped_column(String(40), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    chunk_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retrieved_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )
