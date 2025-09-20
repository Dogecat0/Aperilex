"""Base query infrastructure for CQRS pattern.

Queries represent read operations that don't change system state. They include
pagination support and schema version metadata.
"""

from abc import ABC

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel


class BaseQuery(SchemaVersionedModel, ABC):  # noqa: B024
    """Base class for all queries in the system.

    Queries are immutable data structures that represent a request for data
    without changing system state. They include pagination support.
    """

    user_id: str | None = Field(
        default=None,
        description="Optional identifier of the user making the query",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number for pagination (1-based)",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
    )

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.page_size
