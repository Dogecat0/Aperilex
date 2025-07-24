"""Shared pytest fixtures for presentation integration tests."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.presentation.api.app import app
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.company_response import CompanyResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.task_response import TaskResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse, PaginationMetadata
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


@pytest.fixture
def mock_service_factory():
    """Mock ServiceFactory with dispatcher."""
    factory = MagicMock()
    
    # Mock dispatcher
    mock_dispatcher = AsyncMock()
    factory.create_dispatcher.return_value = mock_dispatcher
    
    # Mock handler dependencies
    mock_dependencies = MagicMock()
    factory.get_handler_dependencies.return_value = mock_dependencies
    
    return factory, mock_dispatcher


@pytest.fixture
def mock_background_task_coordinator():
    """Mock BackgroundTaskCoordinator."""
    return AsyncMock()


@pytest.fixture
def test_client(mock_service_factory):
    """FastAPI test client with mocked dependencies."""
    from src.presentation.api.dependencies import get_service_factory
    from src.infrastructure.database.base import get_db
    
    factory, _ = mock_service_factory
    
    # Override dependencies
    app.dependency_overrides[get_service_factory] = lambda: factory
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_with_task_coordinator(mock_service_factory, mock_background_task_coordinator):
    """FastAPI test client with both service factory and task coordinator mocked."""
    from src.presentation.api.dependencies import get_service_factory, get_background_task_coordinator
    from src.infrastructure.database.base import get_db
    
    factory, _ = mock_service_factory
    
    # Override dependencies
    app.dependency_overrides[get_service_factory] = lambda: factory
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_background_task_coordinator] = lambda: mock_background_task_coordinator
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup overrides
    app.dependency_overrides.clear()


# Sample response fixtures
@pytest.fixture
def sample_analysis_response():
    """Sample AnalysisResponse for testing."""
    return AnalysisResponse(
        analysis_id=uuid4(),
        filing_id=uuid4(),
        analysis_type=AnalysisType.COMPREHENSIVE,
        created_by="test-user",
        created_at=datetime.now(),
        confidence_score=85.5,
        llm_provider="openai",
        llm_model="gpt-4",
        processing_time_seconds=45.2,
        filing_summary="Sample filing summary",
        executive_summary="Sample executive summary",
        key_insights=["Key insight 1", "Key insight 2"],
        risk_factors=["Risk factor 1", "Risk factor 2"],
        opportunities=["Opportunity 1", "Opportunity 2"],
        financial_highlights={"revenue": "Increased 15%", "profit": "Decreased 5%"},
        sections_analyzed=["BusinessOverview", "FinancialStatements"]
    )


@pytest.fixture
def sample_company_response():
    """Sample CompanyResponse for testing."""
    return CompanyResponse(
        company_id=uuid4(),
        cik=CIK("0000320193"),
        name="Apple Inc.",
        ticker="AAPL",
        display_name="Apple Inc. (AAPL)",
        industry="Technology",
        sic_code="3571",
        sic_description="Electronic Computers",
        fiscal_year_end="September",
        business_address={
            "street": "One Apple Park Way",
            "city": "Cupertino",
            "state": "CA",
            "zipcode": "95014",
            "country": "USA"
        }
    )


@pytest.fixture
def sample_filing_response():
    """Sample FilingResponse for testing."""
    return FilingResponse(
        filing_id=uuid4(),
        company_id=uuid4(),
        accession_number="0000320193-24-000006",
        filing_type="10-K",
        filing_date=datetime.now().date(),
        processing_status="completed",
        processing_error=None,
        metadata={"pages": 112, "size_mb": 15.6},
        analyses_count=1,
        latest_analysis_date=datetime.now()
    )


@pytest.fixture
def sample_task_response():
    """Sample TaskResponse for testing."""
    return TaskResponse(
        task_id=str(uuid4()),
        status="completed",
        result={"analysis_id": str(uuid4())},
        error_message=None,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        progress_percent=100,
        current_step="Analysis complete"
    )


@pytest.fixture
def sample_paginated_response(sample_analysis_response):
    """Sample PaginatedResponse for testing."""
    return PaginatedResponse.create(
        items=[sample_analysis_response],
        page=1,
        page_size=10,
        total_items=1,
        query_id=uuid4()
    )


@pytest.fixture
def sample_paginated_response_page2(sample_analysis_response):
    """Sample PaginatedResponse for page 2 testing."""
    return PaginatedResponse.create(
        items=[sample_analysis_response],
        page=2,
        page_size=10,
        total_items=1,
        query_id=uuid4()
    )


@pytest.fixture
def sample_templates_response():
    """Sample TemplatesResponse for testing."""
    return TemplatesResponse(
        templates={
            "COMPREHENSIVE": {
                "name": "COMPREHENSIVE",
                "display_name": "Comprehensive Analysis",
                "description": "Complete analysis with all sections",
                "required_sections": ["business", "financials", "risks", "opportunities"]
            },
            "FINANCIAL_FOCUSED": {
                "name": "FINANCIAL_FOCUSED", 
                "display_name": "Financial Analysis",
                "description": "Focus on financial statements",
                "required_sections": ["financials"]
            }
        },
        total_count=2
    )