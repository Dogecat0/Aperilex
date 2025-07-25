"""Get Analysis Query for retrieving specific analysis details."""

from dataclasses import dataclass
from uuid import UUID

from src.application.base.query import BaseQuery


@dataclass(frozen=True)
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

    analysis_id: UUID | None = None
    include_full_results: bool = True
    include_section_details: bool = False
    include_processing_metadata: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate required fields
        if self.analysis_id is None:
            raise ValueError("analysis_id is required")
