"""create handoff package draft table

Revision ID: 20260506_0002
Revises: 20260505_0001
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_0002"
down_revision = "20260505_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "handoff_package_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("package_type", sa.String(length=80), nullable=False),
        sa.Column("case_type", sa.String(length=80), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("masked_worker_id", sa.String(length=80), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=True),
        sa.Column("handoff_ready", sa.Boolean(), nullable=False),
        sa.Column("handoff_blockers", sa.Text(), nullable=True),
        sa.Column("package_json", sa.Text(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_handoff_package_drafts_request_id",
        "handoff_package_drafts",
        ["request_id"],
    )
    op.create_index(
        "ix_handoff_package_drafts_worker_id",
        "handoff_package_drafts",
        ["worker_id"],
    )
    op.create_index(
        "ix_handoff_package_drafts_approval_id",
        "handoff_package_drafts",
        ["approval_id"],
    )
    op.create_index(
        "ix_handoff_package_drafts_status",
        "handoff_package_drafts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_handoff_package_drafts_status", table_name="handoff_package_drafts")
    op.drop_index("ix_handoff_package_drafts_approval_id", table_name="handoff_package_drafts")
    op.drop_index("ix_handoff_package_drafts_worker_id", table_name="handoff_package_drafts")
    op.drop_index("ix_handoff_package_drafts_request_id", table_name="handoff_package_drafts")
    op.drop_table("handoff_package_drafts")
