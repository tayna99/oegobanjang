"""create langchain agent checkpoint metadata table

Revision ID: 20260509_0008
Revises: 20260509_0007
Create Date: 2026-05-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260509_0008"
down_revision = "20260509_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "langchain_agent_checkpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=180), nullable=False),
        sa.Column("checkpoint_ns", sa.String(length=120), nullable=False),
        sa.Column("latest_checkpoint_id", sa.String(length=180), nullable=True),
        sa.Column("interrupt_id", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("resume_blocked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_langchain_agent_checkpoints_thread_id",
        "langchain_agent_checkpoints",
        ["thread_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_langchain_agent_checkpoints_thread_id",
        table_name="langchain_agent_checkpoints",
    )
    op.drop_table("langchain_agent_checkpoints")
