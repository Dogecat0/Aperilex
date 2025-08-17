"""Generic cache manager that works with any storage backend."""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from src.domain.entities.analysis import Analysis
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.infrastructure.messaging import get_storage_service

logger = logging.getLogger(__name__)


class GenericCacheManager:
    """Cache manager that uses the generic storage interface."""

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

    async def _get_storage(self):
        """Get the storage service instance."""
        return await get_storage_service()

    # Company caching methods
    async def cache_company(self, company: Company) -> bool:
        """
        Cache a company entity.

        Args:
            company: Company entity to cache

        Returns:
            True if cached successfully
        """
        storage = await self._get_storage()

        key = f"{self.COMPANY_PREFIX}:id:{company.id}"
        cik_key = f"{self.COMPANY_PREFIX}:cik:{company.cik}"

        company_data = {
            "id": str(company.id),
            "cik": str(company.cik),
            "name": company.name,
            "metadata": company.metadata,
        }

        # Cache by both ID and CIK
        success1 = await storage.set(key, company_data, self.COMPANY_TTL)
        success2 = await storage.set(cik_key, company_data, self.COMPANY_TTL)

        if success1 and success2:
            logger.debug(f"Cached company: {company.name} ({company.cik})")

        return success1 and success2

    async def get_company_by_id(self, company_id: UUID) -> dict[str, Any] | None:
        """Get cached company by ID."""
        storage = await self._get_storage()
        key = f"{self.COMPANY_PREFIX}:id:{company_id}"
        return await storage.get(key)

    async def get_company_by_cik(self, cik: str) -> dict[str, Any] | None:
        """Get cached company by CIK."""
        storage = await self._get_storage()
        key = f"{self.COMPANY_PREFIX}:cik:{cik}"
        return await storage.get(key)

    # Filing caching methods
    async def cache_filing(self, filing: Filing) -> bool:
        """
        Cache a filing entity.

        Args:
            filing: Filing entity to cache

        Returns:
            True if cached successfully
        """
        storage = await self._get_storage()

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
        success1 = await storage.set(key, filing_data, self.FILING_TTL)
        success2 = await storage.set(accession_key, filing_data, self.FILING_TTL)

        if success1 and success2:
            logger.debug(f"Cached filing: {filing.accession_number}")

        return success1 and success2

    async def get_filing_by_id(self, filing_id: UUID) -> dict[str, Any] | None:
        """Get cached filing by ID."""
        storage = await self._get_storage()
        key = f"{self.FILING_PREFIX}:id:{filing_id}"
        return await storage.get(key)

    async def get_filing_by_accession(
        self, accession_number: str
    ) -> dict[str, Any] | None:
        """Get cached filing by accession number."""
        storage = await self._get_storage()
        key = f"{self.FILING_PREFIX}:accession:{accession_number}"
        return await storage.get(key)

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
        storage = await self._get_storage()
        key = f"{self.FILING_PREFIX}:content:{accession_number}"
        return await storage.set(key, content, self.FILING_TTL)

    async def get_filing_content(self, accession_number: str) -> dict[str, Any] | None:
        """Get cached filing content."""
        storage = await self._get_storage()
        key = f"{self.FILING_PREFIX}:content:{accession_number}"
        return await storage.get(key)

    # Analysis caching methods
    async def cache_analysis(self, analysis: Analysis) -> bool:
        """
        Cache an analysis entity.

        Args:
            analysis: Analysis entity to cache

        Returns:
            True if cached successfully
        """
        storage = await self._get_storage()

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

        success = await storage.set(key, analysis_data, self.ANALYSIS_TTL)

        if success:
            logger.debug(
                f"Cached analysis: {analysis.id} ({analysis.analysis_type.value})"
            )

        return success

    async def get_analysis_by_id(self, analysis_id: UUID) -> dict[str, Any] | None:
        """Get cached analysis by ID."""
        storage = await self._get_storage()
        key = f"{self.ANALYSIS_PREFIX}:id:{analysis_id}"
        return await storage.get(key)

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
        storage = await self._get_storage()
        key = f"{self.ANALYSIS_PREFIX}:filing:{filing_id}"
        return await storage.set(key, analyses, self.ANALYSIS_TTL)

    async def get_filing_analyses(self, filing_id: UUID) -> list[dict[str, Any]] | None:
        """Get cached analyses for a filing."""
        storage = await self._get_storage()
        key = f"{self.ANALYSIS_PREFIX}:filing:{filing_id}"
        return await storage.get(key)

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
        storage = await self._get_storage()
        key = f"{self.SEARCH_PREFIX}:{search_key}"
        return await storage.set(key, results, self.SEARCH_TTL)

    async def get_search_results(self, search_key: str) -> list[dict[str, Any]] | None:
        """Get cached search results."""
        storage = await self._get_storage()
        key = f"{self.SEARCH_PREFIX}:{search_key}"
        return await storage.get(key)

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
        storage = await self._get_storage()

        patterns = [
            f"{self.COMPANY_PREFIX}:id:{company_id}",
            f"{self.COMPANY_PREFIX}:cik:{cik}",
            f"{self.FILING_PREFIX}:company:{company_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await storage.clear_pattern(pattern)
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
        storage = await self._get_storage()

        patterns = [
            f"{self.FILING_PREFIX}:id:{filing_id}",
            f"{self.FILING_PREFIX}:accession:{accession_number}",
            f"{self.FILING_PREFIX}:content:{accession_number}",
            f"{self.ANALYSIS_PREFIX}:filing:{filing_id}",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await storage.clear_pattern(pattern)
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
        storage = await self._get_storage()

        patterns = [
            f"{self.COMPANY_PREFIX}:*",
            f"{self.FILING_PREFIX}:*",
            f"{self.ANALYSIS_PREFIX}:*",
            f"{self.SEARCH_PREFIX}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await storage.clear_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Cleared {total_deleted} cache entries")
        return total_deleted

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        storage = await self._get_storage()

        # Basic health check
        is_healthy = await storage.health_check()

        stats = {
            "storage_healthy": is_healthy,
            "storage_type": type(storage).__name__,
        }

        # Try to get additional stats if available
        if hasattr(storage, 'get_stats'):
            try:
                additional_stats = storage.get_stats()
                if hasattr(additional_stats, '__await__'):
                    additional_stats = await additional_stats
                stats.update(additional_stats)
            except Exception as e:
                logger.warning(f"Could not get storage stats: {str(e)}")

        return stats


# Global cache manager instance
cache_manager = GenericCacheManager()
