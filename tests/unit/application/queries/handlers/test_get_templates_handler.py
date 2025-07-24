"""Tests for GetTemplatesQueryHandler."""

import pytest
from typing import Any
from unittest.mock import MagicMock, patch

from src.application.queries.handlers.get_templates_handler import (
    GetTemplatesQueryHandler,
    GetTemplatesQuery,
)
from src.application.services.analysis_template_service import AnalysisTemplateService


class TestGetTemplatesQuery:
    """Test GetTemplatesQuery functionality."""

    def test_get_templates_query_initialization(self) -> None:
        """Test GetTemplatesQuery initialization."""
        query = GetTemplatesQuery(user_id="test_user")
        
        assert query.user_id == "test_user"

    def test_get_templates_query_no_parameters(self) -> None:
        """Test that GetTemplatesQuery has no additional parameters."""
        query = GetTemplatesQuery()
        
        # Should only have base query fields
        assert hasattr(query, 'user_id')
        assert query.user_id is None


class TestGetTemplatesQueryHandler:
    """Test GetTemplatesQueryHandler functionality."""

    @pytest.fixture
    def mock_template_service(self) -> MagicMock:
        """Mock AnalysisTemplateService."""
        return MagicMock(spec=AnalysisTemplateService)

    @pytest.fixture
    def handler(
        self,
        mock_template_service: MagicMock,
    ) -> GetTemplatesQueryHandler:
        """Create GetTemplatesQueryHandler with mocked dependencies."""
        return GetTemplatesQueryHandler(template_service=mock_template_service)

    @pytest.fixture
    def sample_query(self) -> GetTemplatesQuery:
        """Create sample GetTemplatesQuery."""
        return GetTemplatesQuery(user_id="test_user")

    @pytest.fixture
    def mock_templates(self) -> dict[str, dict[str, Any]]:
        """Mock template data."""
        return {
            "COMPREHENSIVE": {
                "name": "Comprehensive Analysis",
                "description": "Complete filing analysis with all schemas",
                "schemas": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                    "FinancialAnalysisSection",
                    "MarketAnalysisSection",
                    "CompetitiveAnalysisSection",
                    "ESGAnalysisSection",
                ],
                "schema_count": 6,
                "estimated_processing_time": "5-8 minutes",
                "recommended_for": "Full company analysis",
            },
            "FINANCIAL_FOCUSED": {
                "name": "Financial Analysis",
                "description": "Focus on financial performance and metrics",
                "schemas": [
                    "FinancialAnalysisSection",
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                ],
                "schema_count": 3,
                "estimated_processing_time": "2-4 minutes",
                "recommended_for": "Financial due diligence",
            },
            "RISK_FOCUSED": {
                "name": "Risk Assessment",
                "description": "Focus on risk factors and compliance",
                "schemas": [
                    "RiskFactorsAnalysisSection",
                    "CompetitiveAnalysisSection",
                ],
                "schema_count": 2,
                "estimated_processing_time": "1-3 minutes",
                "recommended_for": "Risk management",
            },
            "BUSINESS_FOCUSED": {
                "name": "Business Analysis",
                "description": "Focus on business model and strategy",
                "schemas": [
                    "BusinessAnalysisSection",
                    "MarketAnalysisSection",
                ],
                "schema_count": 2,
                "estimated_processing_time": "1-3 minutes",
                "recommended_for": "Strategic analysis",
            },
        }

    def test_handler_initialization(
        self,
        mock_template_service: MagicMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = GetTemplatesQueryHandler(template_service=mock_template_service)

        assert handler.template_service == mock_template_service

    def test_query_type_class_method(self) -> None:
        """Test query_type class method returns correct type."""
        query_type = GetTemplatesQueryHandler.query_type()
        
        assert query_type == GetTemplatesQuery

    @pytest.mark.asyncio
    async def test_handle_query_success(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
        mock_templates: dict[str, dict[str, Any]],
    ) -> None:
        """Test successful query handling."""
        # Setup mock
        mock_template_service.get_all_templates.return_value = mock_templates
        
        result = await handler.handle(sample_query)

        # Verify result
        assert result == mock_templates
        
        # Verify service was called
        mock_template_service.get_all_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_empty_templates(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test query handling when no templates are available."""
        # Setup mock to return empty dict
        empty_templates = {}
        mock_template_service.get_all_templates.return_value = empty_templates
        
        result = await handler.handle(sample_query)

        # Verify result
        assert result == empty_templates
        assert len(result) == 0
        
        # Verify service was called
        mock_template_service.get_all_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_service_error(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test query handling when template service raises error."""
        # Setup mock to raise exception
        service_error = Exception("Template service failed")
        mock_template_service.get_all_templates.side_effect = service_error

        with pytest.raises(Exception, match="Template service failed"):
            await handler.handle(sample_query)

        # Verify service was called
        mock_template_service.get_all_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_different_users(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        mock_templates: dict[str, dict[str, Any]],
    ) -> None:
        """Test handling queries from different users."""
        user_ids = ["user1", "admin", None, "analyst_123"]

        for user_id in user_ids:
            query = GetTemplatesQuery(user_id=user_id)
            
            # Setup mock for each iteration
            mock_template_service.get_all_templates.return_value = mock_templates
            
            result = await handler.handle(query)

            assert result == mock_templates
            mock_template_service.get_all_templates.assert_called()

            # Reset mock for next iteration
            mock_template_service.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_query_logging_success(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
        mock_templates: dict[str, dict[str, Any]],
    ) -> None:
        """Test proper logging on successful query handling."""
        # Setup mock
        mock_template_service.get_all_templates.return_value = mock_templates
        
        with patch('src.application.queries.handlers.get_templates_handler.logger') as mock_logger:
            result = await handler.handle(sample_query)

        assert result == mock_templates

        # Verify logging was called twice (info at start and success)
        assert mock_logger.info.call_count == 2
        
        # Check initial log message
        initial_log_call = mock_logger.info.call_args_list[0]
        initial_message = initial_log_call[0][0]
        initial_extra = initial_log_call[1]["extra"]
        
        assert "Processing get templates query" in initial_message
        assert initial_extra["user_id"] == "test_user"

        # Check success log message
        success_log_call = mock_logger.info.call_args_list[1]
        success_message = success_log_call[0][0]
        success_extra = success_log_call[1]["extra"]
        
        assert "Successfully retrieved 4 templates" in success_message
        assert success_extra["template_count"] == 4
        assert success_extra["template_names"] == ["COMPREHENSIVE", "FINANCIAL_FOCUSED", "RISK_FOCUSED", "BUSINESS_FOCUSED"]

    @pytest.mark.asyncio
    async def test_handle_query_logging_error(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test proper logging on query handling error."""
        # Setup mock to raise exception
        service_error = Exception("Template service error")
        mock_template_service.get_all_templates.side_effect = service_error

        with patch('src.application.queries.handlers.get_templates_handler.logger') as mock_logger:
            with pytest.raises(Exception, match="Template service error"):
                await handler.handle(sample_query)

        # Verify initial info log was called
        mock_logger.info.assert_called_once()
        
        # Verify error log was called
        mock_logger.error.assert_called_once()
        
        error_log_call = mock_logger.error.call_args
        error_message = error_log_call[0][0]
        error_extra = error_log_call[1]["extra"]
        
        assert "Failed to retrieve templates" in error_message
        assert error_extra["error"] == "Template service error"
        
        # Verify exc_info was set for stack trace
        assert error_log_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: GetTemplatesQueryHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler is properly typed
        assert hasattr(handler, 'handle')
        
        # The handler should be a QueryHandler with proper generics
        from src.application.base.handlers import QueryHandler
        assert isinstance(handler, QueryHandler)
        
        # Verify query type method
        assert handler.query_type() == GetTemplatesQuery

    @pytest.mark.asyncio
    async def test_template_data_structure_validation(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test that handler properly handles various template data structures."""
        # Test with different template data structures
        template_variations = [
            # Empty templates
            {},
            # Single template
            {
                "SIMPLE": {
                    "name": "Simple Template",
                    "description": "Basic analysis",
                    "schemas": ["BusinessAnalysisSection"],
                    "schema_count": 1,
                }
            },
            # Complex template with additional fields
            {
                "COMPLEX": {
                    "name": "Complex Template",
                    "description": "Advanced analysis with extra metadata",
                    "schemas": ["BusinessAnalysisSection", "RiskFactorsAnalysisSection"],
                    "schema_count": 2,
                    "estimated_processing_time": "3-5 minutes",
                    "recommended_for": "Comprehensive analysis",
                    "difficulty_level": "advanced",
                    "output_format": "structured",
                    "custom_metadata": {
                        "version": "2.0",
                        "last_updated": "2024-01-15",
                    }
                }
            },
        ]

        for template_data in template_variations:
            # Setup mock for each variation
            mock_template_service.get_all_templates.return_value = template_data
            
            result = await handler.handle(sample_query)

            # Verify result matches template data exactly
            assert result == template_data
            mock_template_service.get_all_templates.assert_called()

            # Reset mock for next iteration
            mock_template_service.reset_mock()

    @pytest.mark.asyncio
    async def test_service_integration_contract(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test that handler correctly integrates with template service contract."""
        # Setup mock with realistic template data
        realistic_templates = {
            "COMPREHENSIVE": {
                "name": "Comprehensive Analysis",
                "description": "Complete SEC filing analysis with all available schemas",
                "schemas": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection", 
                    "FinancialAnalysisSection",
                    "MarketAnalysisSection",
                    "CompetitiveAnalysisSection",
                    "ESGAnalysisSection"
                ],
                "schema_count": 6,
                "estimated_processing_time": "5-8 minutes",
                "recommended_for": "Complete company analysis and due diligence",
                "complexity": "high"
            }
        }
        
        mock_template_service.get_all_templates.return_value = realistic_templates
        
        result = await handler.handle(sample_query)

        # Verify service contract adherence
        assert result == realistic_templates
        
        # Verify service method was called without parameters
        mock_template_service.get_all_templates.assert_called_once_with()
        
        # Verify no additional service methods were called
        assert len(mock_template_service.method_calls) == 1

    @pytest.mark.asyncio
    async def test_query_without_user_id(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        mock_templates: dict[str, dict[str, Any]],
    ) -> None:
        """Test handling query without user_id."""
        query = GetTemplatesQuery()  # No user_id provided
        
        # Setup mock
        mock_template_service.get_all_templates.return_value = mock_templates
        
        result = await handler.handle(query)

        # Verify result is returned correctly
        assert result == mock_templates
        
        # Verify service was called (user_id is not required for template retrieval)
        mock_template_service.get_all_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_consecutive_queries(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        mock_templates: dict[str, dict[str, Any]],
    ) -> None:
        """Test handling multiple consecutive queries."""
        queries = [
            GetTemplatesQuery(user_id="user1"),
            GetTemplatesQuery(user_id="user2"),
            GetTemplatesQuery(),  # No user_id
        ]

        # Setup mock to return same templates for all queries
        mock_template_service.get_all_templates.return_value = mock_templates

        for query in queries:
            result = await handler.handle(query)
            assert result == mock_templates

        # Verify service was called for each query
        assert mock_template_service.get_all_templates.call_count == len(queries)

    @pytest.mark.asyncio
    async def test_error_handling_preserves_exception_details(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
        sample_query: GetTemplatesQuery,
    ) -> None:
        """Test that error handling preserves original exception details."""
        # Create specific exception with details
        specific_error = ValueError("Invalid template configuration in service")
        mock_template_service.get_all_templates.side_effect = specific_error

        with pytest.raises(ValueError, match="Invalid template configuration in service"):
            await handler.handle(sample_query)

        # Verify the original exception type and message are preserved
        mock_template_service.get_all_templates.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_with_realistic_service_response(
        self,
        handler: GetTemplatesQueryHandler,
        mock_template_service: MagicMock,
    ) -> None:
        """Test handler integration with realistic service response."""
        # Create realistic query (API client requesting template info)
        realistic_query = GetTemplatesQuery(user_id="api_client_dashboard")

        # Create comprehensive realistic templates response
        realistic_service_response = {
            "COMPREHENSIVE": {
                "name": "Comprehensive Analysis",
                "description": "Complete SEC filing analysis covering all major areas including business operations, financial performance, risk factors, market position, competitive landscape, and ESG considerations",
                "schemas": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                    "FinancialAnalysisSection", 
                    "MarketAnalysisSection",
                    "CompetitiveAnalysisSection",
                    "ESGAnalysisSection"
                ],
                "schema_count": 6,
                "estimated_processing_time": "5-8 minutes",
                "recommended_for": "Complete due diligence, investment analysis, comprehensive company research",
                "complexity": "high",
                "token_estimate": "15000-25000",
                "use_cases": ["M&A due diligence", "Investment research", "Risk assessment", "ESG reporting"]
            },
            "FINANCIAL_FOCUSED": {
                "name": "Financial Analysis",
                "description": "Focused analysis of financial performance, metrics, and business fundamentals",
                "schemas": [
                    "FinancialAnalysisSection",
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection"
                ],
                "schema_count": 3,
                "estimated_processing_time": "2-4 minutes",
                "recommended_for": "Financial due diligence, earnings analysis, performance evaluation",
                "complexity": "medium",
                "token_estimate": "8000-12000",
                "use_cases": ["Earnings analysis", "Financial health check", "Credit analysis"]
            }
        }

        # Setup service mock
        mock_template_service.get_all_templates.return_value = realistic_service_response

        result = await handler.handle(realistic_query)

        # Verify complete response passthrough
        assert result == realistic_service_response
        assert len(result) == 2
        assert "COMPREHENSIVE" in result
        assert "FINANCIAL_FOCUSED" in result
        
        # Verify service interaction
        mock_template_service.get_all_templates.assert_called_once_with()
        
        # Verify data structure integrity
        comprehensive = result["COMPREHENSIVE"]
        assert comprehensive["schema_count"] == 6
        assert len(comprehensive["schemas"]) == 6
        assert "use_cases" in comprehensive
        
        financial = result["FINANCIAL_FOCUSED"]
        assert financial["schema_count"] == 3
        assert len(financial["schemas"]) == 3
        assert financial["complexity"] == "medium"