"""
Database record models for domain entities.

These models represent the data structures used for database operations,
providing type safety and schema versioning for future compatibility.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    TaskPriority,
    TaskStatus,
)
from src.shared.types import (
    CIK,
    AnalysisId,
    CompanyId,
    FilingId,
    TaskId,
    Ticker,
    UserId,
)

from .base import MetadataDict


class TaskRecord(BaseModel):
    """
    Database record for task entity.

    Tracks task queue state management, worker assignment,
    retry logic, and error handling.
    """

    schema_version: int = Field(
        default=1, description="Schema version for compatibility"
    )

    # Core identifiers
    task_id: TaskId = Field(description="Unique task identifier")
    user_id: UserId = Field(description="User who created the task")
    filing_id: FilingId = Field(description="Associated filing ID")

    # Task state
    status: TaskStatus = Field(description="Current task status")
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL, description="Task priority level"
    )

    # Processing metadata
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: str | None = Field(default=None, description="Last error message")
    worker_id: str | None = Field(default=None, description="Assigned worker ID")

    # Additional metadata
    metadata: MetadataDict = Field(default_factory=dict, description="Task metadata")

    # Timestamps
    created_at: datetime = Field(description="Task creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    started_at: datetime | None = Field(
        default=None, description="Processing start time"
    )
    completed_at: datetime | None = Field(default=None, description="Completion time")


class AnalysisRecord(BaseModel):
    """
    Database record for analysis entity.

    Stores analysis metadata and results reference, tracks LLM provider
    and model, captures token usage and processing metrics.
    """

    schema_version: int = Field(
        default=1, description="Schema version for compatibility"
    )

    # Core identifiers
    analysis_id: AnalysisId = Field(description="Unique analysis identifier")
    filing_id: FilingId = Field(description="Associated filing ID")
    user_id: UserId = Field(description="User who requested analysis")

    # Analysis details
    status: AnalysisStatus = Field(description="Current analysis status")
    analysis_type: AnalysisType = Field(description="Type of analysis performed")

    # Results (stored in storage, this is reference/cache)
    result: dict[str, Any] | None = Field(
        default=None, description="Analysis results (reference to storage)"
    )
    storage_key: str | None = Field(
        default=None, description="Storage location for full results"
    )

    # LLM information
    llm_provider: str | None = Field(default=None, description="LLM provider used")
    llm_model: str | None = Field(default=None, description="Specific model used")
    confidence_score: float | None = Field(
        default=None, description="Confidence in results (0.0 to 1.0)"
    )

    # Processing metrics
    token_count: int | None = Field(default=None, description="Total tokens used")
    processing_time_ms: int | None = Field(
        default=None, description="Processing time in milliseconds"
    )
    cost: float | None = Field(default=None, description="Cost of analysis")

    # Metadata
    created_by: str | None = Field(
        default=None, description="Identifier of who initiated the analysis"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional analysis metadata"
    )

    # Timestamps
    created_at: datetime = Field(description="Analysis creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class FilingRecord(BaseModel):
    """
    Database record for filing entity.

    Tracks all fetched filings, links to storage location,
    includes checksum for integrity and manages timestamps.
    """

    schema_version: int = Field(
        default=1, description="Schema version for compatibility"
    )

    # Core identifiers
    filing_id: FilingId = Field(description="Unique filing identifier")
    company_id: CompanyId = Field(description="Associated company ID")

    # Filing information
    cik: CIK = Field(description="SEC Central Index Key")
    ticker: Ticker = Field(description="Stock ticker symbol")
    filing_type: FilingType = Field(description="SEC form type")
    filing_date: datetime = Field(description="Filing date with SEC")
    period_end_date: datetime | None = Field(
        default=None, description="Reporting period end date"
    )

    # Document information
    accession_number: str = Field(description="SEC accession number")
    form_type: str = Field(description="Exact form type string from SEC")
    filing_url: str = Field(description="URL to SEC filing")

    # Storage information
    storage_key: str | None = Field(
        default=None, description="Storage location for filing content"
    )
    file_size: int | None = Field(default=None, description="File size in bytes")
    checksum: str | None = Field(
        default=None, description="File checksum for integrity"
    )

    # Processing status
    is_processed: bool = Field(default=False, description="Whether filing is processed")
    processing_status: str | None = Field(
        default=None, description="Current processing status"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional filing metadata"
    )

    # Timestamps
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    fetched_at: datetime | None = Field(
        default=None, description="When filing was fetched from source"
    )


class CompanyRecord(BaseModel):
    """
    Database record for company entity.

    Stores company information including identifiers,
    basic details, and relationships to filings.
    """

    schema_version: int = Field(
        default=1, description="Schema version for compatibility"
    )

    # Core identifiers
    company_id: CompanyId = Field(description="Unique company identifier")
    cik: CIK = Field(description="SEC Central Index Key")
    ticker: Ticker | None = Field(default=None, description="Primary stock ticker")

    # Company information
    name: str = Field(description="Company name")
    legal_name: str | None = Field(default=None, description="Full legal entity name")

    # Business details
    industry: str | None = Field(default=None, description="Industry classification")
    sector: str | None = Field(default=None, description="Business sector")
    sic_code: str | None = Field(default=None, description="SIC classification code")
    naics_code: str | None = Field(
        default=None, description="NAICS classification code"
    )

    # Contact information
    business_address: str | None = Field(default=None, description="Business address")
    mailing_address: str | None = Field(default=None, description="Mailing address")
    phone: str | None = Field(default=None, description="Phone number")
    website: str | None = Field(default=None, description="Company website")

    # Status
    is_active: bool = Field(default=True, description="Whether company is active")
    fiscal_year_end: str | None = Field(
        default=None, description="Fiscal year end (MM-DD format)"
    )

    # Statistics
    filing_count: int = Field(default=0, description="Total number of filings")
    last_filing_date: datetime | None = Field(
        default=None, description="Date of most recent filing"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional company metadata"
    )

    # Timestamps
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
