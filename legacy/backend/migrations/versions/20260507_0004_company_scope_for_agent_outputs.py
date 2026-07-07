"""add company scope to agent output tables

Revision ID: 20260507_0004
Revises: 20260507_0003
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260507_0004"
down_revision = "20260507_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contact_messages",
        sa.Column("company_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "status_update_candidates",
        sa.Column("company_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evidence_logs",
        sa.Column("company_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_contact_messages_company_id",
        "contact_messages",
        ["company_id"],
    )
    op.create_index(
        "ix_status_update_candidates_company_id",
        "status_update_candidates",
        ["company_id"],
    )
    op.create_index(
        "ix_evidence_logs_company_id",
        "evidence_logs",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_logs_company_id", table_name="evidence_logs")
    op.drop_index(
        "ix_status_update_candidates_company_id",
        table_name="status_update_candidates",
    )
    op.drop_index("ix_contact_messages_company_id", table_name="contact_messages")
    op.drop_column("evidence_logs", "company_id")
    op.drop_column("status_update_candidates", "company_id")
    op.drop_column("contact_messages", "company_id")
