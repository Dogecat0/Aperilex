"""Get Analysis by Accession Number Query for retrieving analysis by filing accession number."""

from dataclasses import dataclass

from src.application.base.query import BaseQuery
from src.domain.value_objects.accession_number import AccessionNumber


@dataclass(frozen=True)
class GetAnalysisByAccessionQuery(BaseQuery):
    """Query to retrieve the latest analysis for a filing by accession number.

    This query fetches the most recent analysis for a filing identified by
    its SEC accession number, including results, confidence scores, and metadata.

    Attributes:
        accession_number: SEC accession number of the filing
        include_full_results: Whether to include complete analysis results
        include_section_details: Whether to include detailed section breakdowns
        include_processing_metadata: Whether to include processing information
    """

    accession_number: AccessionNumber | None = None
    include_full_results: bool = True
    include_section_details: bool = False
    include_processing_metadata: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate required fields
        if self.accession_number is None:
            raise ValueError("accession_number is required")
