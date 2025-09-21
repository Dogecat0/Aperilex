"""
Authentication provider interface for API security.

This module defines the protocol for authentication and authorization
in the API orchestrator layer.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.shared.types import UserId


class AuthenticationCredentials(BaseModel):
    """Authentication credentials."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for authentication credential models",
    )
    token: str = Field(..., description="Authentication token (JWT, API key, etc.)")
    token_type: str = Field(default="Bearer", description="Type of token")


class AuthenticationResult(BaseModel):
    """Result of authentication attempt."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for authentication result models",
    )
    authenticated: bool = Field(..., description="Whether authentication succeeded")
    user_id: UserId | None = Field(None, description="Authenticated user ID")
    user_email: str | None = Field(None, description="User email address")
    user_tier: str | None = Field(None, description="User subscription tier")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    error_message: str | None = Field(
        None, description="Error message if authentication failed"
    )


class RateLimitInfo(BaseModel):
    """Rate limiting information for a user."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for rate limit info models",
    )
    limit: int = Field(..., description="Maximum requests allowed")
    remaining: int = Field(..., description="Remaining requests in window")
    reset_at: str = Field(..., description="ISO-8601 timestamp when limit resets")
    window_seconds: int = Field(..., description="Rate limit window in seconds")


@runtime_checkable
class IAuthenticationProvider(Protocol):
    """
    Protocol for authentication and authorization.

    Implementations might use JWT, OAuth2, API keys, or custom auth.
    """

    @abstractmethod
    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """
        Authenticate a user based on credentials.

        Args:
            credentials: Authentication credentials

        Returns:
            Authentication result with user information
        """
        ...

    @abstractmethod
    async def authorize(self, user_id: UserId, resource: str, action: str) -> bool:
        """
        Check if a user is authorized to perform an action on a resource.

        Args:
            user_id: User to check authorization for
            resource: Resource being accessed
            action: Action being performed (read, write, delete, etc.)

        Returns:
            True if authorized, False otherwise
        """
        ...

    @abstractmethod
    async def validate_token(self, token: str) -> AuthenticationResult:
        """
        Validate an authentication token.

        Args:
            token: Token to validate

        Returns:
            Authentication result if token is valid
        """
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> AuthenticationCredentials:
        """
        Refresh an authentication token.

        Args:
            refresh_token: Refresh token

        Returns:
            New authentication credentials
        """
        ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an authentication token.

        Args:
            token: Token to revoke

        Returns:
            True if revoked successfully
        """
        ...

    @abstractmethod
    async def get_rate_limit(self, user_id: UserId) -> RateLimitInfo:
        """
        Get rate limit information for a user.

        Args:
            user_id: User to get rate limits for

        Returns:
            Rate limit information
        """
        ...

    @abstractmethod
    async def check_rate_limit(self, user_id: UserId, increment: bool = True) -> bool:
        """
        Check if a user has exceeded rate limits.

        Args:
            user_id: User to check
            increment: Whether to increment the counter

        Returns:
            True if within limits, False if exceeded
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the authentication provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """
        Initialize the error.

        Args:
            message: Error message
            code: Error code for categorization
        """
        super().__init__(message)
        self.code = code


class AuthorizationError(Exception):
    """Exception raised when authorization fails."""

    def __init__(
        self, message: str, resource: str | None = None, action: str | None = None
    ) -> None:
        """
        Initialize the error.

        Args:
            message: Error message
            resource: Resource that was being accessed
            action: Action that was attempted
        """
        super().__init__(message)
        self.resource = resource
        self.action = action
