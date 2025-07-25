"""Get Filing by Accession Number Query for retrieving specific filing details."""

from dataclasses import dataclass

from src.application.base.query import BaseQuery
from src.domain.value_objects.accession_number import AccessionNumber


@dataclass(frozen=True)
class GetFilingByAccessionQuery(BaseQuery):
    """Query to retrieve a specific filing by accession number.

    This query fetches detailed information about a single filing using its
    SEC accession number, including its processing status, metadata, and
    associated analyses.

    Attributes:
        accession_number: SEC accession number of the filing to retrieve
        include_analyses: Whether to include associated analysis results
        include_content_metadata: Whether to include filing content metadata
    """

    accession_number: AccessionNumber | None = None
    include_analyses: bool = False
    include_content_metadata: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate required fields
        if self.accession_number is None:
            raise ValueError("accession_number is required")
