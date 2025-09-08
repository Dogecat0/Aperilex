from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .analysis import Analysis
from .base import Base
from .company import Company


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
