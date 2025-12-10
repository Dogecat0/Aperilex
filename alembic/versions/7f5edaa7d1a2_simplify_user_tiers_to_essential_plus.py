"""Simplify user tiers to ESSENTIAL and PLUS."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f5edaa7d1a2"
down_revision: str | Sequence[str] | None = "6c2ad7f71b9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Map legacy tiers to ESSENTIAL/PLUS and update defaults."""
    connection = op.get_bind()

    connection.execute(
        sa.text(
            "UPDATE users SET tier = 'ESSENTIAL' WHERE tier IN ('BASIC', 'DEMO')"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE users SET tier = 'PLUS' WHERE tier IN ('PROFESSIONAL', 'ENTERPRISE')"
        )
    )

    remaining = connection.execute(
        sa.text("SELECT DISTINCT tier FROM users WHERE tier NOT IN ('ESSENTIAL', 'PLUS')")
    ).fetchall()
    if remaining:
        unknown_values = ", ".join(sorted({row[0] for row in remaining if row[0]}))
        raise RuntimeError(f"Unknown user tiers present after migration: {unknown_values}")

    op.alter_column(
        "users",
        "tier",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'ESSENTIAL'"),
    )


def downgrade() -> None:
    """Revert tier values and defaults to the previous four-tier model."""
    connection = op.get_bind()

    connection.execute(
        sa.text("UPDATE users SET tier = 'BASIC' WHERE tier = 'ESSENTIAL'")
    )
    connection.execute(
        sa.text("UPDATE users SET tier = 'PROFESSIONAL' WHERE tier = 'PLUS'")
    )

    op.alter_column(
        "users",
        "tier",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'BASIC'"),
    )
