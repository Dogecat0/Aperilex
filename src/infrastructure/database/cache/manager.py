"""Dogpile cache configuration for SQLAlchemy queries."""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion, make_region
from sqlalchemy.orm.query import Query

from src.shared.config.settings import Settings

logger = logging.getLogger(__name__)

settings = Settings()


class CacheRegionName(str, Enum):
    """Enumeration of available cache regions."""

    COMPANY = "company"
    FILING = "filing"
    ANALYSIS = "analysis"
    QUERY = "query"


@dataclass
class CacheConfig:
    """Configuration for cache regions."""

    expiration_time: int
    description: str


REGION_CONFIGS = {
    CacheRegionName.COMPANY: CacheConfig(
        expiration_time=604800,  # 7 days - companies change rarely
        description="Company entity cache",
    ),
    CacheRegionName.FILING: CacheConfig(
        expiration_time=604800,  # 7 days - filings are immutable
        description="Filing entity cache",
    ),
    CacheRegionName.ANALYSIS: CacheConfig(
        expiration_time=604800,  # 7 days - analyses are immutable
        description="Analysis entity cache",
    ),
    CacheRegionName.QUERY: CacheConfig(
        expiration_time=604800,  # 7 days for complex queries
        description="Complex query results cache",
    ),
}


# TODO: Validate that this does not include a timestamp or changing data
def create_cache_key_generator(namespace: str) -> Callable[..., str]:
    """Create a cache key generator for a specific namespace.

    Args:
        namespace: Cache namespace (e.g., 'company', 'filing', 'analysis')

    Returns:
        Key generator function
    """

    def generate_key(*args: Any, **kwargs: Any) -> str:
        """Generate a cache key from arguments."""
        key_parts = [namespace]

        # Add positional arguments
        for arg in args:
            if hasattr(arg, "__dict__"):
                # For objects, use their string representation
                key_parts.append(str(arg))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")

        # Create key string
        key = ":".join(key_parts)

        # Hash if too long (memcached has 250 char limit)
        if len(key) > 200:
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            key = f"{namespace}:hash:{key_hash}"

        return key

    return generate_key


T = TypeVar("T")


def query_cache_key[T](namespace: str, query: Query[T]) -> str:
    """Generate a cache key for a SQLAlchemy query.

    Args:
        namespace: Cache namespace
        query: SQLAlchemy query object

    Returns:
        Cache key string
    """
    # Get the compiled SQL with parameters
    compiled = query.statement.compile()
    sql_str = str(compiled)
    params_str = str(compiled.params)

    # Create a unique key from SQL and parameters
    key_data = f"{namespace}:{sql_str}:{params_str}"

    # Hash for consistent key length
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()
    return f"{namespace}:query:{key_hash}"


class CacheManager:
    """Manager for application cache regions with invalidation support."""

    def __init__(self) -> None:
        """Initialize cache manager with configured regions."""
        self.regions: dict[CacheRegionName, CacheRegion] = {}
        self._initialize_regions()

    def _initialize_regions(self) -> None:
        """Initialize cache regions based on configuration."""
        for region_name in CacheRegionName:
            config = REGION_CONFIGS[region_name]

            # expiration = config.expiration_time
            self.regions[region_name] = make_region(
                name=region_name.value,
                function_key_generator=create_cache_key_generator(region_name.value),
            ).configure(
                "dogpile.cache.memory",
                # expiration_time=float(expiration),
                arguments={"cache_dict": {}},
            )

            logger.info(
                "Initialized cache region '%s': %s (TTL: %ds)",
                region_name.value,
                config.description,
                # config.expiration_time,
            )

    def get_region(self, name: CacheRegionName) -> CacheRegion:
        """Get a cache region by name.

        Args:
            name: Region name enum

        Returns:
            Cache region

        Raises:
            KeyError: If region doesn't exist
        """
        if name not in self.regions:
            raise KeyError(f"Cache region '{name.value}' not found")
        return self.regions[name]

    def invalidate_region(self, name: CacheRegionName) -> None:
        """Invalidate all keys in a region.

        Args:
            name: Region name enum
        """
        region = self.get_region(name)
        region.invalidate()
        logger.info("Invalidated cache region: %s", name.value)

    def invalidate_key(self, region_name: CacheRegionName, key: str) -> None:
        """Invalidate a specific key in a region.

        Args:
            region_name: Region name enum
            key: Cache key to invalidate
        """
        region = self.get_region(region_name)
        region.delete(key)
        logger.debug("Invalidated cache key: %s in region: %s", key, region_name.value)

    def invalidate_company(
        self, company_id: str | None = None, cik: str | None = None
    ) -> None:
        """Invalidate company cache entries.

        Args:
            company_id: Optional company ID to invalidate
            cik: Optional company CIK to invalidate
        """
        if company_id:
            self.invalidate_key(CacheRegionName.COMPANY, f"company:id:{company_id}")
        if cik:
            self.invalidate_key(CacheRegionName.COMPANY, f"company:cik:{cik}")

        # Also invalidate related query cache
        self.invalidate_region(CacheRegionName.QUERY)
        logger.info("Invalidated company cache for id=%s, cik=%s", company_id, cik)

    def invalidate_filing(
        self, filing_id: str | None = None, accession_number: str | None = None
    ) -> None:
        """Invalidate filing cache entries.

        Args:
            filing_id: Optional filing ID to invalidate
            accession_number: Optional accession number to invalidate
        """
        if filing_id:
            self.invalidate_key(CacheRegionName.FILING, f"filing:id:{filing_id}")
        if accession_number:
            self.invalidate_key(
                CacheRegionName.FILING, f"filing:accession:{accession_number}"
            )

        # Also invalidate related query cache
        self.invalidate_region(CacheRegionName.QUERY)
        logger.info(
            "Invalidated filing cache for id=%s, accession=%s",
            filing_id,
            accession_number,
        )

    def invalidate_analysis(
        self, analysis_id: str | None = None, filing_id: str | None = None
    ) -> None:
        """Invalidate analysis cache entries.

        Args:
            analysis_id: Optional analysis ID to invalidate
            filing_id: Optional filing ID to invalidate all its analyses
        """
        if analysis_id:
            self.invalidate_key(CacheRegionName.ANALYSIS, f"analysis:id:{analysis_id}")
        if filing_id:
            self.invalidate_key(
                CacheRegionName.ANALYSIS, f"analysis:filing:{filing_id}"
            )

        # Also invalidate related query cache
        self.invalidate_region(CacheRegionName.QUERY)
        logger.info(
            "Invalidated analysis cache for id=%s, filing_id=%s", analysis_id, filing_id
        )

    def get_or_create(
        self,
        region_name: CacheRegionName,
        key: str,
        creator: Callable[[], Any],
        # expiration_time: int | None = None,
    ) -> Any:
        """Get value from cache or create if missing.

        Args:
            region_name: Region name enum
            key: Cache key
            creator: Function to create value if not in cache
            expiration_time: Optional custom expiration time

        Returns:
            Cached or newly created value
        """
        region = self.get_region(region_name)

        # Try to get from cache
        value = region.get(key)

        if value is NO_VALUE:
            # Not in cache, create it
            logger.debug("Cache miss for key: %s in region: %s", key, region_name.value)
            value = creator()

            # CacheRegion.set doesn't support expiration_time parameter
            # The expiration is controlled at region configuration level
            region.set(key, value)

            logger.debug(
                "Cached new value for key: %s in region: %s", key, region_name.value
            )
        else:
            logger.debug("Cache hit for key: %s in region: %s", key, region_name.value)

        return value

    async def get_or_create_async(
        self,
        region_name: CacheRegionName,
        key: str,
        creator: Callable[[], Any],
        # expiration_time: int | None = None,
    ) -> Any:
        """Async version of get_or_create for async creators.

        Args:
            region_name: Region name enum
            key: Cache key
            creator: Async function to create value if not in cache
            expiration_time: Optional custom expiration time

        Returns:
            Cached or newly created value
        """
        region = self.get_region(region_name)

        # Try to get from cache
        value = region.get(key)

        if value is NO_VALUE:
            # Not in cache, create it
            logger.debug("Cache miss for key: %s in region: %s", key, region_name.value)
            value = await creator()

            # CacheRegion.set doesn't support expiration_time parameter
            # The expiration is controlled at region configuration level
            region.set(key, value)

            logger.debug(
                "Cached new value for key: %s in region: %s", key, region_name.value
            )
        else:
            logger.debug("Cache hit for key: %s in region: %s", key, region_name.value)

        return value

    def clear_all(self) -> None:
        """Clear all cache regions."""
        for region_name in CacheRegionName:
            self.invalidate_region(region_name)
        logger.info("Cleared all cache regions")


# Global cache manager instance
cache_manager = CacheManager()
