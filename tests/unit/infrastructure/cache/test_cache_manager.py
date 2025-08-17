"""Tests for CacheManager with comprehensive coverage."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.cache.cache_manager import CacheManager


class TestCacheManagerInitialization:
    """Test cases for CacheManager initialization."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    def test_init(self, mock_redis_service):
        """Test CacheManager initialization."""
        cache_manager = CacheManager()

        assert cache_manager.redis is mock_redis_service
        assert cache_manager.COMPANY_PREFIX == "company"
        assert cache_manager.FILING_PREFIX == "filing"
        assert cache_manager.ANALYSIS_PREFIX == "analysis"
        assert cache_manager.SEARCH_PREFIX == "search"

    def test_ttl_constants(self):
        """Test TTL constants are properly defined."""
        cache_manager = CacheManager()

        assert cache_manager.COMPANY_TTL == timedelta(hours=24)
        assert cache_manager.FILING_TTL == timedelta(hours=12)
        assert cache_manager.ANALYSIS_TTL == timedelta(hours=6)
        assert cache_manager.SEARCH_TTL == timedelta(minutes=30)


class TestCacheManagerConnection:
    """Test cases for Redis connection management."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_ensure_connected_when_already_connected(self, mock_redis_service):
        """Test ensure_connected when Redis is already connected."""
        mock_redis_service._connected = True
        cache_manager = CacheManager()

        await cache_manager.ensure_connected()

        mock_redis_service.connect.assert_not_called()

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_ensure_connected_when_not_connected(self, mock_redis_service):
        """Test ensure_connected when Redis is not connected."""
        mock_redis_service._connected = False
        mock_redis_service.connect = AsyncMock()
        cache_manager = CacheManager()

        await cache_manager.ensure_connected()

        mock_redis_service.connect.assert_called_once()


class TestCacheManagerCompanyMethods:
    """Test cases for company caching methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_cache_company_success(self, mock_logger, mock_redis_service):
        """Test successful company caching."""
        # Setup
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        company_id = uuid4()
        cik = CIK("1234567890")
        company = Company(
            id=company_id,
            cik=cik,
            name="Test Company",
            metadata={"industry": "Technology"},
        )

        cache_manager = CacheManager()

        # Execute
        result = await cache_manager.cache_company(company)

        # Verify
        assert result is True

        expected_data = {
            "id": str(company_id),
            "cik": str(cik),
            "name": "Test Company",
            "metadata": {"industry": "Technology"},
        }

        # Should call set twice (by ID and by CIK)
        assert mock_redis_service.set.call_count == 2
        calls = mock_redis_service.set.call_args_list

        # Check ID-based cache call
        id_call = calls[0]
        assert id_call[0][0] == f"company:id:{company_id}"
        assert id_call[0][1] == expected_data
        assert id_call[0][2] == timedelta(hours=24)

        # Check CIK-based cache call
        cik_call = calls[1]
        assert cik_call[0][0] == f"company:cik:{cik}"
        assert cik_call[0][1] == expected_data
        assert cik_call[0][2] == timedelta(hours=24)

        mock_logger.debug.assert_called_once_with(
            f"Cached company: Test Company ({cik})"
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_company_failure(self, mock_redis_service):
        """Test company caching failure."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(
            side_effect=[True, False]
        )  # First succeeds, second fails

        company_id = uuid4()
        cik = CIK("1234567890")
        company = Company(id=company_id, cik=cik, name="Test Company", metadata={})

        cache_manager = CacheManager()
        result = await cache_manager.cache_company(company)

        assert result is False

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_company_by_id(self, mock_redis_service):
        """Test getting company by ID."""
        mock_redis_service._connected = True
        expected_data = {"id": "123", "name": "Test Company"}
        mock_redis_service.get = AsyncMock(return_value=expected_data)

        company_id = uuid4()
        cache_manager = CacheManager()

        result = await cache_manager.get_company_by_id(company_id)

        assert result == expected_data
        mock_redis_service.get.assert_called_once_with(f"company:id:{company_id}")

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_company_by_cik(self, mock_redis_service):
        """Test getting company by CIK."""
        mock_redis_service._connected = True
        expected_data = {"cik": "1234567890", "name": "Test Company"}
        mock_redis_service.get = AsyncMock(return_value=expected_data)

        cik = "1234567890"
        cache_manager = CacheManager()

        result = await cache_manager.get_company_by_cik(cik)

        assert result == expected_data
        mock_redis_service.get.assert_called_once_with(f"company:cik:{cik}")


class TestCacheManagerFilingMethods:
    """Test cases for filing caching methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_cache_filing_success(self, mock_logger, mock_redis_service):
        """Test successful filing caching."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        filing_id = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0001234567-23-000001")
        filing_date = datetime(2023, 1, 15)

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=FilingType.FORM_10K,
            filing_date=filing_date,
            processing_status=ProcessingStatus.COMPLETED,
            processing_error=None,
            metadata={"pages": 100},
        )

        cache_manager = CacheManager()
        result = await cache_manager.cache_filing(filing)

        assert result is True

        expected_data = {
            "id": str(filing_id),
            "company_id": str(company_id),
            "accession_number": str(accession_number),
            "filing_type": str(filing.filing_type),
            "filing_date": filing_date.isoformat(),
            "processing_status": "completed",
            "processing_error": None,
            "metadata": {"pages": 100},
        }

        # Should call set twice
        assert mock_redis_service.set.call_count == 2
        calls = mock_redis_service.set.call_args_list

        # Check ID-based cache call
        id_call = calls[0]
        assert id_call[0][0] == f"filing:id:{filing_id}"
        assert id_call[0][1] == expected_data
        assert id_call[0][2] == timedelta(hours=12)

        # Check accession number-based cache call
        accession_call = calls[1]
        assert accession_call[0][0] == f"filing:accession:{accession_number}"
        assert accession_call[0][1] == expected_data
        assert accession_call[0][2] == timedelta(hours=12)

        mock_logger.debug.assert_called_once_with(f"Cached filing: {accession_number}")

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_filing_by_id(self, mock_redis_service):
        """Test getting filing by ID."""
        mock_redis_service._connected = True
        expected_data = {"id": "123", "accession_number": "0001234567-23-000001"}
        mock_redis_service.get = AsyncMock(return_value=expected_data)

        filing_id = uuid4()
        cache_manager = CacheManager()

        result = await cache_manager.get_filing_by_id(filing_id)

        assert result == expected_data
        mock_redis_service.get.assert_called_once_with(f"filing:id:{filing_id}")

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_filing_by_accession(self, mock_redis_service):
        """Test getting filing by accession number."""
        mock_redis_service._connected = True
        expected_data = {"id": "123", "accession_number": "0001234567-23-000001"}
        mock_redis_service.get = AsyncMock(return_value=expected_data)

        accession_number = "0001234567-23-000001"
        cache_manager = CacheManager()

        result = await cache_manager.get_filing_by_accession(accession_number)

        assert result == expected_data
        mock_redis_service.get.assert_called_once_with(
            f"filing:accession:{accession_number}"
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_filing_content(self, mock_redis_service):
        """Test caching filing content."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        accession_number = "0001234567-23-000001"
        content = {
            "text": "Filing content",
            "sections": {"business": "Business description"},
        }

        cache_manager = CacheManager()
        result = await cache_manager.cache_filing_content(accession_number, content)

        assert result is True
        mock_redis_service.set.assert_called_once_with(
            f"filing:content:{accession_number}", content, timedelta(hours=12)
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_filing_content(self, mock_redis_service):
        """Test getting filing content."""
        mock_redis_service._connected = True
        expected_content = {"text": "Filing content"}
        mock_redis_service.get = AsyncMock(return_value=expected_content)

        accession_number = "0001234567-23-000001"
        cache_manager = CacheManager()

        result = await cache_manager.get_filing_content(accession_number)

        assert result == expected_content
        mock_redis_service.get.assert_called_once_with(
            f"filing:content:{accession_number}"
        )


class TestCacheManagerAnalysisMethods:
    """Test cases for analysis caching methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_cache_analysis_success(self, mock_logger, mock_redis_service):
        """Test successful analysis caching."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        analysis_id = uuid4()
        filing_id = uuid4()

        # Create a mock Analysis entity - we'll just mock the attributes we need
        analysis = Mock()
        analysis.id = analysis_id
        analysis.filing_id = filing_id
        analysis.analysis_type = Mock()
        analysis.analysis_type.value = "comprehensive"
        analysis.created_by = "test_user"
        analysis.results = {"summary": "Analysis results"}
        analysis.llm_provider = "openai"
        analysis.llm_model = "default"
        analysis.confidence_score = 0.95
        analysis.metadata = {"version": "1.0"}

        cache_manager = CacheManager()
        result = await cache_manager.cache_analysis(analysis)

        assert result is True

        expected_data = {
            "id": str(analysis_id),
            "filing_id": str(filing_id),
            "analysis_type": "comprehensive",
            "created_by": "test_user",
            "results": {"summary": "Analysis results"},
            "llm_provider": "openai",
            "llm_model": "default",
            "confidence_score": 0.95,
            "metadata": {"version": "1.0"},
        }

        mock_redis_service.set.assert_called_once_with(
            f"analysis:id:{analysis_id}", expected_data, timedelta(hours=6)
        )

        mock_logger.debug.assert_called_once_with(
            f"Cached analysis: {analysis_id} (comprehensive)"
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_analysis_by_id(self, mock_redis_service):
        """Test getting analysis by ID."""
        mock_redis_service._connected = True
        expected_data = {"id": "123", "results": {"summary": "Analysis"}}
        mock_redis_service.get = AsyncMock(return_value=expected_data)

        analysis_id = uuid4()
        cache_manager = CacheManager()

        result = await cache_manager.get_analysis_by_id(analysis_id)

        assert result == expected_data
        mock_redis_service.get.assert_called_once_with(f"analysis:id:{analysis_id}")

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_filing_analyses(self, mock_redis_service):
        """Test caching filing analyses."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        filing_id = uuid4()
        analyses = [
            {"id": "123", "type": "comprehensive"},
            {"id": "456", "type": "financial"},
        ]

        cache_manager = CacheManager()
        result = await cache_manager.cache_filing_analyses(filing_id, analyses)

        assert result is True
        mock_redis_service.set.assert_called_once_with(
            f"analysis:filing:{filing_id}", analyses, timedelta(hours=6)
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_filing_analyses(self, mock_redis_service):
        """Test getting filing analyses."""
        mock_redis_service._connected = True
        expected_analyses = [{"id": "123", "type": "comprehensive"}]
        mock_redis_service.get = AsyncMock(return_value=expected_analyses)

        filing_id = uuid4()
        cache_manager = CacheManager()

        result = await cache_manager.get_filing_analyses(filing_id)

        assert result == expected_analyses
        mock_redis_service.get.assert_called_once_with(f"analysis:filing:{filing_id}")


class TestCacheManagerSearchMethods:
    """Test cases for search result caching methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_search_results(self, mock_redis_service):
        """Test caching search results."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=True)

        search_key = "company:AAPL:10-K:2023"
        results = [
            {"id": "123", "accession_number": "0001234567-23-000001"},
            {"id": "456", "accession_number": "0001234567-23-000002"},
        ]

        cache_manager = CacheManager()
        result = await cache_manager.cache_search_results(search_key, results)

        assert result is True
        mock_redis_service.set.assert_called_once_with(
            f"search:{search_key}", results, timedelta(minutes=30)
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_search_results(self, mock_redis_service):
        """Test getting search results."""
        mock_redis_service._connected = True
        expected_results = [{"id": "123", "accession_number": "0001234567-23-000001"}]
        mock_redis_service.get = AsyncMock(return_value=expected_results)

        search_key = "company:AAPL:10-K:2023"
        cache_manager = CacheManager()

        result = await cache_manager.get_search_results(search_key)

        assert result == expected_results
        mock_redis_service.get.assert_called_once_with(f"search:{search_key}")


class TestCacheManagerInvalidationMethods:
    """Test cases for cache invalidation methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_invalidate_company(self, mock_logger, mock_redis_service):
        """Test invalidating company cache."""
        mock_redis_service._connected = True
        mock_redis_service.clear_pattern = AsyncMock(
            side_effect=[1, 2, 3]
        )  # Return different counts

        company_id = uuid4()
        cik = "1234567890"

        cache_manager = CacheManager()
        result = await cache_manager.invalidate_company(company_id, cik)

        assert result is True

        # Should call clear_pattern for each pattern
        expected_patterns = [
            f"company:id:{company_id}",
            f"company:cik:{cik}",
            f"filing:company:{company_id}:*",
        ]

        assert mock_redis_service.clear_pattern.call_count == 3
        for i, call in enumerate(mock_redis_service.clear_pattern.call_args_list):
            assert call[0][0] == expected_patterns[i]

        mock_logger.info.assert_called_once_with(
            f"Invalidated 6 cache entries for company {cik}"
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_invalidate_company_no_deletions(self, mock_redis_service):
        """Test invalidating company cache with no deletions."""
        mock_redis_service._connected = True
        mock_redis_service.clear_pattern = AsyncMock(return_value=0)

        company_id = uuid4()
        cik = "1234567890"

        cache_manager = CacheManager()
        result = await cache_manager.invalidate_company(company_id, cik)

        assert result is False

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_invalidate_filing(self, mock_logger, mock_redis_service):
        """Test invalidating filing cache."""
        mock_redis_service._connected = True
        mock_redis_service.clear_pattern = AsyncMock(side_effect=[2, 1, 1, 3])

        filing_id = uuid4()
        accession_number = "0001234567-23-000001"

        cache_manager = CacheManager()
        result = await cache_manager.invalidate_filing(filing_id, accession_number)

        assert result is True

        expected_patterns = [
            f"filing:id:{filing_id}",
            f"filing:accession:{accession_number}",
            f"filing:content:{accession_number}",
            f"analysis:filing:{filing_id}",
        ]

        assert mock_redis_service.clear_pattern.call_count == 4
        for i, call in enumerate(mock_redis_service.clear_pattern.call_args_list):
            assert call[0][0] == expected_patterns[i]

        mock_logger.info.assert_called_once_with(
            f"Invalidated 7 cache entries for filing {accession_number}"
        )


class TestCacheManagerUtilityMethods:
    """Test cases for utility methods."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_clear_all_cache(self, mock_logger, mock_redis_service):
        """Test clearing all cache data."""
        mock_redis_service._connected = True
        mock_redis_service.clear_pattern = AsyncMock(side_effect=[10, 20, 15, 5])

        cache_manager = CacheManager()
        result = await cache_manager.clear_all_cache()

        assert result == 50

        expected_patterns = ["company:*", "filing:*", "analysis:*", "search:*"]

        assert mock_redis_service.clear_pattern.call_count == 4
        for i, call in enumerate(mock_redis_service.clear_pattern.call_args_list):
            assert call[0][0] == expected_patterns[i]

        mock_logger.info.assert_called_once_with("Cleared 50 cache entries")

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_get_cache_stats_success(self, mock_logger, mock_redis_service):
        """Test getting cache statistics successfully."""
        mock_redis_service._connected = True

        # Mock Redis keys method
        mock_redis_service._redis = Mock()
        mock_redis_service._redis.keys = AsyncMock(
            side_effect=[
                ["company:id:123", "company:cik:456"],  # company keys
                ["filing:id:789"],  # filing keys
                [],  # analysis keys
                ["search:key1", "search:key2", "search:key3"],  # search keys
            ]
        )

        # Mock Redis info method
        mock_redis_service._redis.info = AsyncMock(
            return_value={
                "used_memory_human": "10.5M",
                "connected_clients": 5,
                "total_commands_processed": 1000,
            }
        )

        cache_manager = CacheManager()
        result = await cache_manager.get_cache_stats()

        expected_stats = {
            "company_count": 2,
            "filing_count": 1,
            "analysis_count": 0,
            "search_count": 3,
            "redis_memory_used": "10.5M",
            "redis_connected_clients": 5,
            "redis_total_commands_processed": 1000,
        }

        assert result == expected_stats

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    @patch('src.infrastructure.cache.cache_manager.logger')
    async def test_get_cache_stats_redis_error(self, mock_logger, mock_redis_service):
        """Test getting cache statistics with Redis error."""
        mock_redis_service._connected = True

        # Mock Redis keys method
        mock_redis_service._redis = Mock()
        mock_redis_service._redis.keys = AsyncMock(
            side_effect=[
                ["company:id:123"],  # company keys
                [],  # filing keys
                [],  # analysis keys
                [],  # search keys
            ]
        )

        # Mock Redis info method to raise exception
        mock_redis_service._redis.info = AsyncMock(
            side_effect=Exception("Redis connection lost")
        )

        cache_manager = CacheManager()
        result = await cache_manager.get_cache_stats()

        expected_stats = {
            "company_count": 1,
            "filing_count": 0,
            "analysis_count": 0,
            "search_count": 0,
        }

        assert result == expected_stats
        mock_logger.warning.assert_called_once_with(
            "Could not get Redis info: Redis connection lost"
        )


class TestCacheManagerErrorHandling:
    """Test cases for error handling scenarios."""

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_company_redis_connection_error(self, mock_redis_service):
        """Test company caching with Redis connection error."""
        mock_redis_service._connected = False
        mock_redis_service.connect = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        company_id = uuid4()
        cik = CIK("1234567890")
        company = Company(id=company_id, cik=cik, name="Test Company", metadata={})

        cache_manager = CacheManager()

        # Should raise the connection exception
        with pytest.raises(Exception, match="Connection failed"):
            await cache_manager.cache_company(company)

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_get_company_by_id_not_found(self, mock_redis_service):
        """Test getting company by ID when not found."""
        mock_redis_service._connected = True
        mock_redis_service.get = AsyncMock(return_value=None)

        company_id = uuid4()
        cache_manager = CacheManager()

        result = await cache_manager.get_company_by_id(company_id)

        assert result is None

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_ensure_connected_already_connected(self, mock_redis_service):
        """Test ensure_connected when already connected."""
        mock_redis_service._connected = True
        cache_manager = CacheManager()

        await cache_manager.ensure_connected()

        # Should not call connect since already connected
        assert (
            not hasattr(mock_redis_service, 'connect')
            or not mock_redis_service.connect.called
        )

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_filing_partial_failure(self, mock_redis_service):
        """Test filing caching with partial failure."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(
            side_effect=[True, False]
        )  # First succeeds, second fails

        filing_id = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0001234567-23-000001")
        filing_date = datetime(2023, 1, 15)

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=FilingType.FORM_10K,
            filing_date=filing_date,
            processing_status=ProcessingStatus.COMPLETED,
            processing_error=None,
            metadata={},
        )

        cache_manager = CacheManager()
        result = await cache_manager.cache_filing(filing)

        # Should return False if any cache operation fails
        assert result is False

    @patch('src.infrastructure.cache.cache_manager.redis_service')
    async def test_cache_analysis_failure(self, mock_redis_service):
        """Test analysis caching failure."""
        mock_redis_service._connected = True
        mock_redis_service.set = AsyncMock(return_value=False)

        analysis = Mock()
        analysis.id = uuid4()
        analysis.filing_id = uuid4()
        analysis.analysis_type = Mock()
        analysis.analysis_type.value = "comprehensive"
        analysis.created_by = "test_user"
        analysis.results = {}
        analysis.llm_provider = "openai"
        analysis.llm_model = "default"
        analysis.confidence_score = 0.95
        analysis.metadata = {}

        cache_manager = CacheManager()
        result = await cache_manager.cache_analysis(analysis)

        assert result is False


class TestCacheManagerGlobalInstance:
    """Test cases for the global cache manager instance."""

    def test_global_cache_manager_instance(self):
        """Test that the global cache manager instance is properly created."""
        from src.infrastructure.cache.cache_manager import cache_manager

        assert isinstance(cache_manager, CacheManager)
        assert hasattr(cache_manager, 'redis')
        assert hasattr(cache_manager, 'COMPANY_PREFIX')
        assert hasattr(cache_manager, 'FILING_PREFIX')
        assert hasattr(cache_manager, 'ANALYSIS_PREFIX')
        assert hasattr(cache_manager, 'SEARCH_PREFIX')
