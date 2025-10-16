"""SQLAlchemy model for learning walkthrough bindings."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.enums.learning import (
    LearningReviewStatus,
    LearningWalkthroughArtifactType,
)

from .base import Base


class LearningWalkthroughBinding(Base):
    """Persistence model for walkthrough artifact ↔ lesson bindings."""

    __tablename__ = "learning_walkthrough_bindings"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    walkthrough_section_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    artifact_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    artifact_type: Mapped[LearningWalkthroughArtifactType] = mapped_column(
        Enum(
            LearningWalkthroughArtifactType,
            name="learning_walkthrough_artifact_type",
            create_constraint=True,
        ),
        nullable=False,
    )
    lesson_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    learning_module_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    module_stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    lesson_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[LearningReviewStatus] = mapped_column(
        Enum(
            LearningReviewStatus,
            name="learning_review_status",
            create_constraint=True,
        ),
        nullable=False,
        default=LearningReviewStatus.PENDING,
        server_default=text(f"'{LearningReviewStatus.PENDING.value}'"),
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "walkthrough_section_id",
            "artifact_id",
            "artifact_type",
            name="ux_learning_walkthrough_bindings_artifact",
        ),
    )
