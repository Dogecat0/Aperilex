"""Tests for caching decorators."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.decorators.caching import (
    _default_key_extractor,
    cache_invalidation,
    cached_query,
)
from src.application.services.cache_service import CacheService
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class MockQuery:
    """Mock query class for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockAnalysisResult:
    """Mock analysis result for testing."""

    def __init__(self, analysis_id: UUID):
        self.id = analysis_id


class MockHandler:
    """Mock handler class for decorator testing."""

    def __init__(self, cache_service: CacheService = None):
        self.cache_service = cache_service


class TestDefaultKeyExtractor:
    """Test _default_key_extractor function."""

    def test_key_extractor_basic_query(self) -> None:
        """Test key extraction from basic query."""
        query = MockQuery(analysis_id="test-id-123")

        result = _default_key_extractor("analysis", query)

        assert result == "analysis:analysis_id:test-id-123"

    def test_key_extractor_filing_query(self) -> None:
        """Test key extraction from filing query."""
        query = MockQuery(filing_id=str(uuid4()), include_analyses=True)

        result = _default_key_extractor("filing", query)

        expected = f"filing:filing_id:{query.filing_id}:include_analyses:true"
        assert result == expected

    def test_key_extractor_multiple_id_attributes(self) -> None:
        """Test that first available ID attribute is used."""
        query = MockQuery(
            analysis_id="analysis-123",
            filing_id="filing-456",  # Should not be used
            company_id="company-789",  # Should not be used
        )

        result = _default_key_extractor("test", query)

        assert result == "test:analysis_id:analysis-123"

    def test_key_extractor_no_id_attributes(self) -> None:
        """Test key extraction without ID attributes."""
        query = MockQuery(include_full_results=True)

        result = _default_key_extractor("test", query)

        assert result == "test:include_full_results:true"

    def test_key_extractor_pagination(self) -> None:
        """Test key extraction with pagination."""
        query = MockQuery(page=2, page_size=25)

        result = _default_key_extractor("list", query)

        assert result == "list:page:2:size:25"

    def test_key_extractor_company_filter(self) -> None:
        """Test key extraction with company filter."""
        query = MockQuery(company_cik=CIK("1234567890"))

        result = _default_key_extractor("list", query)

        assert result == "list:cik:1234567890"

    def test_key_extractor_analysis_types_filter(self) -> None:
        """Test key extraction with analysis types filter."""
        query = MockQuery(analysis_types=[AnalysisType.FILING_ANALYSIS])

        result = _default_key_extractor("list", query)

        assert result == "list:types:filing_analysis"

    def test_key_extractor_multiple_analysis_types(self) -> None:
        """Test key extraction with multiple analysis types (sorted)."""
        query = MockQuery(
            analysis_types=[AnalysisType.FILING_ANALYSIS, AnalysisType.FILING_ANALYSIS]
        )

        result = _default_key_extractor("list", query)

        # Types should be sorted for consistent keys
        assert "types:" in result
        assert "filing_analysis" in result

    def test_key_extractor_date_filters(self) -> None:
        """Test key extraction with date filters."""
        created_from = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        created_to = datetime(2024, 3, 31, 15, 30, tzinfo=UTC)

        query = MockQuery(created_from=created_from, created_to=created_to)

        result = _default_key_extractor("list", query)

        assert "from:2024-01-01" in result
        assert "to:2024-03-31" in result

    def test_key_extractor_sorting(self) -> None:
        """Test key extraction with sorting parameters."""
        from src.application.schemas.queries.list_analyses import (
            AnalysisSortField,
            SortDirection,
        )

        query = MockQuery(
            sort_by=AnalysisSortField.CREATED_AT, sort_direction=SortDirection.DESC
        )

        result = _default_key_extractor("list", query)

        assert "sort:created_at:desc" in result

    def test_key_extractor_comprehensive_query(self) -> None:
        """Test key extraction with all parameters."""
        query = MockQuery(
            analysis_id="test-123",
            include_full_results=True,
            include_analyses=False,  # Should not appear in key
            page=1,
            page_size=10,
            company_cik=CIK("1234567890"),
        )

        result = _default_key_extractor("comprehensive", query)

        expected_parts = [
            "comprehensive",
            "analysis_id:test-123",
            "include_full_results:true",
            "page:1",
            "size:10",
            "cik:1234567890",
        ]

        for part in expected_parts:
            assert part in result

        # include_analyses should not appear since it's False
        assert "include_analyses" not in result


class TestCachedQueryDecorator:
    """Test @cached_query decorator."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock CacheService."""
        return AsyncMock(spec=CacheService)

    @pytest.fixture
    def handler_with_cache(self, mock_cache_service: AsyncMock) -> MockHandler:
        """Mock handler with cache service."""
        return MockHandler(cache_service=mock_cache_service)

    @pytest.fixture
    def handler_without_cache(self) -> MockHandler:
        """Mock handler without cache service."""
        return MockHandler(cache_service=None)

    @pytest.mark.asyncio
    async def test_cached_query_cache_hit(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with cache hit."""
        cached_result = {"cached": "data"}
        mock_cache_service.get.return_value = cached_result

        @cached_query("test", ttl_minutes=30)
        async def mock_query_method(self, query):
            return {"fresh": "data"}

        query = MockQuery(analysis_id="test-123")
        result = await mock_query_method(handler_with_cache, query)

        assert result == cached_result
        mock_cache_service.get.assert_called_once_with("test:analysis_id:test-123")
        mock_cache_service.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cached_query_cache_miss(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with cache miss."""
        fresh_result = {"fresh": "data"}
        mock_cache_service.get.return_value = None  # Cache miss

        @cached_query("test", ttl_minutes=30)
        async def mock_query_method(self, query):
            return fresh_result

        query = MockQuery(analysis_id="test-123")
        result = await mock_query_method(handler_with_cache, query)

        assert result == fresh_result
        mock_cache_service.get.assert_called_once_with("test:analysis_id:test-123")
        mock_cache_service.set.assert_called_once_with(
            "test:analysis_id:test-123", fresh_result, ttl=timedelta(minutes=30)
        )

    @pytest.mark.asyncio
    async def test_cached_query_no_cache_service(
        self,
        handler_without_cache: MockHandler,
    ) -> None:
        """Test cached query without cache service."""
        fresh_result = {"no_cache": "data"}

        @cached_query("test")
        async def mock_query_method(self, query):
            return fresh_result

        query = MockQuery(analysis_id="test-123")

        with patch('src.application.decorators.caching.logger') as mock_logger:
            result = await mock_query_method(handler_without_cache, query)

        assert result == fresh_result
        mock_logger.debug.assert_called_once()
        assert "No cache service available" in mock_logger.debug.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cached_query_custom_key_extractor(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with custom key extractor."""
        mock_cache_service.get.return_value = None
        fresh_result = {"custom": "data"}

        def custom_extractor(query):
            return f"custom_{query.special_id}"

        @cached_query("test", key_extractor=custom_extractor)
        async def mock_query_method(self, query):
            return fresh_result

        query = MockQuery(special_id="unique-123")
        result = await mock_query_method(handler_with_cache, query)

        assert result == fresh_result
        mock_cache_service.get.assert_called_once_with("test:custom_unique-123")
        mock_cache_service.set.assert_called_once_with(
            "test:custom_unique-123",
            fresh_result,
            ttl=timedelta(minutes=60),  # Default TTL
        )

    @pytest.mark.asyncio
    async def test_cached_query_cache_error_fallback(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with cache error fallback."""
        mock_cache_service.get.side_effect = Exception("Cache connection failed")
        fresh_result = {"fallback": "data"}

        @cached_query("test")
        async def mock_query_method(self, query):
            return fresh_result

        query = MockQuery(analysis_id="test-123")

        with patch('src.application.decorators.caching.logger') as mock_logger:
            result = await mock_query_method(handler_with_cache, query)

        assert result == fresh_result
        mock_logger.warning.assert_called_once()
        assert "Caching error" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cached_query_set_error_fallback(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with cache set error fallback."""
        mock_cache_service.get.return_value = None
        mock_cache_service.set.side_effect = Exception("Cache write failed")
        fresh_result = {"set_error": "data"}

        @cached_query("test")
        async def mock_query_method(self, query):
            return fresh_result

        query = MockQuery(analysis_id="test-123")

        with patch('src.application.decorators.caching.logger') as mock_logger:
            result = await mock_query_method(handler_with_cache, query)

        assert result == fresh_result
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_query_preserves_function_metadata(self) -> None:
        """Test that decorator preserves original function metadata."""

        @cached_query("test")
        async def original_function(self, query):
            """Original function docstring."""
            return "result"

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original function docstring."

    @pytest.mark.asyncio
    async def test_cached_query_different_ttl_values(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with different TTL values."""
        mock_cache_service.get.return_value = None
        result_data = {"ttl_test": "data"}

        ttl_values = [15, 60, 120, 1440]  # 15min, 1hr, 2hr, 1day

        for ttl_minutes in ttl_values:

            @cached_query("test", ttl_minutes=ttl_minutes)
            async def mock_query_method(self, query):
                return result_data

            query = MockQuery(analysis_id=f"test-{ttl_minutes}")
            await mock_query_method(handler_with_cache, query)

            # Verify TTL was set correctly
            set_call = mock_cache_service.set.call_args
            assert set_call[1]["ttl"] == timedelta(minutes=ttl_minutes)

            # Reset mock for next iteration
            mock_cache_service.reset_mock()

    @pytest.mark.asyncio
    async def test_cached_query_with_complex_query_object(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cached query with complex query object."""
        mock_cache_service.get.return_value = None
        result_data = {"complex": "data"}

        @cached_query("list")
        async def mock_query_method(self, query):
            return result_data

        # Complex query with multiple parameters
        query = MockQuery(
            company_cik=CIK("1234567890"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            page=2,
            page_size=50,
            include_full_results=True,
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
        )

        result = await mock_query_method(handler_with_cache, query)

        assert result == result_data

        # Verify complex cache key was generated
        get_call = mock_cache_service.get.call_args[0][0]
        assert "cik:1234567890" in get_call
        assert "types:filing_analysis" in get_call
        assert "page:2" in get_call
        assert "size:50" in get_call
        assert "include_full_results:true" in get_call
        assert "from:2024-01-01" in get_call


class TestCacheInvalidationDecorator:
    """Test @cache_invalidation decorator."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock CacheService."""
        return AsyncMock(spec=CacheService)

    @pytest.fixture
    def handler_with_cache(self, mock_cache_service: AsyncMock) -> MockHandler:
        """Mock handler with cache service."""
        return MockHandler(cache_service=mock_cache_service)

    @pytest.fixture
    def handler_without_cache(self) -> MockHandler:
        """Mock handler without cache service."""
        return MockHandler(cache_service=None)

    @pytest.mark.asyncio
    async def test_cache_invalidation_with_result_id(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cache invalidation with result containing ID."""
        analysis_id = uuid4()
        command_result = MockAnalysisResult(analysis_id)

        @cache_invalidation(["analysis", "filing"])
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery(some_param="value")
        result = await mock_command_method(handler_with_cache, command)

        assert result == command_result

        # Verify cache invalidation calls
        expected_calls = [f"analysis:{analysis_id}", f"filing:{analysis_id}"]

        clear_calls = [
            call[0][0] for call in mock_cache_service.clear_prefix.call_args_list
        ]
        for expected_call in expected_calls:
            assert expected_call in clear_calls

    @pytest.mark.asyncio
    async def test_cache_invalidation_custom_id_extractor(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cache invalidation with custom ID extractor."""
        target_id = uuid4()
        command_result = {"entity": {"custom_id": target_id}}

        def custom_id_extractor(result):
            return result["entity"]["custom_id"]

        @cache_invalidation(["analysis"], id_extractor=custom_id_extractor)
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery()
        result = await mock_command_method(handler_with_cache, command)

        assert result == command_result
        mock_cache_service.clear_prefix.assert_called_once_with(f"analysis:{target_id}")

    @pytest.mark.asyncio
    async def test_cache_invalidation_no_id_found(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cache invalidation when no ID is found."""
        command_result = {"no": "id"}

        @cache_invalidation(["analysis", "filing"])
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery()
        result = await mock_command_method(handler_with_cache, command)

        assert result == command_result

        # Should clear entire prefixes when no ID is found
        expected_calls = ["analysis", "filing"]
        clear_calls = [
            call[0][0] for call in mock_cache_service.clear_prefix.call_args_list
        ]
        for expected_call in expected_calls:
            assert expected_call in clear_calls

    @pytest.mark.asyncio
    async def test_cache_invalidation_no_cache_service(
        self,
        handler_without_cache: MockHandler,
    ) -> None:
        """Test cache invalidation without cache service."""
        command_result = {"no_cache": "result"}

        @cache_invalidation(["analysis"])
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery()
        result = await mock_command_method(handler_without_cache, command)

        assert result == command_result
        # No assertion needed - just shouldn't raise error

    @pytest.mark.asyncio
    async def test_cache_invalidation_error_handling(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cache invalidation with cache service error."""
        mock_cache_service.clear_prefix.side_effect = Exception("Cache clear failed")
        command_result = MockAnalysisResult(uuid4())

        @cache_invalidation(["analysis"])
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery()

        with patch('src.application.decorators.caching.logger') as mock_logger:
            result = await mock_command_method(handler_with_cache, command)

        assert result == command_result
        mock_logger.warning.assert_called_once()
        assert "Cache invalidation error" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cache_invalidation_preserves_function_metadata(self) -> None:
        """Test that decorator preserves original function metadata."""

        @cache_invalidation(["test"])
        async def original_function(self, command):
            """Original command function docstring."""
            return "result"

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original command function docstring."

    @pytest.mark.asyncio
    async def test_cache_invalidation_multiple_prefixes(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test cache invalidation with multiple prefixes."""
        analysis_id = uuid4()
        command_result = MockAnalysisResult(analysis_id)

        prefixes = ["analysis", "filing", "company", "list", "search"]

        @cache_invalidation(prefixes)
        async def mock_command_method(self, command):
            return command_result

        command = MockQuery()
        result = await mock_command_method(handler_with_cache, command)

        assert result == command_result

        # Verify all prefixes were cleared with the ID
        assert mock_cache_service.clear_prefix.call_count == len(prefixes)

        clear_calls = [
            call[0][0] for call in mock_cache_service.clear_prefix.call_args_list
        ]
        for prefix in prefixes:
            expected_call = f"{prefix}:{analysis_id}"
            assert expected_call in clear_calls

    @pytest.mark.asyncio
    async def test_cache_invalidation_command_failure_no_invalidation(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache is not invalidated when command fails."""

        @cache_invalidation(["analysis"])
        async def mock_command_method(self, command):
            raise Exception("Command failed")

        command = MockQuery()

        with pytest.raises(Exception, match="Command failed"):
            await mock_command_method(handler_with_cache, command)

        # Cache should not be invalidated when command fails
        mock_cache_service.clear_prefix.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_invalidation_integration_with_cached_query(
        self,
        handler_with_cache: MockHandler,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test integration between cache invalidation and cached query decorators."""
        analysis_id = uuid4()

        # Mock cached query method
        @cached_query("analysis")
        async def mock_query_method(self, query):
            return {"cached": "query_result"}

        # Mock command method that invalidates cache
        @cache_invalidation(["analysis"])
        async def mock_command_method(self, command):
            return MockAnalysisResult(analysis_id)

        # Test cache miss, then cache invalidation
        mock_cache_service.get.return_value = None

        # Execute query (should cache result)
        query = MockQuery(analysis_id=str(analysis_id))
        query_result = await mock_query_method(handler_with_cache, query)

        # Execute command (should invalidate cache)
        command = MockQuery()
        command_result = await mock_command_method(handler_with_cache, command)

        # Verify query was cached and then invalidated
        mock_cache_service.get.assert_called_once()
        mock_cache_service.set.assert_called_once()
        mock_cache_service.clear_prefix.assert_called_once_with(
            f"analysis:{analysis_id}"
        )

        assert query_result == {"cached": "query_result"}
        assert command_result.id == analysis_id
