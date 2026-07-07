"""add daily briefing persistence tables

Revision ID: 20260508_0005
Revises: 20260507_0004
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260508_0005"
down_revision = "20260507_0004"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "daily_briefing_results",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("date", sa.String(length=20), nullable=False),
        sa.Column("source_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_results_company_id", "daily_briefing_results", ["company_id"])
    op.create_index("ix_daily_briefing_results_date", "daily_briefing_results", ["date"])

    op.create_table(
        "daily_briefing_cases",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("risk_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_cases_company_id", "daily_briefing_cases", ["company_id"])

    op.create_table(
        "daily_briefing_actions",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_actions_case_id", "daily_briefing_actions", ["case_id"])
    op.create_index("ix_daily_briefing_actions_company_id", "daily_briefing_actions", ["company_id"])

    op.create_table(
        "daily_briefing_approvals",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_approvals_action_id", "daily_briefing_approvals", ["action_id"])
    op.create_index("ix_daily_briefing_approvals_case_id", "daily_briefing_approvals", ["case_id"])
    op.create_index("ix_daily_briefing_approvals_company_id", "daily_briefing_approvals", ["company_id"])

    op.create_table(
        "daily_briefing_evidence_events",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=True),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_briefing_evidence_events_case_id", "daily_briefing_evidence_events", ["case_id"])
    op.create_index("ix_daily_briefing_evidence_events_company_id", "daily_briefing_evidence_events", ["company_id"])

    op.create_table(
        "daily_briefing_handoff_previews",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_handoff_previews_action_id", "daily_briefing_handoff_previews", ["action_id"])
    op.create_index("ix_daily_briefing_handoff_previews_case_id", "daily_briefing_handoff_previews", ["case_id"])
    op.create_index("ix_daily_briefing_handoff_previews_company_id", "daily_briefing_handoff_previews", ["company_id"])

    op.create_table(
        "daily_briefing_document_request_drafts",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_document_request_drafts_action_id", "daily_briefing_document_request_drafts", ["action_id"])
    op.create_index("ix_daily_briefing_document_request_drafts_case_id", "daily_briefing_document_request_drafts", ["case_id"])
    op.create_index("ix_daily_briefing_document_request_drafts_company_id", "daily_briefing_document_request_drafts", ["company_id"])
    op.create_index("ix_daily_briefing_document_request_drafts_worker_id", "daily_briefing_document_request_drafts", ["worker_id"])

    op.create_table(
        "daily_briefing_external_delivery_jobs",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("external_send_performed", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_external_delivery_jobs_action_id", "daily_briefing_external_delivery_jobs", ["action_id"])
    op.create_index("ix_daily_briefing_external_delivery_jobs_case_id", "daily_briefing_external_delivery_jobs", ["case_id"])
    op.create_index("ix_daily_briefing_external_delivery_jobs_company_id", "daily_briefing_external_delivery_jobs", ["company_id"])

    op.create_table(
        "daily_briefing_handoff_export_artifacts",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("case_id", sa.String(length=120), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=40), nullable=False),
        sa.Column("content_hash", sa.String(length=120), nullable=False),
        sa.Column("external_delivery_performed", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_handoff_export_artifacts_action_id", "daily_briefing_handoff_export_artifacts", ["action_id"])
    op.create_index("ix_daily_briefing_handoff_export_artifacts_case_id", "daily_briefing_handoff_export_artifacts", ["case_id"])
    op.create_index("ix_daily_briefing_handoff_export_artifacts_company_id", "daily_briefing_handoff_export_artifacts", ["company_id"])

    op.create_table(
        "daily_briefing_scheduler_run_history",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("run_date", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("company_ids", sa.Text(), nullable=False),
        sa.Column("total_companies", sa.String(length=20), nullable=False),
        sa.Column("succeeded_count", sa.String(length=20), nullable=False),
        sa.Column("failed_count", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_briefing_scheduler_run_history_run_date", "daily_briefing_scheduler_run_history", ["run_date"])

    op.create_table(
        "daily_briefing_metrics_snapshots",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_date", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_briefing_metrics_snapshots_company_id", "daily_briefing_metrics_snapshots", ["company_id"])
    op.create_index("ix_daily_briefing_metrics_snapshots_snapshot_date", "daily_briefing_metrics_snapshots", ["snapshot_date"])

    op.create_table(
        "daily_briefing_pilot_feedback",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=120), nullable=True),
        sa.Column("feedback_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_briefing_pilot_feedback_company_id", "daily_briefing_pilot_feedback", ["company_id"])
    op.create_index("ix_daily_briefing_pilot_feedback_case_id", "daily_briefing_pilot_feedback", ["case_id"])

    op.create_table(
        "daily_briefing_citation_refresh_queue",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("citation_id", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_citation_refresh_queue_citation_id", "daily_briefing_citation_refresh_queue", ["citation_id"])
    op.create_index("ix_daily_briefing_citation_refresh_queue_status", "daily_briefing_citation_refresh_queue", ["status"])

    op.create_table(
        "daily_briefing_user_company_access",
        sa.Column("id", sa.String(length=160), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_user_company_access_user_id", "daily_briefing_user_company_access", ["user_id"])
    op.create_index("ix_daily_briefing_user_company_access_company_id", "daily_briefing_user_company_access", ["company_id"])

    op.create_table(
        "daily_briefing_source_companies",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("quota_limit", sa.String(length=20), nullable=True),
        sa.Column("current_foreign_worker_count", sa.String(length=20), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "daily_briefing_source_workers",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("display_name_masked", sa.String(length=120), nullable=False),
        sa.Column("raw_name", sa.String(length=120), nullable=False),
        sa.Column("visa_expiry_date", sa.String(length=20), nullable=True),
        sa.Column("contract_end_date", sa.String(length=20), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_source_workers_company_id", "daily_briefing_source_workers", ["company_id"])

    op.create_table(
        "daily_briefing_source_candidates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("display_name_masked", sa.String(length=120), nullable=False),
        sa.Column("raw_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_source_candidates_company_id", "daily_briefing_source_candidates", ["company_id"])

    op.create_table(
        "daily_briefing_source_documents",
        sa.Column("id", sa.String(length=160), primary_key=True),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("due_date", sa.String(length=20), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_source_documents_worker_id", "daily_briefing_source_documents", ["worker_id"])

    op.create_table(
        "daily_briefing_source_candidate_documents",
        sa.Column("id", sa.String(length=160), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("due_date", sa.String(length=20), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_source_candidate_documents_candidate_id", "daily_briefing_source_candidate_documents", ["candidate_id"])

    op.create_table(
        "daily_briefing_source_reporting_events",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("occurred_at", sa.String(length=40), nullable=False),
        sa.Column("discovered_at", sa.String(length=40), nullable=False),
        sa.Column("reporting_due_date", sa.String(length=20), nullable=False),
        sa.Column("reported_at", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_daily_briefing_source_reporting_events_company_id", "daily_briefing_source_reporting_events", ["company_id"])
    op.create_index("ix_daily_briefing_source_reporting_events_worker_id", "daily_briefing_source_reporting_events", ["worker_id"])

    op.create_table(
        "daily_briefing_source_citations",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("ingest_at", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=120), nullable=True),
        sa.Column("chunk_id", sa.String(length=120), nullable=True),
        sa.Column("chunk_version", sa.String(length=80), nullable=True),
        sa.Column("retrieved_at", sa.String(length=40), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("daily_briefing_source_citations")
    op.drop_index("ix_daily_briefing_source_reporting_events_worker_id", table_name="daily_briefing_source_reporting_events")
    op.drop_index("ix_daily_briefing_source_reporting_events_company_id", table_name="daily_briefing_source_reporting_events")
    op.drop_table("daily_briefing_source_reporting_events")
    op.drop_index("ix_daily_briefing_source_candidate_documents_candidate_id", table_name="daily_briefing_source_candidate_documents")
    op.drop_table("daily_briefing_source_candidate_documents")
    op.drop_index("ix_daily_briefing_source_documents_worker_id", table_name="daily_briefing_source_documents")
    op.drop_table("daily_briefing_source_documents")
    op.drop_index("ix_daily_briefing_source_candidates_company_id", table_name="daily_briefing_source_candidates")
    op.drop_table("daily_briefing_source_candidates")
    op.drop_index("ix_daily_briefing_source_workers_company_id", table_name="daily_briefing_source_workers")
    op.drop_table("daily_briefing_source_workers")
    op.drop_table("daily_briefing_source_companies")
    op.drop_index("ix_daily_briefing_document_request_drafts_worker_id", table_name="daily_briefing_document_request_drafts")
    op.drop_index("ix_daily_briefing_document_request_drafts_company_id", table_name="daily_briefing_document_request_drafts")
    op.drop_index("ix_daily_briefing_document_request_drafts_case_id", table_name="daily_briefing_document_request_drafts")
    op.drop_index("ix_daily_briefing_document_request_drafts_action_id", table_name="daily_briefing_document_request_drafts")
    op.drop_table("daily_briefing_document_request_drafts")
    op.drop_index("ix_daily_briefing_external_delivery_jobs_company_id", table_name="daily_briefing_external_delivery_jobs")
    op.drop_index("ix_daily_briefing_external_delivery_jobs_case_id", table_name="daily_briefing_external_delivery_jobs")
    op.drop_index("ix_daily_briefing_external_delivery_jobs_action_id", table_name="daily_briefing_external_delivery_jobs")
    op.drop_table("daily_briefing_external_delivery_jobs")
    op.drop_index("ix_daily_briefing_handoff_export_artifacts_company_id", table_name="daily_briefing_handoff_export_artifacts")
    op.drop_index("ix_daily_briefing_handoff_export_artifacts_case_id", table_name="daily_briefing_handoff_export_artifacts")
    op.drop_index("ix_daily_briefing_handoff_export_artifacts_action_id", table_name="daily_briefing_handoff_export_artifacts")
    op.drop_table("daily_briefing_handoff_export_artifacts")
    op.drop_index("ix_daily_briefing_citation_refresh_queue_status", table_name="daily_briefing_citation_refresh_queue")
    op.drop_index("ix_daily_briefing_citation_refresh_queue_citation_id", table_name="daily_briefing_citation_refresh_queue")
    op.drop_table("daily_briefing_citation_refresh_queue")
    op.drop_index("ix_daily_briefing_pilot_feedback_case_id", table_name="daily_briefing_pilot_feedback")
    op.drop_index("ix_daily_briefing_pilot_feedback_company_id", table_name="daily_briefing_pilot_feedback")
    op.drop_table("daily_briefing_pilot_feedback")
    op.drop_index("ix_daily_briefing_metrics_snapshots_snapshot_date", table_name="daily_briefing_metrics_snapshots")
    op.drop_index("ix_daily_briefing_metrics_snapshots_company_id", table_name="daily_briefing_metrics_snapshots")
    op.drop_table("daily_briefing_metrics_snapshots")
    op.drop_index("ix_daily_briefing_scheduler_run_history_run_date", table_name="daily_briefing_scheduler_run_history")
    op.drop_table("daily_briefing_scheduler_run_history")
    op.drop_index("ix_daily_briefing_user_company_access_company_id", table_name="daily_briefing_user_company_access")
    op.drop_index("ix_daily_briefing_user_company_access_user_id", table_name="daily_briefing_user_company_access")
    op.drop_table("daily_briefing_user_company_access")
    op.drop_index("ix_daily_briefing_handoff_previews_company_id", table_name="daily_briefing_handoff_previews")
    op.drop_index("ix_daily_briefing_handoff_previews_case_id", table_name="daily_briefing_handoff_previews")
    op.drop_index("ix_daily_briefing_handoff_previews_action_id", table_name="daily_briefing_handoff_previews")
    op.drop_table("daily_briefing_handoff_previews")
    op.drop_index("ix_daily_briefing_evidence_events_company_id", table_name="daily_briefing_evidence_events")
    op.drop_index("ix_daily_briefing_evidence_events_case_id", table_name="daily_briefing_evidence_events")
    op.drop_table("daily_briefing_evidence_events")
    op.drop_index("ix_daily_briefing_approvals_company_id", table_name="daily_briefing_approvals")
    op.drop_index("ix_daily_briefing_approvals_case_id", table_name="daily_briefing_approvals")
    op.drop_index("ix_daily_briefing_approvals_action_id", table_name="daily_briefing_approvals")
    op.drop_table("daily_briefing_approvals")
    op.drop_index("ix_daily_briefing_actions_company_id", table_name="daily_briefing_actions")
    op.drop_index("ix_daily_briefing_actions_case_id", table_name="daily_briefing_actions")
    op.drop_table("daily_briefing_actions")
    op.drop_index("ix_daily_briefing_cases_company_id", table_name="daily_briefing_cases")
    op.drop_table("daily_briefing_cases")
    op.drop_index("ix_daily_briefing_results_date", table_name="daily_briefing_results")
    op.drop_index("ix_daily_briefing_results_company_id", table_name="daily_briefing_results")
    op.drop_table("daily_briefing_results")
