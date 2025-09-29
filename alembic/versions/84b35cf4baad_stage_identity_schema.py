"""stage identity schema

Revision ID: 84b35cf4baad
Revises: 909acfb8d771
Create Date: 2025-09-29 19:45:23.730594

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '84b35cf4baad'
down_revision: str | Sequence[str] | None = '909acfb8d771'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column(
            "tier",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'BASIC'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="ux_users_email"),
    )

    op.create_table(
        "user_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column("raw_profile", sa.JSON(), nullable=True),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_subject",
            name="ux_user_identities_provider_subject",
        ),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("time_zone", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", name="ux_user_profiles_user_id"),
    )

    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_profiles")
    op.drop_table("user_identities")
    op.drop_table("users")
