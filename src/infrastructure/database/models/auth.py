"""SQLAlchemy models supporting authentication tokens and rate limits."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base import Base


class AuthSession(Base):
    """Persisted authentication session for refresh token lifecycle."""

    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        unique=True,
    )
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    session_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="auth_sessions",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "session_key",
            name="ux_auth_sessions_user_session_key",
        ),
    )


class AuthRateLimit(Base):
    """Tracks rate limiting stubs for authentication workflows."""

    __tablename__ = "auth_rate_limits"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="auth_rate_limits",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("key", "action", name="ux_auth_rate_limits_key_action"),
    )
