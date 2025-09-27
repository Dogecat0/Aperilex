"""
Repository interfaces for domain entities.

This module defines protocols for repository operations and domain models
used for database interaction, following the Repository pattern.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.shared.enums import AnalysisStatus, FilingType, TaskStatus
from src.shared.types import (
    CIK,
    AccessionNumber,
    AnalysisId,
    CompanyId,
    FilingId,
    Ticker,
    UserId,
)

# Domain Models (Pydantic representations for interface contracts)


class CompanyData(BaseModel):
    """Company data model for repository operations."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for company data models",
    )
    id: CompanyId
    cik: CIK
    name: str
    ticker: Ticker | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FilingData(BaseModel):
    """Filing data model for repository operations."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for filing data models",
    )
    id: FilingId
    company_id: CompanyId
    filing_type: FilingType
    accession_number: AccessionNumber
    filing_date: datetime
    processing_status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current processing status stored as TaskStatus",
    )
    processing_error: str | None = Field(
        default=None,
        description="Processing error message if filing processing failed",
    )
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AnalysisData(BaseModel):
    """Analysis data model for repository operations."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for analysis data models",
    )
    id: AnalysisId
    filing_id: FilingId
    user_id: UserId
    created_by: str | None = Field(
        default=None,
        description="Identifier of the actor that initiated the analysis",
    )
    status: AnalysisStatus
    analysis_type: str
    result: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Compact summary payload persisted in Postgres",
    )
    error_message: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


# Repository Protocols


@runtime_checkable
class ICompanyRepository(Protocol):
    """Protocol for Company repository operations.

    Enhanced repository pattern: Handles both UUID and human identifier lookups
    with efficient caching. Complex queries are delegated to query services.
    """

    @abstractmethod
    async def get_by_id(self, company_id: CompanyId) -> CompanyData | None:
        """
        Get company by ID.

        Args:
            company_id: Unique company identifier

        Returns:
            Company data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_cik(self, cik: CIK) -> CompanyData | None:
        """
        Get company by CIK.

        Args:
            cik: Central Index Key

        Returns:
            Company data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_ticker(self, ticker: Ticker) -> CompanyData | None:
        """
        Get company by ticker symbol.

        Args:
            ticker: Company ticker symbol

        Returns:
            Company data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def create(self, company: CompanyData) -> CompanyData:
        """
        Create a new company.

        Args:
            company: Company data to create

        Returns:
            Created company data with generated ID

        Raises:
            AlreadyExistsError: If company with same CIK exists
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def update(self, company: CompanyData) -> CompanyData:
        """
        Update existing company.

        Args:
            company: Company data with updates

        Returns:
            Updated company data

        Raises:
            NotFoundError: If company not found
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def delete(self, company_id: CompanyId) -> bool:
        """
        Delete a company.

        Args:
            company_id: Company identifier to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def exists(self, company_id: CompanyId) -> bool:
        """
        Check if company exists by company ID.

        Args:
            company_id: Unique company identifier

        Returns:
            True if company exists, False otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def find_by_name(self, name: str, limit: int = 10) -> list[CompanyData]:
        """
        Find companies by name (partial match).

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching companies

        Raises:
            DatabaseError: If database operation fails
        """
        ...


@runtime_checkable
class IFilingRepository(Protocol):
    """Protocol for Filing repository operations.

    Enhanced repository pattern: Handles both UUID and human identifier lookups
    with efficient caching. Complex queries are delegated to query services.
    """

    @abstractmethod
    async def get_by_id(self, filing_id: FilingId) -> FilingData | None:
        """
        Get filing by ID.

        Args:
            filing_id: Unique filing identifier

        Returns:
            Filing data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_accession_number(
        self, accession_number: AccessionNumber
    ) -> FilingData | None:
        """
        Get filing by accession number.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_company_id(
        self,
        company_id: CompanyId,
        filing_type: FilingType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingData]:
        """
        Get filings for a company.

        Args:
            company_id: Company identifier
            filing_type: Optional filter by filing type
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of filings for the company

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_latest_by_type(
        self,
        company_id: CompanyId,
        filing_type: FilingType,
    ) -> FilingData | None:
        """
        Get the most recent filing of a specific type for a company.

        Args:
            company_id: Company identifier
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            Latest filing if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def create(self, filing: FilingData) -> FilingData:
        """
        Create a new filing.

        Args:
            filing: Filing data to create

        Returns:
            Created filing data with generated ID

        Raises:
            AlreadyExistsError: If filing with same accession number exists
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def update(self, filing: FilingData) -> FilingData:
        """
        Update existing filing.

        Args:
            filing: Filing data with updates

        Returns:
            Updated filing data

        Raises:
            NotFoundError: If filing not found
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def delete(self, filing_id: FilingId) -> bool:
        """
        Delete a filing.

        Args:
            filing_id: Filing identifier to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def exists(self, filing_id: FilingId) -> bool:
        """
        Check if filing exists by filing ID.

        Args:
            filing_id: Unique filing identifier

        Returns:
            True if filing exists, False otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...


@runtime_checkable
class IAnalysisRepository(Protocol):
    """Protocol for Analysis repository operations.

    Enhanced repository pattern: Handles basic CRUD and relationship-based lookups.
    Complex queries are delegated to query services.
    """

    @abstractmethod
    async def get_by_id(self, analysis_id: AnalysisId) -> AnalysisData | None:
        """
        Get analysis by ID.

        Args:
            analysis_id: Unique analysis identifier

        Returns:
            Analysis data if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_filing_id(
        self,
        filing_id: FilingId,
        analysis_type: str | None = None,
    ) -> list[AnalysisData]:
        """
        Get analyses for a filing.

        Args:
            filing_id: Filing identifier
            analysis_type: Optional filter by analysis type

        Returns:
            List of analyses for the filing

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UserId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisData]:
        """
        Get analyses for a user.

        Args:
            user_id: User identifier
            status: Optional filter by status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of analyses for the user

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def create(self, analysis: AnalysisData) -> AnalysisData:
        """
        Create a new analysis.

        Args:
            analysis: Analysis data to create

        Returns:
            Created analysis data with generated ID

        Raises:
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def update(self, analysis: AnalysisData) -> AnalysisData:
        """
        Update existing analysis.

        Args:
            analysis: Analysis data with updates

        Returns:
            Updated analysis data

        Raises:
            NotFoundError: If analysis not found
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def update_status(
        self,
        analysis_id: AnalysisId,
        status: AnalysisStatus,
        error_message: str | None = None,
    ) -> bool:
        """
        Update analysis status.

        Args:
            analysis_id: Analysis identifier
            status: New status
            error_message: Optional error message if failed

        Returns:
            True if updated successfully

        Raises:
            NotFoundError: If analysis not found
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def delete(self, analysis_id: AnalysisId) -> bool:
        """
        Delete an analysis.

        Args:
            analysis_id: Analysis identifier to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def exists(self, analysis_id: AnalysisId) -> bool:
        """
        Check if analysis exists by analysis ID.

        Args:
            analysis_id: Unique analysis identifier

        Returns:
            True if analysis exists, False otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        ...

    @abstractmethod
    async def count_with_filters(
        self,
        *,
        company_cik: Any | None = None,
        search: str | None = None,
        segment: str | None = None,
        statuses: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        created_by: str | None = None,
    ) -> int:
        """Count analyses matching the provided filters."""

        ...

    @abstractmethod
    async def find_with_filters(
        self,
        *,
        company_cik: Any | None = None,
        search: str | None = None,
        segment: str | None = None,
        statuses: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        created_by: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AnalysisData]:
        """Retrieve analyses with optional filtering, sorting, and pagination."""

        ...

    @abstractmethod
    async def save_result(
        self,
        analysis_id: AnalysisId,
        result: dict[str, Any],
    ) -> bool:
        """
        Save analysis result.

        Args:
            analysis_id: Analysis identifier
            result: Analysis result data

        Returns:
            True if saved successfully

        Raises:
            NotFoundError: If analysis not found
            ValidationError: If result data is invalid
            DatabaseError: If database operation fails
        """
        ...


@runtime_checkable
class IRepositoryFactory(Protocol):
    """Protocol for creating repository instances with proper session management."""

    @abstractmethod
    async def get_company_repository(self) -> ICompanyRepository:
        """
        Get a Company repository instance.

        Returns:
            Company repository with active session

        Raises:
            DatabaseError: If repository cannot be created
        """
        ...

    @abstractmethod
    async def get_filing_repository(self) -> IFilingRepository:
        """
        Get a Filing repository instance.

        Returns:
            Filing repository with active session

        Raises:
            DatabaseError: If repository cannot be created
        """
        ...

    @abstractmethod
    async def get_analysis_repository(self) -> IAnalysisRepository:
        """
        Get an Analysis repository instance.

        Returns:
            Analysis repository with active session

        Raises:
            DatabaseError: If repository cannot be created
        """
        ...

    @abstractmethod
    async def begin_transaction(self) -> None:
        """
        Begin a database transaction.

        All repositories created after this call will share the same transaction.

        Raises:
            DatabaseError: If transaction cannot be started
        """
        ...

    @abstractmethod
    async def commit_transaction(self) -> None:
        """
        Commit the current transaction.

        Raises:
            DatabaseError: If commit fails
            TransactionError: If no active transaction
        """
        ...

    @abstractmethod
    async def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.

        Raises:
            DatabaseError: If rollback fails
            TransactionError: If no active transaction
        """
        ...

    @abstractmethod
    async def close(self, success: bool = True) -> None:
        """
        Close all repository sessions and cleanup resources.

        Args:
            success: Indicates whether resources should be committed (True) or rolled back (False)

        Raises:
            DatabaseError: If close operation fails
        """
        ...
