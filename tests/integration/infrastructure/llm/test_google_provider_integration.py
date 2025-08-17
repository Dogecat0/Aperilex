"""Integration test for Google Provider with AnalysisOrchestrator."""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.value_objects import FilingType
from src.infrastructure.llm import GoogleProvider
from src.infrastructure.llm.base import ComprehensiveAnalysisResponse


class TestGoogleProviderIntegration:
    """Test Google Provider integration with the system."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Google API key not configured for integration tests",
    )
    async def test_google_provider_with_real_api(self):
        """Test Google provider with real API (requires GOOGLE_API_KEY env var)."""
        provider = GoogleProvider()

        # Small test filing sections
        filing_sections = {
            "Item 1 - Business": (
                "Apple Inc. designs, manufactures, and markets smartphones, personal computers, "
                "tablets, wearables, and accessories worldwide. The company offers iPhone, "
                "a line of smartphones; Mac, a line of personal computers; iPad, a line of "
                "multi-purpose tablets; and wearables, home, and accessories comprising AirPods, "
                "Apple TV, Apple Watch, Beats products, HomePod, and iPod touch."
            ),
            "Item 1A - Risk Factors": (
                "The Company's business, reputation, results of operations, financial condition "
                "and stock price can be adversely affected by various risks. These include "
                "global and regional economic conditions, competition, supply chain disruptions, "
                "and changes in laws and regulations."
            ),
        }

        result = await provider.analyze_filing(
            filing_sections=filing_sections,
            filing_type=FilingType.FORM_10K,
            company_name="Apple Inc.",
            analysis_focus=["business model", "key risks"],
        )

        assert isinstance(result, ComprehensiveAnalysisResponse)
        assert result.company_name == "Apple Inc."
        assert result.filing_type == "10-K"
        assert len(result.section_analyses) == 2
        assert result.filing_summary
        assert result.executive_summary

    @pytest.mark.asyncio
    async def test_google_provider_mocked_integration(self):
        """Test Google provider integration with mocked API calls."""
        with patch("src.infrastructure.llm.google_provider.genai.Client") as mock_genai:
            # Setup mock client
            mock_client = Mock()
            mock_client.aio = Mock()
            mock_client.aio.models = Mock()

            # Mock analysis response
            mock_response = Mock()
            mock_response.text = '{"operational_overview": {"description": "Technology company", "industry_classification": "Technology", "primary_markets": ["Global"], "business_model": "Product sales", "revenue_model": "Direct"}}'

            mock_client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )
            mock_genai.return_value = mock_client

            # Create provider
            provider = GoogleProvider(api_key="test-key")

            # Test filing sections
            filing_sections = {
                "Item 1 - Business": "A" * 200,  # Long enough text
            }

            result = await provider.analyze_filing(
                filing_sections=filing_sections,
                filing_type=FilingType.FORM_10K,
                company_name="Test Corp",
            )

            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert result.company_name == "Test Corp"
            assert result.filing_type == "10-K"
            assert result.total_sections_analyzed >= 0

    def test_google_provider_can_be_instantiated(self):
        """Test that GoogleProvider can be instantiated with proper config."""
        with patch("src.infrastructure.llm.google_provider.genai.Client"):
            provider = GoogleProvider(api_key="test-key")
            assert provider.model == "default"
            assert provider.api_key == "test-key"
            assert len(provider.section_schemas) > 0

    def test_google_provider_compatible_with_base_interface(self):
        """Test that GoogleProvider implements BaseLLMProvider interface."""
        from src.infrastructure.llm.base import BaseLLMProvider

        with patch("src.infrastructure.llm.google_provider.genai.Client"):
            provider = GoogleProvider(api_key="test-key")

            # Check it's an instance of the base class
            assert isinstance(provider, BaseLLMProvider)

            # Check required methods exist
            assert hasattr(provider, "analyze_filing")
            assert hasattr(provider, "analyze_section")

            # Check methods are callable
            assert callable(provider.analyze_filing)
            assert callable(provider.analyze_section)
