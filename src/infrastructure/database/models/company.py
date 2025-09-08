from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .filing import Filing


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
