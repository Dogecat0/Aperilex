"""Filing entity for processing status tracking.

This entity focuses on tracking the processing status of SEC filings.
All detailed filing data should be retrieved directly from edgartools.
"""

from datetime import date
from typing import Any
from uuid import UUID

from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus


class Filing:
    """Filing entity for processing status tracking.

    This entity tracks the processing status of SEC filings in our analysis
    pipeline. For detailed filing content and metadata, use edgartools directly.

    Attributes:
        id: Unique identifier for the filing in our system
        company_id: Reference to the company that filed
        accession_number: SEC accession number for unique identification
        filing_type: Type of filing (10-K, 10-Q, etc.)
        filing_date: Date filing was submitted to SEC
        processing_status: Current processing status in our pipeline
        processing_error: Error message if processing failed
        metadata: Additional metadata for processing context
    """

    def __init__(
        self,
        id: UUID,
        company_id: UUID,
        accession_number: AccessionNumber,
        filing_type: FilingType,
        filing_date: date,
        processing_status: ProcessingStatus = ProcessingStatus.PENDING,
        processing_error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a Filing entity.

        Args:
            id: Unique identifier for the filing
            company_id: ID of the company that filed
            accession_number: SEC accession number
            filing_type: Type of filing (10-K, 10-Q, etc.)
            filing_date: Date filing was submitted
            processing_status: Current processing status
            processing_error: Error message if processing failed
            metadata: Additional processing metadata
        """
        self._id = id
        self._company_id = company_id
        self._accession_number = accession_number
        self._filing_type = filing_type
        self._filing_date = filing_date
        self._processing_status = processing_status
        self._processing_error = processing_error
        self._metadata = metadata or {}

        self._validate_invariants()

    @property
    def id(self) -> UUID:
        """Get filing ID."""
        return self._id

    @property
    def company_id(self) -> UUID:
        """Get company ID."""
        return self._company_id

    @property
    def accession_number(self) -> AccessionNumber:
        """Get accession number."""
        return self._accession_number

    @property
    def filing_type(self) -> FilingType:
        """Get filing type."""
        return self._filing_type

    @property
    def filing_date(self) -> date:
        """Get filing date."""
        return self._filing_date

    @property
    def processing_status(self) -> ProcessingStatus:
        """Get processing status."""
        return self._processing_status

    @property
    def processing_error(self) -> str | None:
        """Get processing error message."""
        return self._processing_error

    @property
    def metadata(self) -> dict[str, Any]:
        """Get filing metadata."""
        return self._metadata.copy()

    def mark_as_processing(self) -> None:
        """Mark filing as currently being processed."""
        if not self._processing_status.can_transition_to(ProcessingStatus.PROCESSING):
            raise ValueError(
                f"Cannot transition from {self._processing_status} to PROCESSING"
            )
        self._processing_status = ProcessingStatus.PROCESSING
        self._processing_error = None

    def mark_as_completed(self) -> None:
        """Mark filing as successfully processed."""
        if not self._processing_status.can_transition_to(ProcessingStatus.COMPLETED):
            raise ValueError(
                f"Cannot transition from {self._processing_status} to COMPLETED"
            )
        self._processing_status = ProcessingStatus.COMPLETED
        self._processing_error = None

    def mark_as_failed(self, error: str) -> None:
        """Mark filing as failed with error message.

        Args:
            error: Error message describing the failure

        Raises:
            ValueError: If error message is empty or invalid transition
        """
        if not error or not error.strip():
            raise ValueError("Error message cannot be empty")

        if not self._processing_status.can_transition_to(ProcessingStatus.FAILED):
            raise ValueError(
                f"Cannot transition from {self._processing_status} to FAILED"
            )

        self._processing_status = ProcessingStatus.FAILED
        self._processing_error = error.strip()

    def reset_for_retry(self) -> None:
        """Reset processing status to pending for retry."""
        self._processing_status = ProcessingStatus.PENDING
        self._processing_error = None

    def can_be_processed(self) -> bool:
        """Check if filing can be processed.

        Returns:
            True if filing is in a state that allows processing
        """
        return self._processing_status in [
            ProcessingStatus.PENDING,
            ProcessingStatus.FAILED,
        ]

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata entry.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def _validate_invariants(self) -> None:
        """Validate domain invariants."""
        if self._processing_error and self._processing_status != ProcessingStatus.FAILED:
            raise ValueError("Processing error can only be set when status is FAILED")

    def __eq__(self, other: object) -> bool:
        """Check equality based on accession number."""
        if not isinstance(other, Filing):
            return False
        return self._accession_number == other._accession_number

    def __hash__(self) -> int:
        """Hash based on accession number."""
        return hash(self._accession_number)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Filing: {self._filing_type} [{self._accession_number}] "
            f"({self._processing_status})"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Filing(id={self._id}, accession_number={self._accession_number}, "
            f"type={self._filing_type}, status={self._processing_status})"
        )
