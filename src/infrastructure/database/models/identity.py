"""SQLAlchemy models for user identity and learning artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.enums import UserStatus, UserTier

from .base import Base

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .analysis import Analysis
    from .auth import AuthRateLimit, AuthSession
    from .task import Task


class User(Base):
    """Core user account record."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserStatus.ACTIVE.value,
        server_default=text("'ACTIVE'"),
    )
    tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserTier.BASIC.value,
        server_default=text("'BASIC'"),
    )

    identities: Mapped[list[UserIdentity]] = relationship(
        "UserIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    learning_progress: Mapped[list[LearningProgress]] = relationship(
        "LearningProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    quiz_attempts: Mapped[list[QuizAttempt]] = relationship(
        "QuizAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    analyses: Mapped[list[Analysis]] = relationship(
        "Analysis",
        back_populates="user",
        lazy="noload",
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="user",
        lazy="noload",
    )
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    auth_rate_limits: Mapped[list[AuthRateLimit]] = relationship(
        "AuthRateLimit",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserIdentity(Base):
    """External identity mapping for a user."""

    __tablename__ = "user_identities"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="ux_user_identities_provider_subject",
        ),
    )

    user: Mapped[User] = relationship("User", back_populates="identities")


class UserProfile(Base):
    """User profile preferences and personalization."""

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    time_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="profile")


class LearningProgress(Base):
    """Tracks a learner's progress within a module."""

    __tablename__ = "learning_progress"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "module_key",
            name="ux_learning_progress_user_module",
        ),
    )

    user: Mapped[User] = relationship("User", back_populates="learning_progress")


class QuizAttempt(Base):
    """Stores quiz attempt outcomes for learning modules."""

    __tablename__ = "quiz_attempts"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quiz_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    correct_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    score_percent: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_human_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    responses: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    user: Mapped[User] = relationship("User", back_populates="quiz_attempts")
