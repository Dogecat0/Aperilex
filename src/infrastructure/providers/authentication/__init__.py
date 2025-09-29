"""
Authentication provider implementations.

Provides concrete implementations of the IAuthenticationProvider protocol.
"""

from .google_oauth_provider import GoogleOAuthAuthenticationProvider
from .mock_provider import MockAuthenticationProvider

__all__ = [
    "MockAuthenticationProvider",
    "GoogleOAuthAuthenticationProvider",
]
