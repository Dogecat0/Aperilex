"""Paginated Response DTO for paginated result sets."""

from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

# Generic type for the items in the paginated response
T = TypeVar('T')


@dataclass(frozen=True)
class PaginationMetadata:
    """Metadata for pagination information.

    Attributes:
        page: Current page number (1-based)
        page_size: Number of items per page
        total_items: Total number of items across all pages
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
        next_page: Next page number (if available)
        previous_page: Previous page number (if available)
    """

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: int | None
    previous_page: int | None

    @classmethod
    def create(
        cls, page: int, page_size: int, total_items: int
    ) -> "PaginationMetadata":
        """Create pagination metadata from basic parameters.

        Args:
            page: Current page number (1-based)
            page_size: Items per page
            total_items: Total number of items

        Returns:
            PaginationMetadata with calculated values
        """
        total_pages = (
            (total_items + page_size - 1) // page_size if total_items > 0 else 0
        )
        has_next = page < total_pages
        has_previous = page > 1
        next_page = page + 1 if has_next else None
        previous_page = page - 1 if has_previous else None

        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            next_page=next_page,
            previous_page=previous_page,
        )


@dataclass(frozen=True)
class PaginatedResponse[T]:
    """Generic paginated response DTO.

    This DTO wraps a list of items with pagination metadata, providing
    a consistent structure for paginated API responses.

    Attributes:
        items: List of items for the current page
        pagination: Pagination metadata
        query_id: ID of the query that generated this response (for caching)
        filters_applied: Summary of filters that were applied
    """

    items: list[T]
    pagination: PaginationMetadata
    query_id: UUID | None = None
    filters_applied: str | None = None

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int,
        query_id: UUID | None = None,
        filters_applied: str | None = None,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response from items and pagination parameters.

        Args:
            items: List of items for current page
            page: Current page number (1-based)
            page_size: Items per page
            total_items: Total number of items across all pages
            query_id: Optional query ID for tracking
            filters_applied: Optional summary of applied filters

        Returns:
            PaginatedResponse with items and pagination metadata
        """
        pagination = PaginationMetadata.create(page, page_size, total_items)

        return cls(
            items=items,
            pagination=pagination,
            query_id=query_id,
            filters_applied=filters_applied,
        )

    @classmethod
    def empty(
        cls,
        page: int = 1,
        page_size: int = 20,
        query_id: UUID | None = None,
        filters_applied: str | None = None,
    ) -> "PaginatedResponse[T]":
        """Create an empty paginated response.

        Args:
            page: Current page number
            page_size: Items per page
            query_id: Optional query ID for tracking
            filters_applied: Optional summary of applied filters

        Returns:
            Empty PaginatedResponse
        """
        return cls.create(
            items=[],
            page=page,
            page_size=page_size,
            total_items=0,
            query_id=query_id,
            filters_applied=filters_applied,
        )

    @property
    def is_empty(self) -> bool:
        """Check if the response contains no items.

        Returns:
            True if items list is empty
        """
        return len(self.items) == 0

    @property
    def item_count(self) -> int:
        """Get the number of items in the current page.

        Returns:
            Number of items in current page
        """
        return len(self.items)

    @property
    def is_first_page(self) -> bool:
        """Check if this is the first page.

        Returns:
            True if current page is 1
        """
        return self.pagination.page == 1

    @property
    def is_last_page(self) -> bool:
        """Check if this is the last page.

        Returns:
            True if this is the last page
        """
        return not self.pagination.has_next

    @property
    def start_item_number(self) -> int:
        """Get the starting item number for this page (1-based).

        Returns:
            Starting item number
        """
        if self.is_empty:
            return 0
        return (self.pagination.page - 1) * self.pagination.page_size + 1

    @property
    def end_item_number(self) -> int:
        """Get the ending item number for this page (1-based).

        Returns:
            Ending item number
        """
        if self.is_empty:
            return 0
        return self.start_item_number + self.item_count - 1

    def get_page_summary(self) -> str:
        """Get a human-readable summary of the current page.

        Returns:
            String describing current page position
        """
        if self.is_empty:
            return "No items found"

        if self.pagination.total_items <= self.pagination.page_size:
            return f"Showing all {self.pagination.total_items} items"

        return (
            f"Showing {self.start_item_number}-{self.end_item_number} "
            f"of {self.pagination.total_items} items "
            f"(page {self.pagination.page} of {self.pagination.total_pages})"
        )

    def get_navigation_info(self) -> dict[str, int | None]:
        """Get navigation information for building pagination controls.

        Returns:
            Dictionary with navigation page numbers
        """
        return {
            "first_page": 1 if self.pagination.total_pages > 0 else None,
            "previous_page": self.pagination.previous_page,
            "current_page": self.pagination.page,
            "next_page": self.pagination.next_page,
            "last_page": (
                self.pagination.total_pages if self.pagination.total_pages > 0 else None
            ),
        }

    # Convenience properties for accessing pagination metadata directly
    @property
    def page(self) -> int:
        """Get current page number."""
        return self.pagination.page

    @property
    def page_size(self) -> int:
        """Get page size."""
        return self.pagination.page_size

    @property
    def total_items(self) -> int:
        """Get total number of items."""
        return self.pagination.total_items

    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return self.pagination.total_pages

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.pagination.has_next

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.pagination.has_previous
