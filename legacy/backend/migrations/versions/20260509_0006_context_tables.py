"""create runtime context tables

Revision ID: 20260509_0006
Revises: 20260509_0005
Create Date: 2026-05-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260509_0006"
down_revision = "20260509_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("business_number", sa.String(length=40), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("current_foreign_workers", sa.Integer(), nullable=False),
        sa.Column("housing_available", sa.Boolean(), nullable=False),
        sa.Column("shift_type", sa.String(length=120), nullable=True),
        sa.Column("requested_role", sa.String(length=120), nullable=True),
        sa.Column("preferred_start_date", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("nationality", sa.String(length=80), nullable=True),
        sa.Column("preferred_language", sa.String(length=16), nullable=True),
        sa.Column("visa_type", sa.String(length=20), nullable=True),
        sa.Column("visa_expires_at", sa.String(length=40), nullable=True),
        sa.Column("contract_starts_at", sa.String(length=40), nullable=True),
        sa.Column("contract_ends_at", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workers_company_id", "workers", ["company_id"])
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("nationality", sa.String(length=40), nullable=True),
        sa.Column("desired_role", sa.String(length=120), nullable=True),
        sa.Column("available_from", sa.String(length=40), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("passport", sa.Boolean(), nullable=False),
        sa.Column("photo", sa.Boolean(), nullable=False),
        sa.Column("health_check", sa.Boolean(), nullable=False),
        sa.Column("understood_housing", sa.Boolean(), nullable=False),
        sa.Column("understood_shift", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidates_company_id", "candidates", ["company_id"])
    op.create_table(
        "worker_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("doc_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.String(length=40), nullable=True),
        sa.Column("reviewed_at", sa.String(length=40), nullable=True),
        sa.Column("expires_at", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_documents_company_id", "worker_documents", ["company_id"])
    op.create_index("ix_worker_documents_worker_id", "worker_documents", ["worker_id"])
    op.create_table(
        "document_requirements",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("case_type", sa.String(length=80), nullable=False),
        sa.Column("visa_type", sa.String(length=20), nullable=False),
        sa.Column("required_doc", sa.String(length=120), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_requirements_case_type", "document_requirements", ["case_type"])
    op.create_index("ix_document_requirements_visa_type", "document_requirements", ["visa_type"])


def downgrade() -> None:
    op.drop_index("ix_document_requirements_visa_type", table_name="document_requirements")
    op.drop_index("ix_document_requirements_case_type", table_name="document_requirements")
    op.drop_table("document_requirements")
    op.drop_index("ix_worker_documents_worker_id", table_name="worker_documents")
    op.drop_index("ix_worker_documents_company_id", table_name="worker_documents")
    op.drop_table("worker_documents")
    op.drop_index("ix_candidates_company_id", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index("ix_workers_company_id", table_name="workers")
    op.drop_table("workers")
    op.drop_table("companies")
    op.drop_table("users")
