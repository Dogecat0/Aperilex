"""Get Filing Query for retrieving specific filing details."""

from dataclasses import dataclass
from uuid import UUID

from src.application.base.query import BaseQuery


@dataclass(frozen=True)
class GetFilingQuery(BaseQuery):
    """Query to retrieve a specific filing by ID.

    This query fetches detailed information about a single filing,
    including its processing status, metadata, and associated analyses.

    Attributes:
        filing_id: UUID of the filing to retrieve
        include_analyses: Whether to include associated analysis results
        include_content_metadata: Whether to include filing content metadata
    """

    filing_id: UUID | None = None
    include_analyses: bool = False
    include_content_metadata: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate required fields
        if self.filing_id is None:
            raise ValueError("filing_id is required")
