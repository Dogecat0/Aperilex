"""Align analysis schema and add performance indexes

Revision ID: 1b7dc9a0872e
Revises: c5a3b8f9d1e2
Create Date: 2025-09-24 20:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b7dc9a0872e"
down_revision: str | Sequence[str] | None = "c5a3b8f9d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to align with latest models."""
    connection = op.get_bind()

    # --- analyses table updates ---
    op.add_column(
        "analyses",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("result", sa.JSON(), nullable=True),
    )

    # Backfill new columns from existing data
    connection.execute(
        sa.text(
            "UPDATE analyses SET user_id = created_by::uuid WHERE created_by IS NOT NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET user_id = '00000000-0000-0000-0000-000000000000'::uuid "
            "WHERE user_id IS NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET status = 'COMPLETED' WHERE status IS NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET status = COALESCE(meta_data->>'status', status)"
            " WHERE meta_data IS NOT NULL AND meta_data->>'status' IS NOT NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET result = meta_data->'result'"
            " WHERE meta_data IS NOT NULL AND meta_data->'result' IS NOT NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET meta_data = (meta_data::jsonb - 'status')::json"
            " WHERE meta_data IS NOT NULL AND (meta_data::jsonb ? 'status')"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE analyses SET meta_data = (meta_data::jsonb - 'result')::json"
            " WHERE meta_data IS NOT NULL AND (meta_data::jsonb ? 'result')"
        )
    )

    # Enforce non-null constraints after backfill
    op.alter_column(
        "analyses",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "analyses",
        "status",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=None,
    )

    # Allow nullable provider/model fields to reflect optional metadata
    op.alter_column(
        "analyses",
        "llm_provider",
        existing_type=sa.String(length=50),
        nullable=True,
    )
    op.alter_column(
        "analyses",
        "llm_model",
        existing_type=sa.String(length=100),
        nullable=True,
    )

    # Create compound indexes to speed up common queries
    op.create_index(
        "ix_analyses_filing_analysis_type_created_at",
        "analyses",
        ["filing_id", "analysis_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_analyses_user_status_created_at",
        "analyses",
        ["user_id", "status", "created_at"],
        unique=False,
    )

    # --- filings table index ---
    op.create_index(
        "ix_filings_company_type_date",
        "filings",
        ["company_id", "filing_type", "filing_date"],
        unique=False,
    )

    # --- companies ticker unique index ---
    op.create_index(
        "ux_companies_ticker",
        "companies",
        [sa.text("(meta_data->>'ticker')")],
        unique=True,
        postgresql_where=sa.text("(meta_data->>'ticker') IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema changes."""
    # Drop added indexes
    op.drop_index("ux_companies_ticker", table_name="companies")
    op.drop_index("ix_filings_company_type_date", table_name="filings")
    op.drop_index("ix_analyses_user_status_created_at", table_name="analyses")
    op.drop_index("ix_analyses_filing_analysis_type_created_at", table_name="analyses")

    # Revert nullable changes
    op.alter_column(
        "analyses",
        "llm_model",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "analyses",
        "llm_provider",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    # Remove added columns
    op.drop_column("analyses", "result")
    op.drop_column("analyses", "status")
    op.drop_column("analyses", "user_id")
