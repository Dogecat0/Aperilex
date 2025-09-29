"""
Repository interfaces for domain entities.

This module defines protocols for repository operations and domain models
used for database interaction, following the Repository pattern.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.shared.enums import (
    AnalysisStatus,
    FilingType,
    TaskStatus,
    UserStatus,
    UserTier,
)
from src.shared.types import (
    CIK,
    AccessionNumber,
    AnalysisId,
    AuthRateLimitId,
    AuthSessionId,
    CompanyId,
    Email,
    FilingId,
    LearningProgressId,
    QuizAttemptId,
    Ticker,
    UserId,
    UserIdentityId,
    UserProfileId,
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
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Compact summary payload persisted in Postgres",
    )
    error_message: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class UserData(BaseModel):
    """User data contract for repository operations."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for user data models",
    )
    id: UserId
    email: Email
    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        description="Lifecycle state for the user",
    )
    tier: UserTier = Field(
        default=UserTier.BASIC,
        description="Subscription tier for the user",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserIdentityData(BaseModel):
    """External identity mapping data model."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for user identity data models",
    )
    id: UserIdentityId
    user_id: UserId
    provider: str = Field(description="Identity provider (e.g., GOOGLE)")
    provider_subject: str = Field(
        description="Stable subject/ID value issued by the provider",
    )
    provider_email: Email | None = Field(
        default=None,
        description="Email address returned by the provider",
    )
    raw_profile: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider profile payload for auditing",
    )
    verified_at: datetime | None = Field(
        default=None,
        description="Timestamp when the provider verified the identity",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserProfileData(BaseModel):
    """User profile and preference data model."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for user profile data models",
    )
    id: UserProfileId
    user_id: UserId
    display_name: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary preference map stored as JSON",
    )
    time_zone: str | None = Field(
        default=None,
        description="Preferred time zone identifier",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LearningProgressData(BaseModel):
    """Learning progress record for a specific module."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning progress data models",
    )
    id: LearningProgressId
    user_id: UserId
    module_key: str = Field(description="Stable identifier for the learning module")
    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Completion percentage for the module",
    )
    last_interaction_at: datetime | None = Field(
        default=None,
        description="Most recent interaction timestamp",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the module was completed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental metadata for the progress entry",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QuizAttemptData(BaseModel):
    """Quiz attempt model for learning analytics."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for quiz attempt data models",
    )
    id: QuizAttemptId
    user_id: UserId
    quiz_id: str = Field(description="Identifier for the quiz or assessment")
    question_count: int = Field(
        default=0,
        ge=0,
        description="Total number of questions in the attempt",
    )
    correct_count: int = Field(
        default=0,
        ge=0,
        description="Number of correct responses",
    )
    score_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Score represented as a percentage",
    )
    passed: bool = Field(
        default=False,
        description="Whether the attempt met the passing threshold",
    )
    responses: dict[str, Any] | None = Field(
        default=None,
        description="Structured response payload for review",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental metadata for analytics",
    )
    attempted_at: datetime = Field(
        description="When the attempt occurred",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuthSessionData(BaseModel):
    """Authentication session persisted for refresh token lifecycle."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for auth session data models",
    )
    id: AuthSessionId
    user_id: UserId
    refresh_token_hash: str = Field(
        ..., description="SHA-256 hash of the active refresh token"
    )
    previous_refresh_token_hash: str | None = Field(
        default=None,
        description="Hash of the previously valid refresh token",
    )
    session_key: str | None = Field(
        default=None,
        description="Stable identifier for the client session/device",
    )
    user_agent: str | None = Field(
        default=None,
        description="Captured user agent string for auditing",
    )
    ip_address: str | None = Field(
        default=None,
        description="Origin IP address for the session",
    )
    issued_at: datetime = Field(
        description="Timestamp when the session was issued",
    )
    expires_at: datetime = Field(
        description="Timestamp when the refresh token expires",
    )
    last_refreshed_at: datetime | None = Field(
        default=None,
        description="Timestamp of the latest successful refresh",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Timestamp when the session was revoked",
    )
    revoked_reason: str | None = Field(
        default=None,
        description="Optional reason provided during revocation",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata captured for the session",
    )


class AuthRateLimitData(BaseModel):
    """Rate limit tracker for authentication-related operations."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for auth rate limit data models",
    )
    id: AuthRateLimitId
    key: str = Field(
        ..., description="Unique identifier for the rate-limited subject",
    )
    action: str = Field(
        ..., description="Action being rate limited (e.g., LOGIN, REFRESH)",
    )
    user_id: UserId | None = Field(
        default=None,
        description="User identifier when rate limit is user-scoped",
    )
    window_start: datetime = Field(
        description="Start timestamp for the active rate limit window",
    )
    window_seconds: int = Field(
        ge=1,
        description="Window duration in seconds",
    )
    count: int = Field(
        default=0,
        ge=0,
        description="Number of events recorded within the window",
    )
    limit: int = Field(
        ge=1,
        description="Maximum allowed events within the window",
    )
    last_updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when the entry was last updated",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured metadata for analytics",
    )


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
    async def save_summary(
        self,
        analysis_id: AnalysisId,
        summary: dict[str, Any],
        *,
        metadata_updates: dict[str, str | int | float | bool] | None = None,
    ) -> bool:
        """Persist the compact summary payload for an analysis.

        Args:
            analysis_id: Analysis identifier
            summary: Summary payload to store in Postgres
            metadata_updates: Optional metadata entries to merge into `meta_data`

        Returns:
            True if saved successfully

        Raises:
            NotFoundError: If analysis not found
            ValidationError: If summary data is invalid
            DatabaseError: If database operation fails
        """
        ...


@runtime_checkable
class IUserRepository(Protocol):
    """Repository protocol for core user records."""

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> UserData | None:
        """Fetch a user by identifier."""

    @abstractmethod
    async def get_by_email(self, email: Email) -> UserData | None:
        """Fetch a user by email address."""

    @abstractmethod
    async def list_by_tier(
        self,
        tier: UserTier,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserData]:
        """List users filtered by subscription tier."""

    @abstractmethod
    async def create(self, user: UserData) -> UserData:
        """Persist a new user record."""

    @abstractmethod
    async def update(self, user: UserData) -> UserData:
        """Update an existing user record."""

    @abstractmethod
    async def delete(self, user_id: UserId) -> bool:
        """Delete a user by identifier."""

    @abstractmethod
    async def set_status(
        self,
        user_id: UserId,
        status: UserStatus,
    ) -> bool:
        """Update the lifecycle status for a user."""

    @abstractmethod
    async def exists(self, user_id: UserId) -> bool:
        """Check whether a user exists."""


@runtime_checkable
class IUserIdentityRepository(Protocol):
    """Repository for external user identity mappings."""

    @abstractmethod
    async def get_by_id(
        self, identity_id: UserIdentityId
    ) -> UserIdentityData | None:
        """Fetch an identity mapping by identifier."""

    @abstractmethod
    async def get_by_provider_subject(
        self,
        provider: str,
        provider_subject: str,
    ) -> UserIdentityData | None:
        """Fetch mapping for provider subject pair."""

    @abstractmethod
    async def list_for_user(self, user_id: UserId) -> list[UserIdentityData]:
        """List all identity mappings for a user."""

    @abstractmethod
    async def create(self, identity: UserIdentityData) -> UserIdentityData:
        """Persist a new identity mapping."""

    @abstractmethod
    async def update(self, identity: UserIdentityData) -> UserIdentityData:
        """Update an identity mapping."""

    @abstractmethod
    async def delete(self, identity_id: UserIdentityId) -> bool:
        """Delete an identity mapping."""


@runtime_checkable
class IUserProfileRepository(Protocol):
    """Repository for user profile records."""

    @abstractmethod
    async def get_by_id(
        self, profile_id: UserProfileId
    ) -> UserProfileData | None:
        """Fetch a profile by identifier."""

    @abstractmethod
    async def get_by_user_id(self, user_id: UserId) -> UserProfileData | None:
        """Fetch the profile associated with a user."""

    @abstractmethod
    async def upsert(self, profile: UserProfileData) -> UserProfileData:
        """Create or update the user's profile."""

    @abstractmethod
    async def delete(self, profile_id: UserProfileId) -> bool:
        """Remove a profile record."""


@runtime_checkable
class ILearningProgressRepository(Protocol):
    """Repository for learning progress tracking."""

    @abstractmethod
    async def get_by_id(
        self, progress_id: LearningProgressId
    ) -> LearningProgressData | None:
        """Fetch progress by identifier."""

    @abstractmethod
    async def get_for_user_module(
        self,
        user_id: UserId,
        module_key: str,
    ) -> LearningProgressData | None:
        """Fetch progress for a specific user/module pair."""

    @abstractmethod
    async def upsert(self, progress: LearningProgressData) -> LearningProgressData:
        """Create or update the progress entry."""

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LearningProgressData]:
        """List progress entries for a user."""

    @abstractmethod
    async def delete(self, progress_id: LearningProgressId) -> bool:
        """Delete a progress entry."""


@runtime_checkable
class IQuizAttemptRepository(Protocol):
    """Repository for quiz attempt persistence."""

    @abstractmethod
    async def get_by_id(
        self, attempt_id: QuizAttemptId
    ) -> QuizAttemptData | None:
        """Fetch a quiz attempt by identifier."""

    @abstractmethod
    async def get_latest_for_quiz(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttemptData | None:
        """Fetch the most recent attempt for a user/quiz pair."""

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[QuizAttemptData]:
        """List quiz attempts for a user."""

    @abstractmethod
    async def record_attempt(self, attempt: QuizAttemptData) -> QuizAttemptData:
        """Persist a new quiz attempt."""

    @abstractmethod
    async def delete(self, attempt_id: QuizAttemptId) -> bool:
        """Delete a quiz attempt record."""


@runtime_checkable
class IAuthSessionRepository(Protocol):
    """Repository protocol for managing authentication sessions."""

    @abstractmethod
    async def create(self, session: AuthSessionData) -> AuthSessionData:
        """Persist a new authentication session."""

    @abstractmethod
    async def get_by_id(self, session_id: AuthSessionId) -> AuthSessionData | None:
        """Fetch a session by identifier."""

    @abstractmethod
    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> AuthSessionData | None:
        """Fetch a session by hashed refresh token value."""

    @abstractmethod
    async def list_active_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[AuthSessionData]:
        """List active sessions for a specific user."""

    @abstractmethod
    async def rotate_refresh_token(
        self,
        session_id: AuthSessionId,
        refresh_token_hash: str,
        expires_at: datetime,
        *,
        previous_hash: str | None,
        rotation_time: datetime,
    ) -> AuthSessionData:
        """Rotate refresh token and return the updated session."""

    @abstractmethod
    async def mark_revoked(
        self,
        session_id: AuthSessionId,
        revoked_at: datetime,
        reason: str | None = None,
    ) -> bool:
        """Mark a session as revoked."""

    @abstractmethod
    async def update_last_activity(
        self,
        session_id: AuthSessionId,
        timestamp: datetime,
    ) -> bool:
        """Update the last refresh timestamp for a session."""

    @abstractmethod
    async def delete_expired(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> int:
        """Delete expired sessions; returns number of rows removed."""


@runtime_checkable
class IAuthRateLimitRepository(Protocol):
    """Repository protocol for authentication rate limiting state."""

    @abstractmethod
    async def get_current(
        self,
        key: str,
        action: str,
    ) -> AuthRateLimitData | None:
        """Fetch the current rate limit entry for the given key/action."""

    @abstractmethod
    async def increment_and_get(
        self,
        key: str,
        action: str,
        *,
        user_id: UserId | None,
        window_seconds: int,
        limit: int,
        now: datetime,
    ) -> tuple[AuthRateLimitData, bool]:
        """Increment usage counter and return updated entry along with allowance."""

    @abstractmethod
    async def reset(self, key: str, action: str) -> bool:
        """Reset rate limit counters for the specified key/action."""

    @abstractmethod
    async def cleanup(
        self,
        *,
        older_than: datetime,
        limit: int = 500,
    ) -> int:
        """Remove stale rate limit entries and return number removed."""


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
    async def get_user_repository(self) -> IUserRepository:
        """Get a User repository instance."""

    @abstractmethod
    async def get_user_identity_repository(self) -> IUserIdentityRepository:
        """Get a UserIdentity repository instance."""

    @abstractmethod
    async def get_user_profile_repository(self) -> IUserProfileRepository:
        """Get a UserProfile repository instance."""

    @abstractmethod
    async def get_learning_progress_repository(self) -> ILearningProgressRepository:
        """Get a LearningProgress repository instance."""

    @abstractmethod
    async def get_quiz_attempt_repository(self) -> IQuizAttemptRepository:
        """Get a QuizAttempt repository instance."""

    @abstractmethod
    async def get_auth_session_repository(self) -> IAuthSessionRepository:
        """Get an AuthSession repository instance."""

    @abstractmethod
    async def get_auth_rate_limit_repository(self) -> IAuthRateLimitRepository:
        """Get an AuthRateLimit repository instance."""

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
