"""Prune legacy analysis columns

Revision ID: 8f2c1b4cb4f8
Revises: d6219cf36885
Create Date: 2025-10-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f2c1b4cb4f8"
down_revision: str | Sequence[str] | None = "d6219cf36885"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema by pruning legacy analysis columns."""

    op.execute(
        sa.text(
            """
            UPDATE analyses
            SET meta_data = (
                jsonb_strip_nulls(
                    COALESCE(meta_data::jsonb, '{}'::jsonb) ||
                    jsonb_build_object(
                        'llm_provider', llm_provider,
                        'llm_model', llm_model,
                        'confidence_score', confidence_score,
                        'storage_key', CASE
                            WHEN result IS NOT NULL AND (result::jsonb ? 'storage_key')
                                THEN result::jsonb ->> 'storage_key'
                            ELSE NULL
                        END
                    )
                )
            )::json
            """
        )
    )

    op.execute("DROP INDEX IF EXISTS ix_analyses_confidence_score")

    op.drop_column("analyses", "confidence_score")
    op.drop_column("analyses", "llm_model")
    op.drop_column("analyses", "llm_provider")
    op.drop_column("analyses", "result")


def downgrade() -> None:
    """Recreate legacy columns for downgrade compatibility."""

    op.add_column(
        "analyses",
        sa.Column("result", sa.JSON(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("llm_provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("llm_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analyses_confidence_score ON analyses (confidence_score)"
    )
