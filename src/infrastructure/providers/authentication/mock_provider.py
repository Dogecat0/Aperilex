"""
Mock authentication provider for testing.

Provides a simple in-memory authentication provider for development and testing.
"""

import uuid
from datetime import UTC, datetime, timedelta

from src.application.interfaces.authentication import (
    AuthenticationCredentials,
    AuthenticationResult,
    RateLimitInfo,
)
from src.shared.types import UserId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TOKEN_TYPE = "Bearer"  # nosec


class MockAuthenticationProvider:
    """
    Mock authentication provider for testing.

    This provider accepts any token and returns a mock user.
    Used for development and testing environments.
    """

    def __init__(self) -> None:
        """
        Initialize the mock authentication provider.
        """
        self.mock_user_id = UserId(uuid.uuid4())
        self.mock_email = "test@example.com"
        self.mock_tier = "BASIC"
        self.mock_permissions = ["read", "write"]
        self.request_counts: dict[str, int] = {}

    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """
        Mock authentication - always succeeds for testing.

        Args:
            credentials: Authentication credentials

        Returns:
            Successful authentication result with mock user
        """
        # Simulate authentication delay
        logger.debug(f"Mock authentication for token: {credentials.token[:20]}...")

        # Always return successful authentication for testing
        return AuthenticationResult(
            authenticated=True,
            user_id=self.mock_user_id,
            user_email=self.mock_email,
            user_tier=self.mock_tier,
            permissions=self.mock_permissions,
            error_message=None,
        )

    async def authorize(self, user_id: UserId, resource: str, action: str) -> bool:
        """
        Mock authorization - always allows for testing.

        Args:
            user_id: User to check authorization for
            resource: Resource being accessed
            action: Action being performed

        Returns:
            Always True for testing
        """
        logger.debug(
            f"Mock authorization: user={user_id}, resource={resource}, action={action}"
        )
        return True

    async def validate_token(self, token: str) -> "AuthenticationResult":
        """
        Mock token validation - always succeeds.

        Args:
            token: Token to validate

        Returns:
            Successful authentication result
        """
        credentials = AuthenticationCredentials(
            token=token, token_type=DEFAULT_TOKEN_TYPE
        )
        return await self.authenticate(credentials)

    async def refresh_token(self, refresh_token: str) -> "AuthenticationCredentials":
        """
        Mock token refresh - returns a new mock token.

        Args:
            refresh_token: Refresh token

        Returns:
            New mock authentication credentials
        """
        new_token = f"mock_access_token_{uuid.uuid4()}"
        return AuthenticationCredentials(
            token=new_token,
            token_type=DEFAULT_TOKEN_TYPE,
        )

    async def revoke_token(self, token: str) -> bool:
        """
        Mock token revocation - always succeeds.

        Args:
            token: Token to revoke

        Returns:
            Always True
        """
        logger.debug(f"Mock token revoked: {token[:20]}...")
        return True

    async def get_rate_limit(self, user_id: UserId) -> RateLimitInfo:
        """
        Mock rate limit information.

        Args:
            user_id: User to get rate limits for

        Returns:
            Mock rate limit information
        """
        user_key = str(user_id)
        count = self.request_counts.get(user_key, 0)

        return RateLimitInfo(
            limit=100,
            remaining=max(0, 100 - count),
            reset_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            window_seconds=3600,
        )

    async def check_rate_limit(self, user_id: UserId, increment: bool = True) -> bool:
        """
        Mock rate limit check.

        Args:
            user_id: User to check
            increment: Whether to increment the counter

        Returns:
            True if within limits (always true for first 100 requests)
        """
        user_key = str(user_id)
        count = self.request_counts.get(user_key, 0)

        if increment:
            self.request_counts[user_key] = count + 1

        # Allow first 100 requests
        return count < 100

    async def health_check(self) -> bool:
        """
        Mock health check - always healthy.

        Returns:
            Always True
        """
        return True
