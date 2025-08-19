from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base


class Company(Base):
    """Company model for storing company reference data."""

    __tablename__: str = "companies"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    cik: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Relationships
    filings: Mapped[list["Filing"]] = relationship(
        "Filing",
        back_populates="company",
        lazy="select",
    )


class Filing(Base):
    """Filing model for tracking SEC filing processing status."""

    __tablename__: str = "filings"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    accession_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    filing_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )
    filing_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="filings",
        lazy="joined",
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis",
        back_populates="filing",
        lazy="select",
        cascade="all, delete-orphan",
    )


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
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    llm_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    llm_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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
