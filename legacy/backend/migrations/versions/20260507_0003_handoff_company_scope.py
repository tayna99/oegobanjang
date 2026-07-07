"""add company scope to handoff package drafts

Revision ID: 20260507_0003
Revises: 20260506_0002
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260507_0003"
down_revision = "20260506_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "handoff_package_drafts",
        sa.Column("company_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_handoff_package_drafts_company_id",
        "handoff_package_drafts",
        ["company_id"],
    )
    op.create_index(
        "ix_handoff_package_drafts_company_status",
        "handoff_package_drafts",
        ["company_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_handoff_package_drafts_company_status",
        table_name="handoff_package_drafts",
    )
    op.drop_index(
        "ix_handoff_package_drafts_company_id",
        table_name="handoff_package_drafts",
    )
    op.drop_column("handoff_package_drafts", "company_id")
