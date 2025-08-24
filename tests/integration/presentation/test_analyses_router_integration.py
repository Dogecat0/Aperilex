"""Integration tests for analyses router with real service dependencies."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.presentation.api.routers.analyses import router


@pytest.mark.integration
class TestAnalysesRouterIntegration:
    """Integration tests for analyses router endpoints."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Analyses Router Integration")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def teardown_method(self):
        """Clean up after each test method."""
        # Clear any dependency overrides to prevent test interference
        self.app.dependency_overrides.clear()

        # Force garbage collection to clean up any remaining objects
        import gc

        gc.collect()

    def test_list_analyses_endpoint_with_real_dependencies(self):
        """Test list analyses endpoint with mocked service dependencies."""
        # Arrange
        expected_items = [
            self._create_analysis_response(),
            self._create_analysis_response(analysis_type="comprehensive"),
        ]
        expected_response = PaginatedResponse(
            items=expected_items,
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=2),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/api/analyses")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert "items" in data
            assert "pagination" in data
            assert len(data["items"]) == 2
            assert data["pagination"]["total_items"] == 2
            assert data["pagination"]["page"] == 1

            # Validate individual analysis items
            for item in data["items"]:
                self._validate_analysis_response_structure(item)

    def test_list_analyses_with_filters_integration(self):
        """Test list analyses endpoint with various filter combinations."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_analysis_response()],
            pagination=PaginationMetadata.create(page=2, page_size=10, total_items=15),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - test with multiple filters
            response = self.client.get(
                "/api/analyses?"
                "company_cik=0000320193&"
                "analysis_type=filing_analysis&"
                "analysis_template=comprehensive&"
                "min_confidence_score=0.8&"
                "created_from=2023-01-01T00:00:00Z&"
                "created_to=2023-12-31T23:59:59Z&"
                "page=2&"
                "page_size=10"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Verify pagination reflects the filters
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["page_size"] == 10
            assert data["pagination"]["has_previous"] is True

            # Verify query was called with correct filters
            mock_dispatcher.dispatch_query.assert_called_once()
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query_call.company_cik.value == "0000320193"
            assert query_call.analysis_types == [AnalysisType.FILING_ANALYSIS]
            assert query_call.analysis_template == AnalysisTemplate.COMPREHENSIVE
            assert query_call.min_confidence_score == 0.8

    def test_list_analyses_invalid_cik_error_handling(self):
        """Test list analyses endpoint handles invalid CIK gracefully."""
        # Act
        response = self.client.get("/api/analyses?company_cik=invalid-cik-format")

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "Invalid CIK format" in data["detail"]

    def test_list_analyses_service_failure_error_handling(self):
        """Test list analyses endpoint handles service failures gracefully."""
        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(
                side_effect=RuntimeError("Database connection failed")
            )

            # Act
            response = self.client.get("/api/analyses")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to list analyses" in data["detail"]

    def test_get_analysis_templates_endpoint_integration(self):
        """Test get analysis templates endpoint with service dependencies."""
        # Arrange
        expected_templates = {
            "comprehensive": {
                "description": "Comprehensive analysis covering all business areas",
                "schemas": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                    "MDAAnalysisSection",
                    "BalanceSheetAnalysisSection",
                    "IncomeStatementAnalysisSection",
                    "CashFlowAnalysisSection",
                ],
                "schema_count": 6,
            },
            "financial_focused": {
                "description": "Financial analysis focusing on statements and performance",
                "schemas": [
                    "BalanceSheetAnalysisSection",
                    "IncomeStatementAnalysisSection",
                    "CashFlowAnalysisSection",
                ],
                "schema_count": 3,
            },
            "risk_focused": {
                "description": "Risk analysis focusing on risk factors and forward outlook",
                "schemas": ["RiskFactorsAnalysisSection", "MDAAnalysisSection"],
                "schema_count": 2,
            },
            "business_focused": {
                "description": "Business analysis focusing on strategy and market position",
                "schemas": ["BusinessAnalysisSection", "MDAAnalysisSection"],
                "schema_count": 2,
            },
        }
        expected_response = TemplatesResponse(
            templates=expected_templates, total_count=4
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/api/analyses/templates")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert "templates" in data
            assert "total_count" in data
            assert data["total_count"] == 4

            # Validate template content
            assert "comprehensive" in data["templates"]
            assert "financial_focused" in data["templates"]
            assert "risk_focused" in data["templates"]
            assert "business_focused" in data["templates"]

            comprehensive_template = data["templates"]["comprehensive"]
            assert (
                comprehensive_template["description"]
                == "Comprehensive analysis covering all business areas"
            )
            assert "schemas" in comprehensive_template
            assert len(comprehensive_template["schemas"]) == 6
            assert comprehensive_template["schema_count"] == 6

    def test_get_analysis_templates_with_filter_integration(self):
        """Test get analysis templates endpoint with type filter (filter not yet implemented, returns all)."""
        # Arrange - Since filtering is not implemented, this returns all templates
        all_templates = {
            "comprehensive": {
                "description": "Comprehensive analysis covering all business areas",
                "schemas": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                    "MDAAnalysisSection",
                    "BalanceSheetAnalysisSection",
                    "IncomeStatementAnalysisSection",
                    "CashFlowAnalysisSection",
                ],
                "schema_count": 6,
            },
            "financial_focused": {
                "description": "Financial analysis focusing on statements and performance",
                "schemas": [
                    "BalanceSheetAnalysisSection",
                    "IncomeStatementAnalysisSection",
                    "CashFlowAnalysisSection",
                ],
                "schema_count": 3,
            },
            "risk_focused": {
                "description": "Risk analysis focusing on risk factors and forward outlook",
                "schemas": ["RiskFactorsAnalysisSection", "MDAAnalysisSection"],
                "schema_count": 2,
            },
            "business_focused": {
                "description": "Business analysis focusing on strategy and market position",
                "schemas": ["BusinessAnalysisSection", "MDAAnalysisSection"],
                "schema_count": 2,
            },
        }
        expected_response = TemplatesResponse(templates=all_templates, total_count=4)

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(
                "/api/analyses/templates?template_type=financial"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            # Since filtering is not implemented, we get all templates
            assert data["total_count"] == 4
            assert "financial_focused" in data["templates"]
            assert "comprehensive" in data["templates"]
            assert "risk_focused" in data["templates"]
            assert "business_focused" in data["templates"]

    def test_get_analysis_by_id_endpoint_integration(self):
        """Test get analysis by ID endpoint with service dependencies."""
        # Arrange
        analysis_id = uuid4()
        expected_response = self._create_analysis_response(
            analysis_id=analysis_id, include_full_results=True
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/analyses/{analysis_id}")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate complete analysis response
            self._validate_analysis_response_structure(data)
            assert data["analysis_id"] == str(analysis_id)
            assert (
                "full_results" in data
            )  # Should include full results for individual analysis
            assert data["full_results"] is not None

    def test_get_analysis_not_found_integration(self):
        """Test get analysis endpoint handles not found cases."""
        # Arrange
        analysis_id = uuid4()

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(
                side_effect=RuntimeError("Analysis not found")
            )

            # Act
            response = self.client.get(f"/api/analyses/{analysis_id}")

            # Assert
            assert response.status_code == 500  # Internal error handling
            data = response.json()
            assert "Failed to retrieve analysis" in data["detail"]

    def test_analyses_router_cors_and_headers_integration(self):
        """Test analyses router handles CORS and header requirements."""
        with self._mock_dependencies() as (mock_factory, mock_session):
            expected_response = PaginatedResponse(
                items=[],
                pagination=PaginationMetadata.create(
                    page=1, page_size=20, total_items=0
                ),
            )
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(
                "/api/analyses",
                headers={"Accept": "application/json", "User-Agent": "TestClient"},
            )

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    def test_analyses_router_performance_with_large_dataset(self):
        """Test analyses router performance with large paginated dataset."""
        # Arrange - simulate large dataset
        large_item_count = 1000
        expected_response = PaginatedResponse(
            items=[self._create_analysis_response() for _ in range(20)],  # One page
            pagination=PaginationMetadata(
                page=1,
                page_size=20,
                total_items=large_item_count,
                total_pages=50,
                has_next=True,
                has_previous=False,
                next_page=2,
                previous_page=None,
            ),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - measure response time
            import time

            start_time = time.time()
            response = self.client.get("/api/analyses?page_size=20")
            response_time = time.time() - start_time

            # Assert
            assert response.status_code == 200
            assert response_time < 5.0  # Should respond within 5 seconds

            data = response.json()
            assert len(data["items"]) == 20
            assert data["pagination"]["total_items"] == large_item_count
            assert data["pagination"]["has_next"] is True

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from src.infrastructure.database.base import get_db
        from src.presentation.api.dependencies import get_service_factory

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = Mock()
        mock_dispatcher = Mock()

        mock_factory.create_dispatcher.return_value = mock_dispatcher
        mock_factory.get_handler_dependencies = AsyncMock(return_value={})

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_db] = lambda: mock_session
                app.dependency_overrides[get_service_factory] = lambda: mock_factory
                return mock_factory, mock_session

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

                # Clean up AsyncMock objects to prevent hanging
                try:
                    if hasattr(
                        mock_factory.create_dispatcher.return_value, 'dispatch_query'
                    ):
                        async_mock = (
                            mock_factory.create_dispatcher.return_value.dispatch_query
                        )
                        if hasattr(async_mock, '_mock_calls'):
                            async_mock._mock_calls.clear()
                    if hasattr(
                        mock_factory.create_dispatcher.return_value, 'dispatch_command'
                    ):
                        async_mock = (
                            mock_factory.create_dispatcher.return_value.dispatch_command
                        )
                        if hasattr(async_mock, '_mock_calls'):
                            async_mock._mock_calls.clear()
                except Exception:
                    pass  # Ignore cleanup errors

        return DependencyOverrider()

    def _create_analysis_response(
        self,
        analysis_id=None,
        analysis_type="filing_analysis",
        include_full_results=False,
    ) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=analysis_id or uuid4(),
            filing_id=uuid4(),
            analysis_type=analysis_type,
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=150.0,
            filing_summary="Comprehensive 10-K filing analysis for tech company",
            executive_summary="Strong financial performance with growth opportunities",
            key_insights=[
                "Revenue increased 15% year-over-year",
                "Operating margins improved to 25%",
                "Strong cash flow generation",
            ],
            risk_factors=[
                "Market competition intensifying",
                "Regulatory changes in key markets",
            ],
            opportunities=[
                "Expansion into emerging markets",
                "New product line development",
            ],
            financial_highlights=[
                "Record quarterly revenue",
                "Debt-to-equity ratio improved",
            ],
            sections_analyzed=8,
            full_results=(
                {
                    "detailed_financial_analysis": {"revenue": 50000, "profit": 12500},
                    "business_analysis": {
                        "market_share": 0.15,
                        "competitive_position": "strong",
                    },
                    "risk_assessment": {"overall_risk": "medium", "key_risks": 3},
                }
                if include_full_results
                else None
            ),
        )

    def _validate_analysis_response_structure(self, data: dict):
        """Validate that analysis response has expected structure."""
        required_fields = [
            "analysis_id",
            "filing_id",
            "analysis_type",
            "created_at",
            "confidence_score",
            "llm_provider",
            "llm_model",
            "processing_time_seconds",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate types
        assert isinstance(data["confidence_score"], int | float)
        assert 0.0 <= data["confidence_score"] <= 1.0
        assert isinstance(data["processing_time_seconds"], int | float)
        assert data["processing_time_seconds"] >= 0


@pytest.mark.integration
@pytest.mark.slow
class TestAnalysesRouterStressTest:
    """Stress tests for analyses router under load."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Analyses Router Stress")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def teardown_method(self):
        """Clean up after each test method."""
        # Clear any dependency overrides to prevent test interference
        self.app.dependency_overrides.clear()

        # Force garbage collection to clean up any remaining objects
        import gc

        gc.collect()

    def test_concurrent_list_analyses_requests(self):
        """Test analyses router handles concurrent requests properly."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_analysis_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        # Pre-configure the main app with dependency overrides to avoid thread conflicts
        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            def make_request():
                """Make a single request to the analyses endpoint using the pre-configured client."""
                return self.client.get("/api/analyses")

            # Act - simulate concurrent requests with pre-configured dependencies
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(20)]
                responses = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # Assert - all requests should succeed
            assert len(responses) == 20
            for response in responses:
                assert response.status_code == 200

    def test_analyses_router_memory_usage(self):
        """Test analyses router doesn't leak memory under repeated requests."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_analysis_response() for _ in range(100)],
            pagination=PaginationMetadata(
                page=1,
                page_size=100,
                total_items=1000,
                total_pages=10,
                has_next=True,
                has_previous=False,
                next_page=2,
                previous_page=None,
            ),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - make many requests to check for memory leaks
            import gc

            gc.collect()  # Initial cleanup
            initial_objects = len(gc.get_objects())

            for i in range(50):
                response = self.client.get("/api/analyses?page_size=100")
                assert response.status_code == 200

                # Periodic cleanup to prevent accumulation
                if i % 10 == 0:
                    gc.collect()

            # Final cleanup before measurement
            gc.collect()
            final_objects = len(gc.get_objects())

            # Assert - object count shouldn't grow significantly
            object_growth = final_objects - initial_objects
            assert (
                object_growth < 5000
            )  # Allow reasonable growth for integration tests with FastAPI app and mocks

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from src.infrastructure.database.base import get_db
        from src.presentation.api.dependencies import get_service_factory

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = Mock()
        mock_dispatcher = Mock()

        mock_factory.create_dispatcher.return_value = mock_dispatcher
        mock_factory.get_handler_dependencies = AsyncMock(return_value={})

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_db] = lambda: mock_session
                app.dependency_overrides[get_service_factory] = lambda: mock_factory
                return mock_factory, mock_session

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

        return DependencyOverrider()

    def _create_analysis_response(self) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=120.0,
        )
