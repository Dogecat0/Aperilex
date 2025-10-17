"""Add learning walkthrough bindings table."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a2a8c98d3f4"
down_revision: str | Sequence[str] | None = "0a0e8e0b1c42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

learning_review_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="learning_review_status",
    create_type=False,
)
learning_artifact_type = postgresql.ENUM(
    "HIGHLIGHT",
    "COMPREHENSION_CHECK",
    name="learning_walkthrough_artifact_type",
    create_type=False,
)


def upgrade() -> None:
    """Create learning walkthrough bindings table."""

    bind = op.get_bind()
    learning_review_status.create(bind, checkfirst=True)
    learning_artifact_type.create(bind, checkfirst=True)

    op.create_table(
        "learning_walkthrough_bindings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "walkthrough_section_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "artifact_type",
            learning_artifact_type,
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "learning_module_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "module_stage",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "lesson_title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            learning_review_status,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "last_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "walkthrough_section_id",
            "artifact_id",
            "artifact_type",
            name="ux_learning_walkthrough_bindings_artifact",
        ),
    )
    op.create_index(
        "ix_learning_walkthrough_bindings_walkthrough_section_id",
        "learning_walkthrough_bindings",
        ["walkthrough_section_id"],
    )
    op.create_index(
        "ix_learning_walkthrough_bindings_lesson_id",
        "learning_walkthrough_bindings",
        ["lesson_id"],
    )
    op.create_index(
        "ix_learning_walkthrough_bindings_learning_module_key",
        "learning_walkthrough_bindings",
        ["learning_module_key"],
    )


def downgrade() -> None:
    """Drop learning walkthrough bindings table."""

    op.drop_index(
        "ix_learning_walkthrough_bindings_learning_module_key",
        table_name="learning_walkthrough_bindings",
    )
    op.drop_index(
        "ix_learning_walkthrough_bindings_lesson_id",
        table_name="learning_walkthrough_bindings",
    )
    op.drop_index(
        "ix_learning_walkthrough_bindings_walkthrough_section_id",
        table_name="learning_walkthrough_bindings",
    )
    op.drop_table("learning_walkthrough_bindings")

    bind = op.get_bind()
    learning_artifact_type.drop(bind, checkfirst=True)
    learning_review_status.drop(bind, checkfirst=True)
