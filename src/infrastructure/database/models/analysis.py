from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .filing import Filing


class Analysis(Base):
    """Analysis model for storing LLM analysis results."""

    __tablename__: str = "analyses"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    filing_id: Mapped[UUID] = mapped_column(
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    llm_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    llm_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    filing: Mapped["Filing"] = relationship(
        "Filing",
        back_populates="analyses",
        lazy="joined",
    )
