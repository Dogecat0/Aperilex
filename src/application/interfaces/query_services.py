"""
Query service interfaces for complex data retrieval operations.

These services handle complex queries, filtering, aggregations, and
business logic queries that go beyond simple CRUD operations.
They operate on system IDs after resolution has been performed.
"""

from abc import abstractmethod
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.shared.enums import (
    AnalysisStatus,
    FilingType,
    LearningReviewStatus,
    LearningWalkthroughArtifactType,
    UserStatus,
    UserTier,
)
from src.shared.types import (
    AnalysisId,
    CompanyId,
    Email,
    FilingId,
    LearningProgressId,
    LearningWalkthroughBindingId,
    QuizAttemptId,
    UserId,
)

# Query Result Models (using Pydantic for validation)


class FilingQueryResult(BaseModel):
    """Result model for filing queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for filing query result models",
    )
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

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for filing query page models",
    )
    items: list[FilingQueryResult]
    total_count: int


class AnalysisQueryResult(BaseModel):
    """Result model for analysis queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for analysis query result models",
    )
    analysis_id: AnalysisId
    filing_id: FilingId
    user_id: UserId
    status: AnalysisStatus
    analysis_type: str
    created_at: datetime
    updated_at: datetime | None = None


class CompanyQueryResult(BaseModel):
    """Result model for company queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for company query result models",
    )
    company_id: CompanyId
    cik: str
    name: str
    ticker: str | None = None
    metadata: dict[str, str | int | float | bool] = {}


class UserQueryResult(BaseModel):
    """Result model for user queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for user query result models",
    )
    user_id: UserId
    email: Email
    status: UserStatus
    tier: UserTier
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LearningProgressQueryResult(BaseModel):
    """Result model for learning progress queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning progress query result models",
    )
    progress_id: LearningProgressId
    user_id: UserId
    module_key: str
    progress_percent: int
    completed_at: datetime | None = None
    last_interaction_at: datetime | None = None
    updated_at: datetime | None = None


class LearningWalkthroughBindingQueryResult(BaseModel):
    """Result model for walkthrough binding queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for binding query result models",
    )
    binding_id: LearningWalkthroughBindingId
    walkthrough_section_id: str
    artifact_id: str
    artifact_type: LearningWalkthroughArtifactType
    lesson_id: str
    learning_module_key: str
    module_stage: str
    lesson_title: str | None = None
    status: LearningReviewStatus
    last_reviewed_at: datetime | None = None
    updated_at: datetime | None = None


class QuizAttemptQueryResult(BaseModel):
    """Result model for quiz attempt queries."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for quiz attempt query result models",
    )
    attempt_id: QuizAttemptId
    user_id: UserId
    quiz_id: str
    score_percent: float
    passed: bool
    attempted_at: datetime


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

    @abstractmethod
    async def get_latest_completed(
        self,
        cik: str,
        filing_type: FilingType,
        before_date: datetime,
    ) -> AnalysisQueryResult | None:
        """Fetch the latest completed analysis for a company before the provided date.

        Args:
            cik: Company CIK identifier
            filing_type: Filing type to filter on
            before_date: Only consider analyses created before this datetime

        Returns:
            Most recent completed analysis query result, if available

        Raises:
            QueryServiceError: If the lookup operation fails
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


@runtime_checkable
class IUserQueryService(Protocol):
    """Query service for user search and listing operations."""

    @abstractmethod
    async def get_user_overview(self, user_id: UserId) -> UserQueryResult | None:
        """Fetch a concise overview for a specific user."""

    @abstractmethod
    async def search_users(
        self,
        *,
        email: str | None = None,
        statuses: list[UserStatus] | None = None,
        tiers: list[UserTier] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserQueryResult]:
        """Search users with optional filters and pagination."""

    @abstractmethod
    async def list_recent_users(
        self,
        *,
        limit: int = 20,
    ) -> list[UserQueryResult]:
        """List recently registered users for dashboards."""


@runtime_checkable
class ILearningProgressQueryService(Protocol):
    """Query service for learning progress aggregation."""

    @abstractmethod
    async def get_user_progress(
        self,
        user_id: UserId,
    ) -> list[LearningProgressQueryResult]:
        """Retrieve all progress entries for a user."""

    @abstractmethod
    async def get_module_learners(
        self,
        module_key: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LearningProgressQueryResult]:
        """Retrieve learners engaging with a given module."""


@runtime_checkable
class ILearningWalkthroughBindingQueryService(Protocol):
    """Query service for walkthrough binding aggregation."""

    @abstractmethod
    async def get_binding(
        self,
        binding_id: LearningWalkthroughBindingId,
    ) -> LearningWalkthroughBindingQueryResult | None:
        """Retrieve a binding by identifier."""

    @abstractmethod
    async def get_binding_by_artifact(
        self,
        artifact_id: str,
        artifact_type: LearningWalkthroughArtifactType,
    ) -> LearningWalkthroughBindingQueryResult | None:
        """Retrieve a binding by its walkthrough artifact."""

    @abstractmethod
    async def list_section_bindings(
        self,
        walkthrough_section_id: str,
    ) -> list[LearningWalkthroughBindingQueryResult]:
        """Retrieve bindings for a specific walkthrough section."""

    @abstractmethod
    async def list_module_bindings(
        self,
        learning_module_key: str,
    ) -> list[LearningWalkthroughBindingQueryResult]:
        """Retrieve bindings associated with a learning module."""


@runtime_checkable
class IQuizAttemptQueryService(Protocol):
    """Query service for quiz attempt analytics."""

    @abstractmethod
    async def get_recent_attempts(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[QuizAttemptQueryResult]:
        """Retrieve recent quiz attempts for a user."""

    @abstractmethod
    async def get_best_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttemptQueryResult | None:
        """Retrieve the best scoring attempt for the quiz."""


class QueryServiceError(Exception):
    """Raised when a query service operation fails."""

    pass
