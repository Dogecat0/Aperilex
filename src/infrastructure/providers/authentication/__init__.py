"""
Authentication provider implementations.

Provides concrete implementations of the IAuthenticationProvider protocol.
"""

from .mock_provider import MockAuthenticationProvider

__all__ = [
    "MockAuthenticationProvider",
]
