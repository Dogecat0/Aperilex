"""Tests for AnalysisRepository with comprehensive coverage."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import Result, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.schemas.queries.list_analyses import (
    AnalysisSortField,
    SortDirection,
)
from src.domain.entities.analysis import Analysis, AnalysisType
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


class TestAnalysisRepositoryInitialization:
    """Test cases for AnalysisRepository initialization."""

    def test_init(self):
        """Test AnalysisRepository initialization."""
        session = Mock(spec=AsyncSession)

        repository = AnalysisRepository(session)

        assert repository.session is session
        assert repository.model_class is AnalysisModel


class TestAnalysisRepositoryConversions:
    """Test cases for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test to_entity conversion method."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Create model with all fields
        test_id = uuid4()
        filing_id = uuid4()
        created_at = datetime.now(UTC)
        model = AnalysisModel(
            id=test_id,
            filing_id=filing_id,
            analysis_type="filing_analysis",
            created_by="test_user",
            results={"key": "value"},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.85,
            meta_data={"test": "data"},
            created_at=created_at,
        )

        entity = repository.to_entity(model)

        assert isinstance(entity, Analysis)
        assert entity.id == test_id
        assert entity.filing_id == filing_id
        assert entity.analysis_type == AnalysisType.FILING_ANALYSIS
        assert entity.created_by == "test_user"
        assert entity.results == {"key": "value"}
        assert entity.llm_provider == "openai"
        assert entity.llm_model == "dummy"
        assert entity.confidence_score == 0.85
        assert entity.metadata == {"test": "data"}
        assert entity.created_at == created_at

    def test_to_entity_with_minimal_fields(self):
        """Test to_entity conversion with minimal required fields."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        filing_id = uuid4()
        created_at = datetime.now(UTC)
        model = AnalysisModel(
            id=test_id,
            filing_id=filing_id,
            analysis_type="custom_query",
            created_by=None,
            results={},
            llm_provider="anthropic",
            llm_model="dummy",
            confidence_score=None,
            meta_data=None,
            created_at=created_at,
        )

        entity = repository.to_entity(model)

        assert entity.id == test_id
        assert entity.filing_id == filing_id
        assert entity.analysis_type == AnalysisType.CUSTOM_QUERY
        assert entity.created_by is None
        assert entity.results == {}
        assert entity.confidence_score is None
        assert entity.metadata == {}

    def test_to_model_conversion(self):
        """Test to_model conversion method."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        filing_id = uuid4()
        created_at = datetime.now(UTC)
        entity = Analysis(
            id=test_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="test_user",
            results={"insight": "data"},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.92,
            metadata={"processing_time": 15.5},
            created_at=created_at,
        )

        model = repository.to_model(entity)

        assert isinstance(model, AnalysisModel)
        assert model.id == test_id
        assert model.filing_id == filing_id
        assert model.analysis_type == "comprehensive"
        assert model.created_by == "test_user"
        assert model.results == {"insight": "data"}
        assert model.llm_provider == "openai"
        assert model.llm_model == "dummy"
        assert model.confidence_score == 0.92
        assert model.meta_data == {"processing_time": 15.5}
        assert model.created_at == created_at

    def test_conversion_round_trip(self):
        """Test that entity -> model -> entity conversion preserves data."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        original_id = uuid4()
        filing_id = uuid4()
        created_at = datetime.now(UTC)
        original_entity = Analysis(
            id=original_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.HISTORICAL_TREND,
            created_by="api_user",
            results={"trends": ["up", "down"]},
            llm_provider="anthropic",
            llm_model="dummy",
            confidence_score=0.78,
            metadata={"version": "1.0"},
            created_at=created_at,
        )

        # Convert to model and back to entity
        model = repository.to_model(original_entity)
        final_entity = repository.to_entity(model)

        # Data should be preserved
        assert final_entity.id == original_id
        assert final_entity.filing_id == filing_id
        assert final_entity.analysis_type == AnalysisType.HISTORICAL_TREND
        assert final_entity.created_by == "api_user"
        assert final_entity.results == {"trends": ["up", "down"]}
        assert final_entity.llm_provider == "anthropic"
        assert final_entity.llm_model == "dummy"
        assert final_entity.confidence_score == 0.78
        assert final_entity.metadata == {"version": "1.0"}
        assert final_entity.created_at == created_at


class TestAnalysisRepositoryGetByFilingId:
    """Test cases for get_by_filing_id method."""

    async def test_get_by_filing_id_success(self):
        """Test successful retrieval by filing ID."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()
        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type="filing_analysis",
            created_by="test_user",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_filing_id(filing_id)

        assert len(result) == 1
        assert isinstance(result[0], Analysis)
        assert result[0].filing_id == filing_id
        session.execute.assert_called_once()

    async def test_get_by_filing_id_with_type_filter(self):
        """Test get_by_filing_id with analysis type filter."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_filing_id(
            filing_id, analysis_type=AnalysisType.COMPREHENSIVE
        )

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_get_by_filing_id_empty_result(self):
        """Test get_by_filing_id with no matches."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_filing_id(filing_id)

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_get_by_filing_id_database_error(self):
        """Test get_by_filing_id when database raises error."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()
        session.execute = AsyncMock(side_effect=SQLAlchemyError("Database error"))

        with pytest.raises(SQLAlchemyError, match="Database error"):
            await repository.get_by_filing_id(filing_id)


class TestAnalysisRepositoryGetByType:
    """Test cases for get_by_type method."""

    async def test_get_by_type_success(self):
        """Test successful retrieval by analysis type."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_models = [
            AnalysisModel(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type="comprehensive",
                created_by="user1",
                results={"data": "test1"},
                llm_provider="openai",
                llm_model="dummy",
                created_at=datetime.now(UTC),
            ),
            AnalysisModel(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type="comprehensive",
                created_by="user2",
                results={"data": "test2"},
                llm_provider="anthropic",
                llm_model="dummy",
                created_at=datetime.now(UTC),
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_type(AnalysisType.COMPREHENSIVE)

        assert len(result) == 2
        assert all(isinstance(analysis, Analysis) for analysis in result)
        assert all(
            analysis.analysis_type == AnalysisType.COMPREHENSIVE for analysis in result
        )
        session.execute.assert_called_once()

    async def test_get_by_type_with_limit(self):
        """Test get_by_type with limit parameter."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="custom_query",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_type(AnalysisType.CUSTOM_QUERY, limit=5)

        assert len(result) == 1
        assert result[0].analysis_type == AnalysisType.CUSTOM_QUERY
        session.execute.assert_called_once()


class TestAnalysisRepositoryGetByUser:
    """Test cases for get_by_user method."""

    async def test_get_by_user_success(self):
        """Test successful retrieval by user."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="test_user",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_user("test_user")

        assert len(result) == 1
        assert result[0].created_by == "test_user"
        session.execute.assert_called_once()

    async def test_get_by_user_with_date_filters(self):
        """Test get_by_user with date range filters."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        start_date = datetime.now(UTC)
        end_date = datetime.now(UTC)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_user(
            "test_user", start_date=start_date, end_date=end_date
        )

        assert len(result) == 0
        session.execute.assert_called_once()


class TestAnalysisRepositoryGetHighConfidenceAnalyses:
    """Test cases for get_high_confidence_analyses method."""

    async def test_get_high_confidence_analyses_success(self):
        """Test successful retrieval of high confidence analyses."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="comprehensive",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.95,
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_high_confidence_analyses()

        assert len(result) == 1
        assert result[0].confidence_score == 0.95
        session.execute.assert_called_once()

    async def test_get_high_confidence_analyses_with_custom_threshold(self):
        """Test get_high_confidence_analyses with custom confidence threshold."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_high_confidence_analyses(
            min_confidence=0.9, limit=10
        )

        assert len(result) == 0
        session.execute.assert_called_once()


class TestAnalysisRepositoryGetLatestAnalysisForFiling:
    """Test cases for get_latest_analysis_for_filing method."""

    async def test_get_latest_analysis_for_filing_success(self):
        """Test successful retrieval of latest analysis."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()
        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type="filing_analysis",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock the get_by_filing_id method by setting up the query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_latest_analysis_for_filing(filing_id)

        assert result is not None
        assert isinstance(result, Analysis)
        assert result.filing_id == filing_id

    async def test_get_latest_analysis_for_filing_not_found(self):
        """Test get_latest_analysis_for_filing when no analysis exists."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_latest_analysis_for_filing(filing_id)

        assert result is None


class TestAnalysisRepositoryCountByType:
    """Test cases for count_by_type method."""

    async def test_count_by_type_success(self):
        """Test successful count by type."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock query result with counts
        mock_result = Mock(spec=Result)
        mock_rows = [("filing_analysis", 5), ("comprehensive", 3), ("custom_query", 2)]
        mock_result.all.return_value = mock_rows
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_by_type()

        expected = {"filing_analysis": 5, "comprehensive": 3, "custom_query": 2}
        assert result == expected
        session.execute.assert_called_once()

    async def test_count_by_type_empty_result(self):
        """Test count_by_type with empty result."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_by_type()

        assert result == {}
        session.execute.assert_called_once()


class TestAnalysisRepositoryFindByFilingId:
    """Test cases for find_by_filing_id method."""

    async def test_find_by_filing_id_success(self):
        """Test find_by_filing_id delegates to get_by_filing_id."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        filing_id = uuid4()
        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type="filing_analysis",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_filing_id(filing_id)

        assert len(result) == 1
        assert result[0].filing_id == filing_id


class TestAnalysisRepositoryCountWithFilters:
    """Test cases for count_with_filters method."""

    async def test_count_with_filters_no_filters(self):
        """Test count_with_filters with no filters."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 10
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_with_filters()

        assert result == 10
        session.execute.assert_called_once()

    async def test_count_with_filters_with_company_cik(self):
        """Test count_with_filters with company CIK filter."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_with_filters(company_cik="1234567890")

        assert result == 5
        session.execute.assert_called_once()

    async def test_count_with_filters_with_analysis_types(self):
        """Test count_with_filters with analysis types filter."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 3
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_with_filters(
            analysis_types=[AnalysisType.COMPREHENSIVE, AnalysisType.CUSTOM_QUERY]
        )

        assert result == 3
        session.execute.assert_called_once()

    async def test_count_with_filters_with_date_range(self):
        """Test count_with_filters with date range filters."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 2
        session.execute = AsyncMock(return_value=mock_result)

        start_date = datetime.now(UTC)
        end_date = datetime.now(UTC)

        result = await repository.count_with_filters(
            created_from=start_date, created_to=end_date
        )

        assert result == 2
        session.execute.assert_called_once()

    async def test_count_with_filters_with_confidence_score(self):
        """Test count_with_filters with minimum confidence score."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 7
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_with_filters(min_confidence_score=0.8)

        assert result == 7
        session.execute.assert_called_once()

    async def test_count_with_filters_returns_zero_on_none_result(self):
        """Test count_with_filters returns 0 when result is None."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock scalar result returning None
        mock_result = Mock()
        mock_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_with_filters()

        assert result == 0


class TestAnalysisRepositoryFindWithFilters:
    """Test cases for find_with_filters method."""

    async def test_find_with_filters_no_filters(self):
        """Test find_with_filters with no filters."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_with_filters()

        assert len(result) == 1
        assert isinstance(result[0], Analysis)
        session.execute.assert_called_once()

    async def test_find_with_filters_with_company_cik(self):
        """Test find_with_filters with company CIK filter."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_with_filters(company_cik="1234567890")

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_find_with_filters_with_all_filters(self):
        """Test find_with_filters with all filter types."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="comprehensive",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.9,
            created_at=datetime.now(UTC),
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        start_date = datetime.now(UTC)
        end_date = datetime.now(UTC)

        result = await repository.find_with_filters(
            company_cik="1234567890",
            analysis_types=[AnalysisType.COMPREHENSIVE],
            created_from=start_date,
            created_to=end_date,
            min_confidence_score=0.8,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=10,
        )

        assert len(result) == 1
        assert result[0].analysis_type == AnalysisType.COMPREHENSIVE
        session.execute.assert_called_once()

    async def test_find_with_filters_with_sorting(self):
        """Test find_with_filters with different sorting options."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock empty result for each sorting test
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        # Test different sort fields
        sort_fields = [
            AnalysisSortField.CREATED_AT,
            AnalysisSortField.CONFIDENCE_SCORE,
            AnalysisSortField.ANALYSIS_TYPE,
        ]

        for sort_field in sort_fields:
            result = await repository.find_with_filters(
                sort_by=sort_field, sort_direction=SortDirection.ASC
            )
            assert len(result) == 0

    async def test_find_with_filters_with_pagination(self):
        """Test find_with_filters with pagination parameters."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_with_filters(page=2, page_size=5)

        assert len(result) == 0
        session.execute.assert_called_once()


class TestAnalysisRepositoryBaseRepositoryMethods:
    """Test cases for inherited BaseRepository methods."""

    async def test_get_by_id_success(self):
        """Test successful get by ID."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        test_model = AnalysisModel(
            id=test_id,
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        session.get = AsyncMock(return_value=test_model)

        result = await repository.get_by_id(test_id)

        assert result is not None
        assert isinstance(result, Analysis)
        assert result.id == test_id
        session.get.assert_called_once_with(AnalysisModel, test_id)

    async def test_get_by_id_not_found(self):
        """Test get by ID when record is not found."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repository.get_by_id(test_id)

        assert result is None
        session.get.assert_called_once_with(AnalysisModel, test_id)

    async def test_create_success(self):
        """Test successful entity creation."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        repository = AnalysisRepository(session)

        test_entity = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
        )

        result = await repository.create(test_entity)

        assert isinstance(result, Analysis)
        assert result.analysis_type == AnalysisType.FILING_ANALYSIS
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_update_success(self):
        """Test successful entity update."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock()
        session.flush = AsyncMock()
        repository = AnalysisRepository(session)

        test_entity = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="user1",
            results={"updated": "data"},
            llm_provider="openai",
            llm_model="dummy",
        )

        result = await repository.update(test_entity)

        assert result is test_entity
        session.merge.assert_called_once()
        session.flush.assert_called_once()

    async def test_delete_success(self):
        """Test successful entity deletion."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        test_model = AnalysisModel(
            id=test_id,
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        session.get = AsyncMock(return_value=test_model)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.delete(test_id)

        assert result is True
        session.get.assert_called_once_with(AnalysisModel, test_id)
        session.delete.assert_called_once_with(test_model)
        session.flush.assert_called_once()

    async def test_delete_not_found(self):
        """Test delete when record is not found."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repository.delete(test_id)

        assert result is False
        session.get.assert_called_once_with(AnalysisModel, test_id)
        session.delete.assert_not_called()
        session.flush.assert_not_called()


class TestAnalysisRepositoryErrorHandling:
    """Test cases for error handling scenarios."""

    async def test_session_execute_error(self):
        """Test handling of session execute errors."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        session.execute = AsyncMock(
            side_effect=SQLAlchemyError("Database connection lost")
        )

        with pytest.raises(SQLAlchemyError, match="Database connection lost"):
            await repository.get_by_type(AnalysisType.FILING_ANALYSIS)

    async def test_session_flush_error_during_create(self):
        """Test handling of flush errors during create."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock(side_effect=SQLAlchemyError("Constraint violation"))
        repository = AnalysisRepository(session)

        test_entity = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
        )

        with pytest.raises(SQLAlchemyError, match="Constraint violation"):
            await repository.create(test_entity)

    async def test_conversion_error_handling(self):
        """Test handling of conversion errors."""
        session = Mock(spec=AsyncSession)
        repository = AnalysisRepository(session)

        # Create a model with invalid data that will cause conversion to fail
        invalid_model = AnalysisModel(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type="invalid_type",  # This will cause AnalysisType conversion to fail
            created_by="user1",
            results={"data": "test"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )

        with pytest.raises(ValueError):
            repository.to_entity(invalid_model)


class TestAnalysisRepositoryIntegration:
    """Integration test cases for AnalysisRepository operations."""

    async def test_full_crud_cycle(self):
        """Test a complete CRUD cycle."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.merge = AsyncMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        repository = AnalysisRepository(session)

        # Create
        test_entity = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="integration_test",
            results={"test": "data"},
            llm_provider="openai",
            llm_model="dummy",
        )

        created_entity = await repository.create(test_entity)
        assert created_entity.analysis_type == AnalysisType.COMPREHENSIVE
        session.add.assert_called_once()
        session.flush.assert_called_once()

        # Get (simulate finding the created entity)
        test_model = AnalysisModel(
            id=created_entity.id,
            filing_id=created_entity.filing_id,
            analysis_type="comprehensive",
            created_by="integration_test",
            results={"test": "data"},
            llm_provider="openai",
            llm_model="dummy",
            created_at=datetime.now(UTC),
        )
        session.get = AsyncMock(return_value=test_model)

        retrieved_entity = await repository.get_by_id(created_entity.id)
        assert retrieved_entity.created_by == "integration_test"
        session.get.assert_called_once()

        # Update
        retrieved_entity.update_results({"updated": "test_data"})
        updated_entity = await repository.update(retrieved_entity)
        assert updated_entity.results["updated"] == "test_data"
        session.merge.assert_called_once()

        # Delete
        deleted = await repository.delete(retrieved_entity.id)
        assert deleted is True
        session.delete.assert_called_once()

        # Commit
        await repository.commit()
        session.commit.assert_called_once()
