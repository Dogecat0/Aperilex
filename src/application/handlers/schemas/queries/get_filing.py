"""Get Filing Query for retrieving specific filing details."""

from uuid import UUID

from pydantic import Field, model_validator

from src.application.base.query import BaseQuery


class GetFilingQuery(BaseQuery):
    """Query to retrieve a specific filing by ID.

    This query fetches detailed information about a single filing,
    including its processing status, metadata, and associated analyses.

    Attributes:
        filing_id: UUID of the filing to retrieve
        include_analyses: Whether to include associated analysis results
        include_content_metadata: Whether to include filing content metadata
    """

    filing_id: UUID | None = Field(
        default=None,
        description="UUID of the filing to retrieve",
    )
    include_analyses: bool = Field(
        default=False,
        description="Whether to include associated analysis results",
    )
    include_content_metadata: bool = Field(
        default=False,
        description="Whether to include filing content metadata",
    )

    @model_validator(mode="after")
    def _validate(self) -> "GetFilingQuery":
        """Validate required query parameters."""
        if self.filing_id is None:
            raise ValueError("filing_id is required")
        return self
