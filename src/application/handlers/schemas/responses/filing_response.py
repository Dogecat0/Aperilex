"""Filing Response DTO for application layer results."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel
from src.domain.entities.filing import Filing
from src.domain.value_objects.processing_status import ProcessingStatus


class FilingResponse(SchemaVersionedModel):
    """Response DTO for filing information.

    This DTO provides a structured representation of filing data optimized
    for application layer consumption, including processing status and metadata.

    Attributes:
        filing_id: Unique identifier for the filing
        company_id: ID of the company that filed
        accession_number: SEC accession number
        filing_type: Type of SEC filing (10-K, 10-Q, etc.)
        filing_date: Date the filing was submitted to SEC
        processing_status: Current processing status in analysis pipeline
        processing_error: Error message if processing failed
        metadata: Additional filing metadata
        analyses_count: Number of analyses performed on this filing (optional)
        latest_analysis_date: Date of most recent analysis (optional)
    """

    filing_id: UUID = Field(description="Unique identifier for the filing")
    company_id: UUID = Field(description="Identifier of the company that filed")
    accession_number: str = Field(
        description="SEC accession number for the filing"
    )
    filing_type: str = Field(description="Type of SEC filing")
    filing_date: date = Field(description="Date the filing was submitted")
    processing_status: ProcessingStatus = Field(
        description="Current processing status in analysis pipeline",
    )
    processing_error: str | None = Field(
        default=None, description="Error message if processing failed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional filing metadata",
    )
    analyses_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of analyses performed on this filing",
    )
    latest_analysis_date: date | None = Field(
        default=None,
        description="Date of most recent analysis",
    )

    @classmethod
    def from_domain(
        cls,
        filing: Filing,
        analyses_count: int | None = None,
        latest_analysis_date: date | None = None,
    ) -> "FilingResponse":
        """Create FilingResponse from domain Filing entity.

        Args:
            filing: Domain Filing entity
            analyses_count: Optional count of analyses for this filing
            latest_analysis_date: Optional date of latest analysis

        Returns:
            FilingResponse with data from domain entity
        """
        return cls(
            filing_id=filing.id,
            company_id=filing.company_id,
            accession_number=str(filing.accession_number),
            filing_type=filing.filing_type.value,
            filing_date=filing.filing_date,
            processing_status=filing.processing_status,
            processing_error=filing.processing_error,
            metadata=filing.metadata,
            analyses_count=analyses_count,
            latest_analysis_date=latest_analysis_date,
        )

    @classmethod
    def from_model(
        cls,
        model: Any,  # FilingModel type
        analyses_count: int | None = None,
        latest_analysis_date: date | None = None,
    ) -> "FilingResponse":
        """Create FilingResponse from database model.

        Args:
            model: Database Filing model
            analyses_count: Optional count of analyses for this filing
            latest_analysis_date: Optional date of latest analysis

        Returns:
            FilingResponse with data from database model
        """
        return cls(
            filing_id=model.id,
            company_id=model.company_id,
            accession_number=model.accession_number,
            filing_type=model.filing_type,
            filing_date=model.filing_date,
            processing_status=ProcessingStatus(model.processing_status),
            processing_error=model.processing_error,
            metadata=model.meta_data or {},
            analyses_count=analyses_count,
            latest_analysis_date=latest_analysis_date,
        )

    @property
    def is_processed(self) -> bool:
        """Check if filing has been successfully processed.

        Returns:
            True if processing status is COMPLETED
        """
        return self.processing_status is ProcessingStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if filing processing failed.

        Returns:
            True if processing status is FAILED
        """
        return self.processing_status is ProcessingStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Check if filing is currently being processed.

        Returns:
            True if processing status is PROCESSING
        """
        return self.processing_status is ProcessingStatus.PROCESSING

    @property
    def is_pending(self) -> bool:
        """Check if filing is pending processing.

        Returns:
            True if processing status is PENDING
        """
        return self.processing_status is ProcessingStatus.PENDING

    @property
    def has_analyses(self) -> bool:
        """Check if filing has associated analyses.

        Returns:
            True if analyses_count > 0
        """
        return self.analyses_count is not None and self.analyses_count > 0

    def get_display_name(self) -> str:
        """Get a human-readable display name for the filing.

        Returns:
            String combining filing type and accession number
        """
        return f"{self.filing_type} - {self.accession_number}"

    def get_status_display(self) -> str:
        """Get a human-readable status description.

        Returns:
            Formatted status description with error info if applicable
        """
        status_map = {
            ProcessingStatus.PENDING: "Pending Processing",
            ProcessingStatus.PROCESSING: "Processing",
            ProcessingStatus.COMPLETED: "Completed",
            ProcessingStatus.FAILED: "Failed",
        }

        base_status = status_map.get(
            self.processing_status, self.processing_status.value
        )

        if self.is_failed and self.processing_error:
            return f"{base_status}: {self.processing_error}"

        return base_status
