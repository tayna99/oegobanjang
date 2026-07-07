"""create agent runtime state snapshots

Revision ID: 20260509_0005
Revises: 20260507_0004
Create Date: 2026-05-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260509_0005"
down_revision = "20260507_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runtime_state_snapshots",
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=False),
        sa.Column("structured_response_json", sa.Text(), nullable=False),
        sa.Column("evidence_events_json", sa.Text(), nullable=False),
        sa.Column("approval_json", sa.Text(), nullable=False),
        sa.Column("interrupt_metadata_json", sa.Text(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index(
        "ix_agent_runtime_state_snapshots_company_id",
        "agent_runtime_state_snapshots",
        ["company_id"],
    )
    op.create_index(
        "ix_agent_runtime_state_snapshots_user_id",
        "agent_runtime_state_snapshots",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_runtime_state_snapshots_user_id",
        table_name="agent_runtime_state_snapshots",
    )
    op.drop_index(
        "ix_agent_runtime_state_snapshots_company_id",
        table_name="agent_runtime_state_snapshots",
    )
    op.drop_table("agent_runtime_state_snapshots")
