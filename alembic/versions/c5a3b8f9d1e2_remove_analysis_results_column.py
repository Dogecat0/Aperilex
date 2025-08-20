"""Remove analysis results column - move to storage

Revision ID: c5a3b8f9d1e2
Revises: 4f48d5eb2b27
Create Date: 2025-08-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5a3b8f9d1e2"
down_revision: str | Sequence[str] | None = "4f48d5eb2b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove the results column from analyses table
    # Results are now stored in external storage (S3/local files)
    op.drop_column("analyses", "results")


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add the results column for rollback
    # Note: This will not restore the actual data that was moved to storage
    op.add_column(
        "analyses",
        sa.Column(
            "results",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
