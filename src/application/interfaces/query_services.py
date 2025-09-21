"""
Query service interfaces for complex data retrieval operations.

These services handle complex queries, filtering, aggregations, and
business logic queries that go beyond simple CRUD operations.
They operate on system IDs after resolution has been performed.
"""

from abc import abstractmethod
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.enums import AnalysisStatus, FilingType
from src.shared.types import AnalysisId, CompanyId, FilingId, UserId

# Query Result Models (using Pydantic for validation)


class FilingQueryResult(BaseModel):
    """Result model for filing queries."""

    schema_version: int = 1
    filing_id: FilingId
    company_id: CompanyId
    filing_type: FilingType
    filing_date: datetime
    accession_number: str
    processing_status: str
    processing_error: str | None = None
    metadata: dict[str, str | int | float | bool] = {}


class FilingQueryPage(BaseModel):
    """Paginated filing query results."""

    schema_version: int = 1
    items: list[FilingQueryResult]
    total_count: int


class AnalysisQueryResult(BaseModel):
    """Result model for analysis queries."""

    schema_version: int = 1
    analysis_id: AnalysisId
    filing_id: FilingId
    user_id: UserId
    status: AnalysisStatus
    analysis_type: str
    created_at: datetime
    updated_at: datetime | None = None


class CompanyQueryResult(BaseModel):
    """Result model for company queries."""

    schema_version: int = 1
    company_id: CompanyId
    cik: str
    name: str
    ticker: str | None = None
    metadata: dict[str, str | int | float | bool] = {}


# Query Service Protocols


@runtime_checkable
class IFilingQueryService(Protocol):
    """Query service for complex filing queries.

    Handles date ranges, type filtering, company filtering, and other
    complex queries that go beyond simple ID lookups.
    """

    @abstractmethod
    async def get_latest_filing(
        self,
        company_id: CompanyId,
        filing_type: FilingType,
    ) -> FilingQueryResult | None:
        """
        Get the latest filing of a specific type for a company.

        Args:
            company_id: Company system ID
            filing_type: Type of filing to find

        Returns:
            Latest filing if found, None otherwise

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def search_by_date_range(
        self,
        start_date: date,
        end_date: date,
        company_id: CompanyId | None = None,
        filing_type: FilingType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingQueryResult]:
        """
        Search filings within a date range with optional filters.

        Args:
            start_date: Start of date range
            end_date: End of date range
            company_id: Optional company filter
            filing_type: Optional filing type filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of filings matching criteria

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def get_filings_by_company(
        self,
        company_id: CompanyId,
        filing_types: list[FilingType] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingQueryResult]:
        """
        Get all filings for a company with optional type filtering.

        Args:
            company_id: Company system ID
            filing_types: Optional list of filing types to include
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of company filings

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def list_company_filings_paginated(
        self,
        *,
        company_id: CompanyId,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_field: str = "filing_date",
        sort_direction: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> FilingQueryPage:
        """Retrieve filings for a company with filtering, sorting, and pagination."""
        ...


@runtime_checkable
class IAnalysisQueryService(Protocol):
    """Query service for complex analysis queries.

    Handles filtering by status, company, filing, date ranges, and other
    complex queries for analysis records.
    """

    @abstractmethod
    async def find_by_filing(
        self,
        filing_id: FilingId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
    ) -> list[AnalysisQueryResult]:
        """
        Find all analyses for a specific filing.

        Args:
            filing_id: Filing system ID
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            List of analyses for the filing

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def find_by_user(
        self,
        user_id: UserId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisQueryResult]:
        """
        Find all analyses for a specific user.

        Args:
            user_id: User system ID
            status: Optional status filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of user's analyses

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def find_recent_completed(
        self,
        company_id: CompanyId | None = None,
        limit: int = 10,
    ) -> list[AnalysisQueryResult]:
        """
        Find recently completed analyses.

        Args:
            company_id: Optional company filter
            limit: Maximum results to return

        Returns:
            List of recent completed analyses

        Raises:
            QueryServiceError: If query operation fails
        """
        ...


@runtime_checkable
class ICompanyQueryService(Protocol):
    """Query service for complex company queries.

    Handles name searches, filtering, and other complex company queries.
    """

    @abstractmethod
    async def search_by_name(
        self,
        name_pattern: str,
        fuzzy: bool = True,
        limit: int = 10,
    ) -> list[CompanyQueryResult]:
        """
        Search companies by name pattern.

        Args:
            name_pattern: Name or partial name to search
            fuzzy: Whether to use fuzzy matching
            limit: Maximum results to return

        Returns:
            List of matching companies, best matches first

        Raises:
            QueryServiceError: If query operation fails
        """
        ...

    @abstractmethod
    async def get_companies_with_recent_filings(
        self,
        days_back: int = 30,
        filing_type: FilingType | None = None,
        limit: int = 100,
    ) -> list[CompanyQueryResult]:
        """
        Get companies that have recent filings.

        Args:
            days_back: Number of days to look back
            filing_type: Optional filing type filter
            limit: Maximum results to return

        Returns:
            List of companies with recent filings

        Raises:
            QueryServiceError: If query operation fails
        """
        ...


class QueryServiceError(Exception):
    """Raised when a query service operation fails."""

    pass
