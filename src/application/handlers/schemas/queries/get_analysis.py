"""Get Analysis Query for retrieving specific analysis details."""

from uuid import UUID

from pydantic import Field, model_validator

from src.application.base.query import BaseQuery


class GetAnalysisQuery(BaseQuery):
    """Query to retrieve a specific analysis by ID.

    This query fetches detailed information about a single analysis,
    including its results, confidence scores, and metadata.

    Attributes:
        analysis_id: UUID of the analysis to retrieve
        include_full_results: Whether to include complete analysis results
        include_section_details: Whether to include detailed section breakdowns
        include_processing_metadata: Whether to include processing information
    """

    analysis_id: UUID | None = Field(
        default=None,
        description="UUID of the analysis to retrieve",
    )
    include_full_results: bool = Field(
        default=True,
        description="Whether to include complete analysis results",
    )
    include_section_details: bool = Field(
        default=False,
        description="Whether to include detailed section breakdowns",
    )
    include_processing_metadata: bool = Field(
        default=False,
        description="Whether to include processing metadata",
    )

    @model_validator(mode="after")
    def _validate(self) -> "GetAnalysisQuery":
        """Validate required query parameters."""
        if self.analysis_id is None:
            raise ValueError("analysis_id is required")
        return self
