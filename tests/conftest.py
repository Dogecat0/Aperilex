"""Global test configuration and fixtures for Aperilex."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.domain.entities.analysis import Analysis
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.analysis_stage import AnalysisStage
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.money import Money
from src.domain.value_objects.processing_status import ProcessingStatus
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.database.base import Base


@pytest.fixture
async def async_engine():
    """Create an async SQLite in-memory database engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    async_session_maker = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


# Domain Value Object Fixtures
@pytest.fixture
def valid_cik() -> CIK:
    """A valid CIK for testing."""
    return CIK("0000320193")


@pytest.fixture
def valid_ticker() -> Ticker:
    """A valid ticker for testing."""
    return Ticker("AAPL")


@pytest.fixture
def valid_accession_number() -> AccessionNumber:
    """A valid accession number for testing."""
    return AccessionNumber("0000320193-23-000106")


@pytest.fixture
def valid_filing_type() -> FilingType:
    """A valid filing type for testing."""
    return FilingType.FORM_10K


@pytest.fixture
def valid_processing_status() -> ProcessingStatus:
    """A valid processing status for testing."""
    return ProcessingStatus.PENDING


@pytest.fixture
def valid_money() -> Money:
    """A valid money value for testing."""
    return Money(amount=Decimal("1000.50"), currency="USD")


@pytest.fixture
def valid_analysis_stage() -> AnalysisStage:
    """A valid analysis stage for testing."""
    return AnalysisStage.FILING_ANALYSIS


# Domain Entity Fixtures
@pytest.fixture
def valid_company(valid_cik: CIK) -> Company:
    """A valid company entity for testing."""
    return Company(
        id=uuid.uuid4(),
        cik=valid_cik,
        name="Apple Inc.",
        metadata={"sector": "Technology", "employees": 164000},
    )


@pytest.fixture
def valid_filing(
    valid_accession_number: AccessionNumber, valid_filing_type: FilingType
) -> Filing:
    """A valid filing entity for testing."""
    return Filing(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        accession_number=valid_accession_number,
        filing_type=valid_filing_type,
        filing_date=datetime(2023, 12, 31, tzinfo=UTC).date(),
        processing_status=ProcessingStatus.COMPLETED,
        metadata={"form": "10-K", "fiscal_year": 2023},
    )


@pytest.fixture
def valid_analysis(valid_filing: Filing) -> Analysis:
    """A valid analysis entity for testing."""
    return Analysis(
        id=uuid.uuid4(),
        filing_id=valid_filing.id,
        analysis_type="filing_analysis",
        template_name="comprehensive_analysis",
        stage=AnalysisStage.FILING_ANALYSIS,
        confidence_score=0.95,
        processing_time_seconds=120.5,
        metadata={"model": "gpt-4", "tokens_used": 5000},
    )


# Test data helpers
@pytest.fixture
def sample_filing_data() -> dict[str, Any]:
    """Sample filing data for testing."""
    return {
        "accession_number": "0000320193-23-000106",
        "company_id": str(uuid.uuid4()),
        "cik": "0000320193",
        "filing_type": "10-K",
        "filing_date": "2023-12-31",
        "reporting_date": "2023-09-30",
        "status": "COMPLETED",
        "metadata": {"form": "10-K", "fiscal_year": 2023},
    }


@pytest.fixture
def sample_analysis_data() -> dict[str, Any]:
    """Sample analysis data for testing."""
    return {
        "filing_id": str(uuid.uuid4()),
        "analysis_type": "filing_analysis",
        "template_name": "comprehensive_analysis",
        "stage": "FILING_ANALYSIS",
        "confidence_score": 0.95,
        "processing_time_seconds": 120.5,
        "metadata": {"model": "gpt-4", "tokens_used": 5000},
    }


@pytest.fixture
def sample_company_data() -> dict[str, Any]:
    """Sample company data for testing."""
    return {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "metadata": {"sector": "Technology", "employees": 164000},
    }


# Mock configurations
@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    return {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "edgar_user_agent": "test@example.com",
        "openai_api_key": "test-key",
        "debug": True,
    }


# Utility fixtures
@pytest.fixture
def utc_now() -> datetime:
    """Current UTC datetime for testing."""
    return datetime.now(UTC)


@pytest.fixture
def uuid4() -> uuid.UUID:
    """A random UUID4 for testing."""
    return uuid.uuid4()


# Circuit Breaker Test Fixtures
@pytest.fixture
def mock_async_success_function():
    """Mock async function that always succeeds."""

    async def success_func(*args, **kwargs):
        return "success"

    return success_func


@pytest.fixture
def mock_async_failure_function():
    """Mock async function that always fails."""

    async def failure_func(*args, **kwargs):
        raise Exception("Test failure")

    return failure_func


@pytest.fixture
def mock_async_conditional_function():
    """Mock async function that can be configured to succeed or fail."""

    class ConditionalFunction:
        def __init__(self):
            self.should_fail = False
            self.call_count = 0

        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            if self.should_fail:
                raise Exception(f"Test failure #{self.call_count}")
            return f"success #{self.call_count}"

        def set_failure_mode(self, should_fail: bool):
            self.should_fail = should_fail

        def reset_call_count(self):
            self.call_count = 0

    return ConditionalFunction()


# Dispatcher Test Fixtures
@pytest.fixture
def mock_command():
    """Mock command for dispatcher testing."""
    from dataclasses import dataclass

    from src.application.base.command import BaseCommand

    @dataclass(frozen=True)
    class TestCommand(BaseCommand):
        test_data: str = "test"

        def validate(self) -> None:
            """Validate test command data."""
            if not self.test_data:
                raise ValueError("test_data cannot be empty")

    return TestCommand


@pytest.fixture
def mock_query():
    """Mock query for dispatcher testing."""
    from dataclasses import dataclass

    from src.application.base.query import BaseQuery

    @dataclass(frozen=True)
    class TestQuery(BaseQuery):
        test_filter: str = "test"

    return TestQuery


@pytest.fixture
def mock_command_handler(mock_command):
    """Mock command handler for dispatcher testing."""

    from src.application.base.handlers import CommandHandler

    class TestCommandHandler(CommandHandler[mock_command, str]):
        def __init__(self, dependency_a: str, dependency_b: int):
            self.dependency_a = dependency_a
            self.dependency_b = dependency_b

        @classmethod
        def command_type(cls):
            return mock_command

        async def handle(self, command) -> str:
            return (
                f"handled_{command.test_data}_{self.dependency_a}_{self.dependency_b}"
            )

    return TestCommandHandler


@pytest.fixture
def mock_query_handler(mock_query):
    """Mock query handler for dispatcher testing."""

    from src.application.base.handlers import QueryHandler

    class TestQueryHandler(QueryHandler[mock_query, dict]):
        def __init__(self, service: str):
            self.service = service

        @classmethod
        def query_type(cls):
            return mock_query

        async def handle(self, query) -> dict:
            return {
                "filter": query.test_filter,
                "service": self.service,
                "page": query.page,
                "page_size": query.page_size,
            }

    return TestQueryHandler


# FastAPI and HTTP testing fixtures
@pytest.fixture
def test_app():
    """Create FastAPI test application."""
    from src.presentation.api.app import app

    return app


@pytest.fixture
def test_client(test_app):
    """Create synchronous test client for FastAPI app."""
    from fastapi.testclient import TestClient

    return TestClient(test_app)


@pytest.fixture
async def async_test_client(test_app):
    """Create asynchronous test client for FastAPI app."""
    import httpx

    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_application_service():
    """Mock ApplicationService for API testing."""
    from src.application.application_service import ApplicationService

    return Mock(spec=ApplicationService)


@pytest.fixture
def mock_task_service():
    """Mock TaskService for API testing."""
    from src.application.services.task_service import TaskService

    return Mock(spec=TaskService)


@pytest.fixture
def mock_background_task_coordinator():
    """Mock BackgroundTaskCoordinator for API testing."""
    from src.application.services.background_task_coordinator import (
        BackgroundTaskCoordinator,
    )

    return Mock(spec=BackgroundTaskCoordinator)


@pytest.fixture
def mock_service_factory(
    mock_application_service, mock_task_service, mock_background_task_coordinator
):
    """Mock ServiceFactory configured with all mocked services."""
    from src.application.factory import ServiceFactory

    factory = Mock(spec=ServiceFactory)
    factory.create_application_service = AsyncMock(
        return_value=mock_application_service
    )
    factory.create_task_service = Mock(return_value=mock_task_service)
    factory.create_background_task_coordinator = AsyncMock(
        return_value=mock_background_task_coordinator
    )
    return factory


@pytest.fixture
def mock_fastapi_request():
    """Mock FastAPI Request object for testing."""
    from fastapi import Request

    request = Mock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"
    request.query_params = {}
    return request


# HTTP response fixtures
@pytest.fixture
def sample_analysis_response():
    """Sample analysis response for API testing."""
    return {
        "id": str(uuid.uuid4()),
        "filing_id": str(uuid.uuid4()),
        "analysis_type": "filing_analysis",
        "template_name": "comprehensive_analysis",
        "stage": "FILING_ANALYSIS",
        "confidence_score": 0.95,
        "processing_time_seconds": 120.5,
        "created_at": "2023-12-31T00:00:00Z",
        "updated_at": "2023-12-31T00:02:00Z",
        "metadata": {"model": "gpt-4", "tokens_used": 5000},
    }


@pytest.fixture
def sample_company_response():
    """Sample company response for API testing."""
    return {
        "id": str(uuid.uuid4()),
        "cik": "0000320193",
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "created_at": "2023-01-01T00:00:00Z",
        "metadata": {"sector": "Technology", "employees": 164000},
    }


@pytest.fixture
def sample_filing_response():
    """Sample filing response for API testing."""
    return {
        "id": str(uuid.uuid4()),
        "company_id": str(uuid.uuid4()),
        "accession_number": "0000320193-23-000106",
        "filing_type": "10-K",
        "filing_date": "2023-12-31",
        "reporting_date": "2023-09-30",
        "processing_status": "COMPLETED",
        "created_at": "2023-12-31T00:00:00Z",
        "metadata": {"form": "10-K", "fiscal_year": 2023},
    }


@pytest.fixture
def sample_task_response():
    """Sample task response for API testing."""
    return {
        "task_id": str(uuid.uuid4()),
        "status": "pending",
        "task_type": "analyze_filing",
        "created_at": "2023-12-31T00:00:00Z",
        "progress": {"current": 0, "total": 100, "message": "Starting analysis"},
    }


@pytest.fixture
def sample_paginated_response():
    """Sample paginated response structure for API testing."""
    return {
        "items": [],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total_items": 0,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False,
        },
    }


@pytest.fixture
def sample_health_response():
    """Sample health response for API testing."""
    return {
        "status": "healthy",
        "services": {
            "database": {"status": "healthy", "response_time_ms": 5},
            "messaging": {"status": "healthy", "response_time_ms": 10},
            "storage": {"status": "healthy", "response_time_ms": 3},
        },
        "uptime_seconds": 86400,
        "version": "1.0.0",
    }


# Markers for test organization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.external_api = pytest.mark.external_api
pytest.mark.requires_api_keys = pytest.mark.requires_api_keys
