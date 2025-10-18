"""Add explicit human review flag to quiz attempts."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c2ad7f71b9e"
down_revision: str | Sequence[str] | None = "5a2a8c98d3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add `is_human_reviewed` column and backfill from metadata."""

    op.add_column(
        "quiz_attempts",
        sa.Column(
            "is_human_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.execute(
        """
        UPDATE quiz_attempts
        SET is_human_reviewed = TRUE
        WHERE
            COALESCE("metadata"->>'human_reviewed', '') ILIKE 'true'
            OR COALESCE("metadata"->>'human_reviewed', '') = '1'
            OR UPPER(COALESCE("metadata"->>'review_status', '')) IN ('REVIEWED', 'APPROVED')
        """
    )

    op.alter_column(
        "quiz_attempts",
        "is_human_reviewed",
        server_default=None,
    )


def downgrade() -> None:
    """Remove `is_human_reviewed` flag."""

    op.drop_column("quiz_attempts", "is_human_reviewed")
