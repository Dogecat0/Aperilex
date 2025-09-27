"""add_analysis_summary_column

Revision ID: d6219cf36885
Revises: 1b7dc9a0872e
Create Date: 2025-09-27 21:20:09.840797

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd6219cf36885'
down_revision: str | Sequence[str] | None = '1b7dc9a0872e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "analyses",
        sa.Column("summary", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("analyses", "summary")
