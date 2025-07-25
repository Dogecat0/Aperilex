"""Base query infrastructure for CQRS pattern.

Queries represent read operations that don't change system state. They include
pagination support.
"""

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseQuery(ABC):  # noqa: B024
    """Base class for all queries in the system.

    Queries are immutable data structures that represent a request for data
    without changing system state. They include pagination support.

    Attributes:
        user_id: Optional identifier of the user making the query
        page: Page number for pagination (1-based)
        page_size: Number of items per page
    """

    user_id: str | None = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.page_size
