"""Cache manager for filing and analysis data."""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from src.domain.entities.analysis import Analysis
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.infrastructure.cache.redis_service import redis_service

logger = logging.getLogger(__name__)


class CacheManager:
    """High-level cache manager for Aperilex entities."""

    # Cache key prefixes
    COMPANY_PREFIX = "company"
    FILING_PREFIX = "filing"
    ANALYSIS_PREFIX = "analysis"
    SEARCH_PREFIX = "search"

    # Default TTL values
    COMPANY_TTL = timedelta(hours=24)  # Companies change infrequently
    FILING_TTL = timedelta(hours=12)  # Filings are fairly static
    ANALYSIS_TTL = timedelta(hours=6)  # Analysis results can be cached shorter
    SEARCH_TTL = timedelta(minutes=30)  # Search results expire quickly

    def __init__(self) -> None:
        """Initialize cache manager."""
        self.redis = redis_service

    async def ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if not self.redis._connected:
            await self.redis.connect()

    # Company caching methods
    async def cache_company(self, company: Company) -> bool:
        """
        Cache a company entity.

        Args:
            company: Company entity to cache

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()

        key = f"{self.COMPANY_PREFIX}:id:{company.id}"
        cik_key = f"{self.COMPANY_PREFIX}:cik:{company.cik}"

        company_data = {
            "id": str(company.id),
            "cik": str(company.cik),
            "name": company.name,
            "metadata": company.metadata,
        }

        # Cache by both ID and CIK
        success1 = await self.redis.set(key, company_data, self.COMPANY_TTL)
        success2 = await self.redis.set(cik_key, company_data, self.COMPANY_TTL)

        if success1 and success2:
            logger.debug(f"Cached company: {company.name} ({company.cik})")

        return success1 and success2

    async def get_company_by_id(self, company_id: UUID) -> dict[str, Any] | None:
        """Get cached company by ID."""
        await self.ensure_connected()
        key = f"{self.COMPANY_PREFIX}:id:{company_id}"
        return await self.redis.get(key)

    async def get_company_by_cik(self, cik: str) -> dict[str, Any] | None:
        """Get cached company by CIK."""
        await self.ensure_connected()
        key = f"{self.COMPANY_PREFIX}:cik:{cik}"
        return await self.redis.get(key)

    # Filing caching methods
    async def cache_filing(self, filing: Filing) -> bool:
        """
        Cache a filing entity.

        Args:
            filing: Filing entity to cache

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()

        key = f"{self.FILING_PREFIX}:id:{filing.id}"
        accession_key = f"{self.FILING_PREFIX}:accession:{filing.accession_number}"

        filing_data = {
            "id": str(filing.id),
            "company_id": str(filing.company_id),
            "accession_number": str(filing.accession_number),
            "filing_type": str(filing.filing_type),
            "filing_date": filing.filing_date.isoformat(),
            "processing_status": filing.processing_status.value,
            "processing_error": filing.processing_error,
            "metadata": filing.metadata,
        }

        # Cache by both ID and accession number
        success1 = await self.redis.set(key, filing_data, self.FILING_TTL)
        success2 = await self.redis.set(accession_key, filing_data, self.FILING_TTL)

        if success1 and success2:
            logger.debug(f"Cached filing: {filing.accession_number}")

        return success1 and success2

    async def get_filing_by_id(self, filing_id: UUID) -> dict[str, Any] | None:
        """Get cached filing by ID."""
        await self.ensure_connected()
        key = f"{self.FILING_PREFIX}:id:{filing_id}"
        return await self.redis.get(key)

    async def get_filing_by_accession(
        self, accession_number: str
    ) -> dict[str, Any] | None:
        """Get cached filing by accession number."""
        await self.ensure_connected()
        key = f"{self.FILING_PREFIX}:accession:{accession_number}"
        return await self.redis.get(key)

    async def cache_filing_content(
        self, accession_number: str, content: dict[str, Any]
    ) -> bool:
        """
        Cache filing content (text, sections, etc.).

        Args:
            accession_number: Filing accession number
            content: Filing content data

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()
        key = f"{self.FILING_PREFIX}:content:{accession_number}"
        return await self.redis.set(key, content, self.FILING_TTL)

    async def get_filing_content(self, accession_number: str) -> dict[str, Any] | None:
        """Get cached filing content."""
        await self.ensure_connected()
        key = f"{self.FILING_PREFIX}:content:{accession_number}"
        return await self.redis.get(key)

    # Analysis caching methods
    async def cache_analysis(self, analysis: Analysis) -> bool:
        """
        Cache an analysis entity.

        Args:
            analysis: Analysis entity to cache

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()

        key = f"{self.ANALYSIS_PREFIX}:id:{analysis.id}"

        analysis_data = {
            "id": str(analysis.id),
            "filing_id": str(analysis.filing_id),
            "analysis_type": analysis.analysis_type.value,
            "created_by": analysis.created_by,
            "results": analysis.results,
            "llm_provider": analysis.llm_provider,
            "llm_model": analysis.llm_model,
            "confidence_score": analysis.confidence_score,
            "metadata": analysis.metadata,
        }

        success = await self.redis.set(key, analysis_data, self.ANALYSIS_TTL)

        if success:
            logger.debug(
                f"Cached analysis: {analysis.id} ({analysis.analysis_type.value})"
            )

        return success

    async def get_analysis_by_id(self, analysis_id: UUID) -> dict[str, Any] | None:
        """Get cached analysis by ID."""
        await self.ensure_connected()
        key = f"{self.ANALYSIS_PREFIX}:id:{analysis_id}"
        return await self.redis.get(key)

    async def cache_filing_analyses(
        self, filing_id: UUID, analyses: list[dict[str, Any]]
    ) -> bool:
        """
        Cache all analyses for a filing.

        Args:
            filing_id: Filing ID
            analyses: List of analysis data

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()
        key = f"{self.ANALYSIS_PREFIX}:filing:{filing_id}"
        return await self.redis.set(key, analyses, self.ANALYSIS_TTL)

    async def get_filing_analyses(self, filing_id: UUID) -> list[dict[str, Any]] | None:
        """Get cached analyses for a filing."""
        await self.ensure_connected()
        key = f"{self.ANALYSIS_PREFIX}:filing:{filing_id}"
        return await self.redis.get(key)

    # Search result caching
    async def cache_search_results(
        self, search_key: str, results: list[dict[str, Any]]
    ) -> bool:
        """
        Cache search results.

        Args:
            search_key: Unique key for the search query
            results: Search results to cache

        Returns:
            True if cached successfully
        """
        await self.ensure_connected()
        key = f"{self.SEARCH_PREFIX}:{search_key}"
        return await self.redis.set(key, results, self.SEARCH_TTL)

    async def get_search_results(self, search_key: str) -> list[dict[str, Any]] | None:
        """Get cached search results."""
        await self.ensure_connected()
        key = f"{self.SEARCH_PREFIX}:{search_key}"
        return await self.redis.get(key)

    # Cache management methods
    async def invalidate_company(self, company_id: UUID, cik: str) -> bool:
        """
        Invalidate all cached data for a company.

        Args:
            company_id: Company ID
            cik: Company CIK

        Returns:
            True if invalidation was successful
        """
        await self.ensure_connected()

        patterns = [
            f"{self.COMPANY_PREFIX}:id:{company_id}",
            f"{self.COMPANY_PREFIX}:cik:{cik}",
            f"{self.FILING_PREFIX}:company:{company_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Invalidated {total_deleted} cache entries for company {cik}")
        return total_deleted > 0

    async def invalidate_filing(self, filing_id: UUID, accession_number: str) -> bool:
        """
        Invalidate all cached data for a filing.

        Args:
            filing_id: Filing ID
            accession_number: Filing accession number

        Returns:
            True if invalidation was successful
        """
        await self.ensure_connected()

        patterns = [
            f"{self.FILING_PREFIX}:id:{filing_id}",
            f"{self.FILING_PREFIX}:accession:{accession_number}",
            f"{self.FILING_PREFIX}:content:{accession_number}",
            f"{self.ANALYSIS_PREFIX}:filing:{filing_id}",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(
            f"Invalidated {total_deleted} cache entries for filing {accession_number}"
        )
        return total_deleted > 0

    async def clear_all_cache(self) -> int:
        """
        Clear all Aperilex cache data.

        Returns:
            Number of keys deleted
        """
        await self.ensure_connected()

        patterns = [
            f"{self.COMPANY_PREFIX}:*",
            f"{self.FILING_PREFIX}:*",
            f"{self.ANALYSIS_PREFIX}:*",
            f"{self.SEARCH_PREFIX}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Cleared {total_deleted} cache entries")
        return total_deleted

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        await self.ensure_connected()

        stats = {}

        # Count keys by prefix
        for prefix in [
            self.COMPANY_PREFIX,
            self.FILING_PREFIX,
            self.ANALYSIS_PREFIX,
            self.SEARCH_PREFIX,
        ]:
            pattern = f"{prefix}:*"
            keys = await self.redis._redis.keys(pattern)
            stats[f"{prefix}_count"] = len(keys)

        # Get Redis info
        try:
            info = await self.redis._redis.info()
            stats.update(
                {
                    "redis_memory_used": info.get("used_memory_human", "N/A"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_total_commands_processed": info.get(
                        "total_commands_processed", 0
                    ),
                }
            )
        except Exception as e:
            logger.warning(f"Could not get Redis info: {str(e)}")

        return stats


# Global cache manager instance
cache_manager = CacheManager()
