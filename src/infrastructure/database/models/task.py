"""SQLAlchemy model for Task entity."""

from typing import Any
from uuid import UUID as UUIDType

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Task(Base):
    """Task model for tracking analysis tasks."""

    __tablename__ = "tasks"

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    filing_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
