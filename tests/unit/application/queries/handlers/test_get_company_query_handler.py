"""Tests for GetCompanyQueryHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.application.queries.handlers.get_company_query_handler import GetCompanyQueryHandler
from src.application.schemas.queries.get_company import GetCompanyQuery
from src.application.schemas.responses.company_response import CompanyResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository


class TestGetCompanyQueryHandler:
    """Test GetCompanyQueryHandler functionality."""

    @pytest.fixture
    def mock_company_repository(self) -> AsyncMock:
        """Mock CompanyRepository."""
        return AsyncMock(spec=CompanyRepository)

    @pytest.fixture
    def mock_edgar_service(self) -> MagicMock:
        """Mock EdgarService."""
        return MagicMock(spec=EdgarService)

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def handler(
        self,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_analysis_repository: AsyncMock,
    ) -> GetCompanyQueryHandler:
        """Create GetCompanyQueryHandler with mocked dependencies."""
        return GetCompanyQueryHandler(
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
            analysis_repository=mock_analysis_repository,
        )

    @pytest.fixture
    def sample_query_cik(self) -> GetCompanyQuery:
        """Create sample GetCompanyQuery with CIK lookup."""
        return GetCompanyQuery(
            cik=CIK("0000320193"),
            include_recent_analyses=False,
        )

    @pytest.fixture
    def sample_query_ticker(self) -> GetCompanyQuery:
        """Create sample GetCompanyQuery with ticker lookup."""
        return GetCompanyQuery(
            ticker="AAPL",
            include_recent_analyses=False,
        )

    @pytest.fixture
    def mock_company_entity(self) -> Company:
        """Mock company entity."""
        return Company(
            id=uuid4(),
            cik=CIK("0000320193"),
            name="Apple Inc.",
        )

    @pytest.fixture
    def mock_edgar_data(self) -> MagicMock:
        """Mock EDGAR company data."""
        edgar_data = MagicMock()
        edgar_data.cik = "0000320193"
        edgar_data.name = "Apple Inc."
        edgar_data.ticker = "AAPL"
        edgar_data.industry = "Technology"
        return edgar_data

    def test_handler_initialization(
        self,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = GetCompanyQueryHandler(
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
            analysis_repository=mock_analysis_repository,
        )

        assert handler.company_repository == mock_company_repository
        assert handler.edgar_service == mock_edgar_service
        assert handler.analysis_repository == mock_analysis_repository

    def test_query_type_class_method(self) -> None:
        """Test query_type class method returns correct type."""
        query_type = GetCompanyQueryHandler.query_type()
        
        assert query_type == GetCompanyQuery

    @pytest.mark.asyncio
    async def test_handle_query_by_cik_company_in_database(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        sample_query_cik: GetCompanyQuery,
        mock_company_entity: Company,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test handling query by CIK when company exists in database."""
        # Setup mocks
        mock_company_repository.get_by_cik.return_value = mock_company_entity
        mock_edgar_service.get_company_by_cik.return_value = mock_edgar_data

        # Mock the CompanyResponse.from_domain_and_edgar method
        expected_response = MagicMock(spec=CompanyResponse)
        with patch.object(
            CompanyResponse, 'from_domain_and_edgar', return_value=expected_response
        ) as mock_from_domain:
            result = await handler.handle(sample_query_cik)

        # Verify result
        assert result is expected_response
        
        # Verify repository and service calls
        mock_company_repository.get_by_cik.assert_called_once_with(sample_query_cik.cik)
        mock_edgar_service.get_company_by_cik.assert_called_once_with(sample_query_cik.cik)
        
        # Verify response creation
        mock_from_domain.assert_called_once_with(
            company=mock_company_entity,
            edgar_data=mock_edgar_data,
        )

    @pytest.mark.asyncio
    async def test_handle_query_by_cik_company_not_in_database(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        sample_query_cik: GetCompanyQuery,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test handling query by CIK when company not in database."""
        # Setup mocks
        mock_company_repository.get_by_cik.return_value = None
        mock_edgar_service.get_company_by_cik.return_value = mock_edgar_data

        # Mock the CompanyResponse.from_edgar_only method
        expected_response = MagicMock(spec=CompanyResponse)
        with patch.object(
            CompanyResponse, 'from_edgar_only', return_value=expected_response
        ) as mock_from_edgar:
            result = await handler.handle(sample_query_cik)

        # Verify result
        assert result is expected_response
        
        # Verify repository and service calls
        mock_company_repository.get_by_cik.assert_called_once_with(sample_query_cik.cik)
        mock_edgar_service.get_company_by_cik.assert_called_once_with(sample_query_cik.cik)
        
        # Verify response creation
        mock_from_edgar.assert_called_once_with(
            edgar_data=mock_edgar_data,
        )

    @pytest.mark.asyncio
    async def test_handle_query_by_ticker(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        sample_query_ticker: GetCompanyQuery,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test handling query by ticker."""
        # Setup mocks - company not found in database for ticker lookup
        mock_company_repository.get_by_ticker.return_value = None
        mock_edgar_service.get_company_by_ticker.return_value = mock_edgar_data

        # Mock the CompanyResponse.from_edgar_only method
        expected_response = MagicMock(spec=CompanyResponse)
        with patch.object(
            CompanyResponse, 'from_edgar_only', return_value=expected_response
        ) as mock_from_edgar:
            result = await handler.handle(sample_query_ticker)

        # Verify result
        assert result is expected_response
        
        # Verify service calls
        mock_edgar_service.get_company_by_ticker.assert_called_once_with(Ticker(sample_query_ticker.ticker))
        
        # Verify response creation
        mock_from_edgar.assert_called_once_with(
            edgar_data=mock_edgar_data,
        )

    @pytest.mark.asyncio
    async def test_handle_query_with_recent_analyses(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_analysis_repository: AsyncMock,
        mock_company_entity: Company,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test handling query with recent analyses inclusion."""
        # Create query with recent analyses
        query = GetCompanyQuery(
            cik=CIK("0000320193"),
            include_recent_analyses=True,
        )

        # Setup mocks
        mock_company_repository.get_by_cik.return_value = mock_company_entity
        mock_edgar_service.get_company_by_cik.return_value = mock_edgar_data
        
        # Mock recent analyses
        mock_analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test_user",
                llm_provider="openai",
                llm_model="gpt-4",
                results={"summary": "Test analysis summary"},
                confidence_score=0.85,
            )
        ]
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        # Mock the CompanyResponse.from_domain_and_edgar method
        expected_response = MagicMock(spec=CompanyResponse)
        with patch.object(
            CompanyResponse, 'from_domain_and_edgar', return_value=expected_response
        ) as mock_from_domain:
            result = await handler.handle(query)

        # Verify result
        assert result is expected_response
        
        # Verify recent analyses were fetched
        mock_analysis_repository.find_with_filters.assert_called_once_with(
            company_cik=query.cik,
            page=1,
            page_size=5
        )
        
        # Verify response creation with recent analyses
        mock_from_domain.assert_called_once()
        call_kwargs = mock_from_domain.call_args[1]
        assert "recent_analyses" in call_kwargs

    @pytest.mark.asyncio
    async def test_handle_query_edgar_service_error(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        sample_query_cik: GetCompanyQuery,
    ) -> None:
        """Test handling query when EDGAR service fails."""
        # Setup mocks
        mock_company_repository.get_by_cik.return_value = None
        mock_edgar_service.get_company_by_cik.side_effect = Exception("EDGAR service unavailable")

        # Expect RuntimeError to be raised
        with pytest.raises(RuntimeError, match="Unable to retrieve company information from SEC EDGAR"):
            await handler.handle(sample_query_cik)

        # Verify service was called
        mock_edgar_service.get_company_by_cik.assert_called_once_with(sample_query_cik.cik)

    @pytest.mark.asyncio
    async def test_get_recent_analyses_success(
        self,
        handler: GetCompanyQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test successful retrieval of recent analyses."""
        cik = CIK("0000320193")
        
        # Mock recent analyses
        mock_analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test_user",
                llm_provider="openai",
                llm_model="gpt-4",
                results={"summary": "Test analysis summary"},
                confidence_score=0.85,
            )
        ]
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        result = await handler._get_recent_analyses(cik)

        assert len(result) == 1
        assert result[0]["analysis_id"] == str(mock_analyses[0].id)
        assert result[0]["analysis_type"] == mock_analyses[0].analysis_type.value
        assert result[0]["confidence_score"] == mock_analyses[0].confidence_score
        assert result[0]["summary"] == "Test analysis summary"

    @pytest.mark.asyncio
    async def test_get_recent_analyses_repository_error(
        self,
        handler: GetCompanyQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handling repository error when fetching recent analyses."""
        cik = CIK("0000320193")
        
        # Mock repository error
        mock_analysis_repository.find_with_filters.side_effect = Exception("Database error")

        result = await handler._get_recent_analyses(cik)

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_collect_enrichments_without_recent_analyses(
        self,
        handler: GetCompanyQueryHandler,
        mock_company_entity: Company,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test enrichment collection without recent analyses."""
        query = GetCompanyQuery(
            cik=CIK("0000320193"),
            include_recent_analyses=False,
        )

        enrichments = await handler._collect_enrichments(query, mock_edgar_data, mock_company_entity)

        assert enrichments == {}

    @pytest.mark.asyncio
    async def test_collect_enrichments_with_recent_analyses_no_entity(
        self,
        handler: GetCompanyQueryHandler,
        mock_edgar_data: MagicMock,
    ) -> None:
        """Test enrichment collection with recent analyses but no company entity."""
        query = GetCompanyQuery(
            cik=CIK("0000320193"),
            include_recent_analyses=True,
        )

        enrichments = await handler._collect_enrichments(query, mock_edgar_data, None)

        # Should not include recent analyses if no company entity
        assert enrichments == {}