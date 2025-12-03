"""SQLAlchemy model for Task entity."""

from typing import TYPE_CHECKING, Any
from uuid import UUID as UUIDType

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .identity import User


class Task(Base):
    """Task model for tracking analysis tasks."""

    __tablename__ = "tasks"

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filing_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="tasks",
        lazy="joined",
    )
