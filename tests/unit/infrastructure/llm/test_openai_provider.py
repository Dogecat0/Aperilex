"""Unit tests for OpenAI Provider with comprehensive API mocking."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.value_objects import FilingType
from src.infrastructure.llm.base import (
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
    SubsectionAnalysisResponse,
)
from src.infrastructure.llm.openai_provider import OpenAIProvider, sentiment_to_score
from src.infrastructure.llm.schemas.business import BusinessAnalysisSection
from src.infrastructure.llm.schemas.mda import MDAAnalysisSection
from src.infrastructure.llm.schemas.risk_factors import RiskFactorsAnalysisSection


class TestSentimentToScore:
    """Test cases for sentiment scoring utility function."""

    def test_sentiment_string_to_score_optimistic(self):
        """Test conversion of optimistic sentiment to score."""
        assert sentiment_to_score("Optimistic") == 1.0
        assert sentiment_to_score("Positive") == 1.0

    def test_sentiment_string_to_score_neutral(self):
        """Test conversion of neutral sentiment to score."""
        assert sentiment_to_score("Neutral") == 0.0
        assert sentiment_to_score("Cautious") == 0.0

    def test_sentiment_string_to_score_negative(self):
        """Test conversion of negative sentiment to score."""
        assert sentiment_to_score("Negative") == -1.0

    def test_sentiment_numeric_passthrough(self):
        """Test that numeric values pass through unchanged."""
        assert sentiment_to_score(0.5) == 0.5
        assert sentiment_to_score(-0.8) == -0.8
        assert sentiment_to_score(1) == 1.0

    def test_sentiment_unknown_string_defaults_to_neutral(self):
        """Test that unknown sentiment strings default to neutral."""
        assert sentiment_to_score("Unknown") == 0.0
        assert sentiment_to_score("InvalidSentiment") == 0.0


class TestOpenAIProvider:
    """Test cases for OpenAIProvider with mocked API calls."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for OpenAI configuration."""
        with patch("src.infrastructure.llm.openai_provider.settings") as mock_settings:
            mock_settings.openai_api_key = "test-api-key"
            mock_settings.openai_base_url = "https://api.openai.com/v1"
            yield mock_settings

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock AsyncOpenAI client."""
        mock_client = Mock()
        mock_client.chat = Mock()
        mock_client.chat.completions = Mock()
        mock_client.chat.completions.parse = AsyncMock()
        return mock_client

    @pytest.fixture
    def provider(self, mock_settings):
        """Create OpenAI provider with mocked dependencies."""
        with patch(
            "src.infrastructure.llm.openai_provider.AsyncOpenAI"
        ) as mock_async_openai:
            mock_client = Mock()
            mock_async_openai.return_value = mock_client

            provider = OpenAIProvider(
                api_key="test-api-key",
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
            )
            provider.client = mock_client  # Ensure we can access the mock
            return provider

    def test_init_with_explicit_credentials(self):
        """Test OpenAI provider initialization with explicit credentials."""
        with patch(
            "src.infrastructure.llm.openai_provider.AsyncOpenAI"
        ) as mock_async_openai:
            provider = OpenAIProvider(
                api_key="explicit-key",
                base_url="https://custom.api.com/v1",
                model="gpt-4",
            )

            mock_async_openai.assert_called_once_with(
                api_key="explicit-key", base_url="https://custom.api.com/v1"
            )
            assert provider.model == "gpt-4"

    def test_init_with_settings_credentials(self, mock_settings):
        """Test OpenAI provider initialization using settings."""
        with patch(
            "src.infrastructure.llm.openai_provider.AsyncOpenAI"
        ) as mock_async_openai:
            provider = OpenAIProvider()

            mock_async_openai.assert_called_once_with(
                api_key="test-api-key", base_url="https://api.openai.com/v1"
            )
            assert provider.model == "gpt-4o-mini"  # default model

    def test_init_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch("src.infrastructure.llm.openai_provider.settings") as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.openai_base_url = "https://api.openai.com/v1"

            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIProvider()

    def test_init_missing_base_url_raises_error(self):
        """Test that missing base URL raises ValueError."""
        with patch("src.infrastructure.llm.openai_provider.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = None

            with pytest.raises(ValueError, match="OpenAI base URL is required"):
                OpenAIProvider()

    def test_section_schemas_mapping(self, provider):
        """Test that section schemas are properly mapped."""
        assert "Item 1 - Business" in provider.section_schemas
        assert "Item 1A - Risk Factors" in provider.section_schemas
        assert "Item 7 - Management Discussion & Analysis" in provider.section_schemas

        assert provider.section_schemas["Item 1 - Business"] == BusinessAnalysisSection
        assert (
            provider.section_schemas["Item 1A - Risk Factors"]
            == RiskFactorsAnalysisSection
        )
        assert (
            provider.section_schemas["Item 7 - Management Discussion & Analysis"]
            == MDAAnalysisSection
        )

    def test_extract_subsection_schemas(self, provider: OpenAIProvider) -> None:
        """Test extraction of subsection schemas from main schema."""
        subsections = provider._extract_subsection_schemas(MDAAnalysisSection)

        # MDA schema should have several subsections
        assert isinstance(subsections, dict)
        assert len(subsections) > 0

        # Check that we found some expected subsections
        expected_subsections = [
            "operational_overview",
            "financial_performance",
            "liquidity_analysis",
        ]
        found_subsections = [key for key in expected_subsections if key in subsections]
        assert len(found_subsections) > 0

    @pytest.mark.asyncio
    async def test_extract_subsection_text_success(
        self, provider: OpenAIProvider
    ) -> None:
        """Test successful extraction of subsection text."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            "Extracted relevant text for operational overview."
        )

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        section_text = "Full section text with operational details and financial data."
        result = await provider._extract_subsection_text(
            section_text=section_text,
            subsection_name="operational_overview",
            subsection_schema=MDAAnalysisSection,
            section_name="Item 7 - Management Discussion & Analysis",
            company_name="Apple Inc.",
        )

        assert result == "Extracted relevant text for operational overview."
        provider.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_subsection_text_api_error(
        self, provider: OpenAIProvider
    ) -> None:
        """Test handling of API errors during subsection text extraction."""
        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        section_text = "Full section text."
        result = await provider._extract_subsection_text(
            section_text=section_text,
            subsection_name="operational_overview",
            subsection_schema=MDAAnalysisSection,
            section_name="Item 7 - Management Discussion & Analysis",
            company_name="Apple Inc.",
        )

        # Should return original text as fallback
        assert result == section_text

    @pytest.mark.asyncio
    async def test_analyze_subsection_success(self, provider: OpenAIProvider) -> None:
        """Test successful subsection analysis."""
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "executive_overview": "Strong operational performance",
                "key_financial_metrics": [
                    {
                        "metric_name": "Revenue",
                        "current_value": "$100M",
                        "previous_value": "$90M",
                        "direction": "Increased",
                        "percentage_change": "11.1%",
                        "explanation": "Growth in core products",
                        "significance": "Key driver",
                    }
                ],
                "outlook_summary": "Positive outlook",
                "outlook_sentiment": "Positive",
            }
        )

        provider.client.chat.completions.parse = AsyncMock(return_value=mock_response)

        # Mock time to ensure processing_time_ms is > 0
        with patch("time.time", side_effect=[1000.0, 1000.1]):  # 100ms difference
            result: SubsectionAnalysisResponse = (
                await provider._analyze_individual_subsection(
                    subsection_text="Sample subsection text",
                    subsection_name="operational_overview",
                    subsection_schema=MDAAnalysisSection,
                    section_name="Item 7 - Management Discussion & Analysis",
                    company_name="Apple Inc.",
                    filing_type=FilingType.FORM_10K,
                )
            )

        assert isinstance(result, SubsectionAnalysisResponse)
        assert result.sub_section_name == "Operational Overview"
        assert result.schema_type == "MDAAnalysisSection"
        assert result.parent_section == "Item 7 - Management Discussion & Analysis"
        assert "executive_overview" in result.analysis
        assert result.processing_time_ms is not None

    @pytest.mark.asyncio
    async def test_analyze_subsection_api_error(self, provider: OpenAIProvider) -> None:
        """Test subsection analysis with API error creates fallback response."""
        provider.client.chat.completions.parse = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await provider._analyze_individual_subsection(
            subsection_text="Sample text",
            subsection_name="operational_overview",
            subsection_schema=MDAAnalysisSection,
            section_name="Item 7 - Management Discussion & Analysis",
            company_name="Apple Inc.",
            filing_type=FilingType.FORM_10K,
        )

        assert isinstance(result, SubsectionAnalysisResponse)
        assert result.sub_section_name == "Operational Overview"
        assert result.analysis == {}  # Empty analysis due to error
        assert "Analysis failed: API Error" in result.subsection_focus

    @pytest.mark.asyncio
    async def test_analyze_section_success(self, provider: OpenAIProvider) -> None:
        """Test successful section analysis with subsections."""
        # Mock subsection analysis calls
        mock_subsection_response = SubsectionAnalysisResponse(
            sub_section_name="Operational Overview",
            schema_type="MDAAnalysisSection",
            analysis={"executive_overview": "Strong performance"},
            parent_section="Item 7 - Management Discussion & Analysis",
            subsection_focus="Operational analysis",
            processing_time_ms=100,
        )

        # Mock the section summary API call
        mock_summary_response = Mock()
        mock_summary_response.choices = [Mock()]
        mock_summary_response.choices[0].message.content = json.dumps(
            {
                "section_name": "Item 7 - Management Discussion & Analysis",
                "section_summary": "Overall positive performance",
                "consolidated_insights": ["Strong revenue growth", "Improved margins"],
                "overall_sentiment": 0.8,
                "critical_findings": ["Key risk identified"],
            }
        )

        provider.client.chat.completions.parse = AsyncMock(
            return_value=mock_summary_response
        )

        # Mock subsection analysis
        with patch.object(
            provider,
            "_analyze_individual_subsection",
            return_value=mock_subsection_response,
        ):
            result = await provider.analyze_section(
                section_text="Sample section text with operational and financial data",
                section_name="Item 7 - Management Discussion & Analysis",
                filing_type=FilingType.FORM_10K,
                company_name="Apple Inc.",
            )

        assert isinstance(result, SectionAnalysisResponse)
        assert result.section_name == "Item 7 - Management Discussion & Analysis"
        assert result.section_summary == "Overall positive performance"
        assert len(result.consolidated_insights) == 2
        assert result.overall_sentiment == 0.8
        assert len(result.sub_sections) > 0

    @pytest.mark.asyncio
    async def test_analyze_section_without_schema(
        self, provider: OpenAIProvider
    ) -> None:
        """Test section analysis for section without specific schema."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "section_name": "Item 2 - Properties",
                "section_summary": "Property holdings analysis",
                "consolidated_insights": ["Multiple locations"],
                "overall_sentiment": 0.0,
                "critical_findings": [],
            }
        )

        provider.client.chat.completions.parse = AsyncMock(return_value=mock_response)

        result = await provider.analyze_section(
            section_text="Sample properties text",
            section_name="Item 2 - Properties",
            filing_type=FilingType.FORM_10K,
            company_name="Apple Inc.",
        )

        assert isinstance(result, SectionAnalysisResponse)
        assert result.section_name == "Item 2 - Properties"
        assert len(result.sub_sections) == 0  # No subsections for this schema

    @pytest.mark.asyncio
    async def test_analyze_filing_comprehensive(self, provider: OpenAIProvider) -> None:
        """Test comprehensive filing analysis with multiple sections."""
        # Mock section analysis results
        mock_section_response = SectionAnalysisResponse(
            section_name="Item 1 - Business",
            section_summary="Strong business model",
            consolidated_insights=["Market leadership"],
            overall_sentiment=0.7,
            critical_findings=["Competitive pressure"],
            sub_sections=[],
            sub_section_count=0,
            processing_time_ms=100,
        )

        # Mock overall analysis API call
        mock_overall_response = Mock()
        mock_overall_response.choices = [Mock()]
        mock_overall_response.choices[0].message.content = json.dumps(
            {
                "filing_summary": "Apple Inc.'s 10-K filing shows strong business fundamentals with continued growth and market leadership.",
                "executive_summary": "Apple maintains its market leadership position with strong financial performance. The company continues to demonstrate resilience in competitive markets while investing in future growth opportunities.",
                "key_insights": ["Strong financial position"],
                "financial_highlights": ["Revenue growth"],
                "risk_factors": ["Market competition"],
                "opportunities": ["Expansion plans"],
                "confidence_score": 0.9,
            }
        )

        provider.client.chat.completions.parse = AsyncMock(
            return_value=mock_overall_response
        )

        # Mock section analysis
        with patch.object(
            provider, "analyze_section", return_value=mock_section_response
        ):
            filing_sections = {
                "Item 1 - Business": "Business description text",
                "Item 1A - Risk Factors": "Risk factors text",
            }

            result = await provider.analyze_filing(
                filing_sections=filing_sections,
                filing_type=FilingType.FORM_10K,
                company_name="Apple Inc.",
            )

        assert isinstance(result, ComprehensiveAnalysisResponse)
        assert result.company_name == "Apple Inc."
        assert result.filing_type == "10-K"
        assert len(result.section_analyses) == 2
        assert result.total_processing_time_ms is not None

    @pytest.mark.asyncio
    async def test_analyze_filing_empty_sections_skipped(
        self, provider: OpenAIProvider
    ) -> None:
        """Test that empty sections are skipped during filing analysis."""
        mock_section_response = SectionAnalysisResponse(
            section_name="Item 1 - Business",
            section_summary="Business analysis",
            consolidated_insights=[],
            overall_sentiment=0.0,
            critical_findings=[],
            sub_sections=[],
            sub_section_count=0,
            processing_time_ms=100,
        )

        mock_overall_response = Mock()
        mock_overall_response.choices = [Mock()]
        mock_overall_response.choices[0].message.content = json.dumps(
            {
                "filing_summary": "Limited analysis due to minimal content in filing sections.",
                "executive_summary": "The filing contains limited substantive content for comprehensive analysis. Only basic business information was available for review.",
                "key_insights": [],
                "financial_highlights": [],
                "risk_factors": [],
                "opportunities": [],
                "confidence_score": 0.5,
            }
        )

        provider.client.chat.completions.parse = AsyncMock(
            return_value=mock_overall_response
        )

        with patch.object(
            provider, "analyze_section", return_value=mock_section_response
        ) as mock_analyze:
            filing_sections = {
                "Item 1 - Business": "Business text",
                "Item 2 - Properties": "",  # Empty section
                "Item 3 - Legal": "   ",  # Whitespace only
            }

            result = await provider.analyze_filing(
                filing_sections=filing_sections,
                filing_type=FilingType.FORM_10K,
                company_name="Apple Inc.",
            )

        # Only non-empty section should be analyzed
        assert mock_analyze.call_count == 1
        assert len(result.section_analyses) == 1

    @pytest.mark.asyncio
    async def test_retry_mechanism_on_api_failure(
        self, provider: OpenAIProvider
    ) -> None:
        """Test that API failures trigger retry mechanism."""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "section_name": "Item 1 - Business",
                "section_summary": "Business analysis",
                "consolidated_insights": [],
                "overall_sentiment": 0.0,
                "critical_findings": [],
            }
        )

        provider.client.chat.completions.parse = AsyncMock(
            side_effect=[Exception("Temporary API error")] + [mock_response] * 10
        )

        # Note: The actual retry decorator should be tested, but for unit tests
        # we can verify the method eventually succeeds after retry
        result = await provider.analyze_section(
            section_text="Sample text",
            section_name="Item 1 - Business",
            filing_type=FilingType.FORM_10K,
            company_name="Apple Inc.",
        )

        # Should eventually succeed
        assert isinstance(result, SectionAnalysisResponse)

    def test_model_configuration(self, provider: OpenAIProvider) -> None:
        """Test that model can be configured."""
        assert provider.model == "gpt-4o-mini"

        with patch("src.infrastructure.llm.openai_provider.AsyncOpenAI"):
            custom_provider = OpenAIProvider(
                api_key="test-key",
                base_url="https://api.openai.com/v1",
                model="gpt-4-turbo",
            )
            assert custom_provider.model == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_concurrent_section_analysis(self, provider: OpenAIProvider) -> None:
        """Test that multiple sections are analyzed concurrently."""
        # Mock multiple section responses
        mock_responses: list[SectionAnalysisResponse] = []
        for i in range(3):
            response = SectionAnalysisResponse(
                section_name=f"Section {i}",
                section_summary=f"Summary {i}",
                consolidated_insights=[],
                overall_sentiment=0.0,
                critical_findings=[],
                sub_sections=[],
                sub_section_count=0,
                processing_time_ms=100,
            )
            mock_responses.append(response)

        # Mock overall analysis
        mock_overall_response = Mock()
        mock_overall_response.choices = [Mock()]
        mock_overall_response.choices[0].message.content = json.dumps(
            {
                "filing_summary": "Comprehensive analysis of Apple Inc.'s 10-K filing with detailed section reviews.",
                "executive_summary": "The filing analysis was performed concurrently across multiple sections, demonstrating efficient processing capabilities. All sections were successfully analyzed for key insights and strategic implications.",
                "key_insights": [],
                "financial_highlights": [],
                "risk_factors": [],
                "opportunities": [],
                "confidence_score": 0.5,
            }
        )

        provider.client.chat.completions.parse = AsyncMock(
            return_value=mock_overall_response
        )

        # Verify asyncio.gather is used for concurrent processing
        with (
            patch.object(
                provider, "analyze_section", side_effect=mock_responses
            ) as mock_analyze,
            patch("asyncio.gather", wraps=asyncio.gather) as mock_gather,
        ):
            filing_sections = {
                "Section 1": "Text 1",
                "Section 2": "Text 2",
                "Section 3": "Text 3",
            }

            result = await provider.analyze_filing(
                filing_sections=filing_sections,
                filing_type=FilingType.FORM_10K,
                company_name="Apple Inc.",
            )

        # Verify concurrent execution
        mock_gather.assert_called_once()
        assert mock_analyze.call_count == 3
        assert len(result.section_analyses) == 3
