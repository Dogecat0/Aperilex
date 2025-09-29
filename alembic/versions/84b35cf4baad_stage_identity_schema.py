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

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_tier", "users", ["tier"])

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

    op.create_table(
        "learning_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("module_key", sa.String(length=128), nullable=False),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_interaction_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
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
            "user_id",
            "module_key",
            name="ux_learning_progress_user_module",
        ),
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("quiz_id", sa.String(length=128), nullable=False),
        sa.Column(
            "question_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "correct_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "score_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "passed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("responses", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
    )

    op.create_index(
        "ix_learning_progress_user_id",
        "learning_progress",
        ["user_id"],
    )
    op.create_index(
        "ix_learning_progress_module_key",
        "learning_progress",
        ["module_key"],
    )
    op.create_index(
        "ix_quiz_attempts_user_id",
        "quiz_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_quiz_attempts_quiz_id",
        "quiz_attempts",
        ["quiz_id"],
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "analyses" in inspector.get_table_names():
        existing_fks = {
            fk["name"] for fk in inspector.get_foreign_keys("analyses")
        }
        if "fk_analyses_user_id_users" not in existing_fks:
            op.create_foreign_key(
                "fk_analyses_user_id_users",
                "analyses",
                "users",
                ["user_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    if "tasks" in inspector.get_table_names():
        existing_fks = {
            fk["name"] for fk in inspector.get_foreign_keys("tasks")
        }
        if "fk_tasks_user_id_users" not in existing_fks:
            op.create_foreign_key(
                "fk_tasks_user_id_users",
                "tasks",
                "users",
                ["user_id"],
                ["id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tasks" in inspector.get_table_names():
        fk_names = {
            fk["name"] for fk in inspector.get_foreign_keys("tasks")
        }
        if "fk_tasks_user_id_users" in fk_names:
            op.drop_constraint("fk_tasks_user_id_users", "tasks", type_="foreignkey")

    if "analyses" in inspector.get_table_names():
        fk_names = {
            fk["name"] for fk in inspector.get_foreign_keys("analyses")
        }
        if "fk_analyses_user_id_users" in fk_names:
            op.drop_constraint(
                "fk_analyses_user_id_users", "analyses", type_="foreignkey"
            )

    op.drop_index(
        "ix_quiz_attempts_quiz_id", table_name="quiz_attempts"
    )
    op.drop_index(
        "ix_quiz_attempts_user_id", table_name="quiz_attempts"
    )
    op.drop_table("quiz_attempts")

    op.drop_index(
        "ix_learning_progress_module_key",
        table_name="learning_progress",
    )
    op.drop_index(
        "ix_learning_progress_user_id", table_name="learning_progress"
    )
    op.drop_table("learning_progress")

    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_profiles")
    op.drop_table("user_identities")
    op.drop_index("ix_users_tier", table_name="users")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
