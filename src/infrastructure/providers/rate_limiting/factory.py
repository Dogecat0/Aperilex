"""
Factory for creating rate limiting provider instances.
"""

import logging
from typing import Any

from src.application.interfaces.rate_limiting import (
    IRateLimitingProvider,
    RateLimitConfig,
)
from src.shared.enums import RateLimitingProvider

from .in_memory import InMemoryRateLimitingProvider

logger = logging.getLogger(__name__)


class RateLimitingProviderFactory:
    """Factory for creating rate limiting provider instances."""

    @staticmethod
    def create(
        provider_type: RateLimitingProvider,
        config: RateLimitConfig | None = None,
        **kwargs: Any,
    ) -> IRateLimitingProvider:
        """
        Create a rate limiting provider instance.

        Args:
            provider_type: Type of provider to create
            config: Rate limiting configuration
            **kwargs: Additional provider-specific configuration

        Returns:
            Rate limiting provider instance

        Raises:
            ValueError: If provider type is not supported
        """
        logger.info(f"Creating rate limiting provider: {provider_type.value}")

        if provider_type == RateLimitingProvider.IN_MEMORY:
            return InMemoryRateLimitingProvider(config=config, **kwargs)

        elif provider_type == RateLimitingProvider.REDIS:
            raise NotImplementedError(
                "Redis rate limiting provider not yet implemented"
            )

        elif provider_type == RateLimitingProvider.MEMCACHED:
            raise NotImplementedError(
                "Memcached rate limiting provider not yet implemented"
            )

        else:
            raise ValueError(f"Unsupported rate limiting provider: {provider_type}")
