"""create runtime resume outbox checkpoint and metrics tables

Revision ID: 20260509_0007
Revises: 20260509_0006
Create Date: 2026-05-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260509_0007"
down_revision = "20260509_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_actions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_approval_actions_request_id", "approval_actions", ["request_id"])
    op.create_table(
        "delivery_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("outbox_type", sa.String(length=100), nullable=False),
        sa.Column("target_channel", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("blocked_actions_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_delivery_outbox_request_id", "delivery_outbox", ["request_id"])
    op.create_table(
        "agent_checkpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=80), nullable=False),
        sa.Column("resume_token", sa.String(length=180), nullable=False),
        sa.Column("allowed_actions_json", sa.Text(), nullable=False),
        sa.Column("blocked_actions_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_token"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_agent_checkpoints_request_id", "agent_checkpoints", ["request_id"])
    op.create_table(
        "runtime_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("metric_type", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("tool_name", sa.String(length=120), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("token_usage_json", sa.Text(), nullable=False),
        sa.Column("retrieval_count", sa.Integer(), nullable=False),
        sa.Column("blocked_count", sa.Integer(), nullable=False),
        sa.Column("approval_pending_count", sa.Integer(), nullable=False),
        sa.Column("provider_error_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runtime_metrics_request_id", "runtime_metrics", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_runtime_metrics_request_id", table_name="runtime_metrics")
    op.drop_table("runtime_metrics")
    op.drop_index("ix_agent_checkpoints_request_id", table_name="agent_checkpoints")
    op.drop_table("agent_checkpoints")
    op.drop_index("ix_delivery_outbox_request_id", table_name="delivery_outbox")
    op.drop_table("delivery_outbox")
    op.drop_index("ix_approval_actions_request_id", table_name="approval_actions")
    op.drop_table("approval_actions")
