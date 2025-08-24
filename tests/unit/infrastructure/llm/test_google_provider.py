"""Comprehensive tests for Google Gemini LLM provider."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.value_objects import FilingType
from src.infrastructure.llm.base import (
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SubsectionAnalysisResponse,
)
from src.infrastructure.llm.google_provider import GoogleProvider
from src.infrastructure.llm.schemas import BusinessAnalysisSection
from src.infrastructure.llm.schemas.business import OperationalOverview


# Test fixtures and helpers
@pytest.fixture
def mock_google_client():
    """Mock Google GenAI client."""
    return AsyncMock()


@pytest.fixture
def google_api_key():
    """Test Google API key."""
    return "test-google-api-key"


@pytest.fixture
def company_name():
    """Test company name."""
    return "Google Inc."


@pytest.fixture
def filing_type():
    """Test filing type."""
    return FilingType.FORM_10K


@pytest.fixture
def sample_filing_sections():
    """Sample filing sections for testing."""
    return {
        "Item 1 - Business": """
            Google Inc. operates through multiple business segments including Search,
            YouTube, Google Cloud, and Other Bets. The company generates revenue
            primarily through advertising and cloud services.

            Search remains the core business, providing search and advertising services
            globally. YouTube has become a major platform for video content and advertising.
            Google Cloud offers enterprise cloud computing services.
        """,
        "Item 1A - Risk Factors": """
            The company faces various risks including:

            Competition risks: Intense competition from other technology companies
            in search, advertising, and cloud computing markets.

            Regulatory risks: Increasing government scrutiny and regulation
            of technology companies, particularly regarding data privacy and antitrust.

            Technology risks: Rapid changes in technology could impact
            the company's competitive position.
        """,
        "Item 7 - Management Discussion & Analysis": """
            Fiscal Year 2023 Performance:

            Total revenues increased 9% to $307.4 billion compared to $282.8 billion
            in the prior year. The increase was driven by growth in Search and Cloud.

            Operating income was $84.3 billion, representing 27% of total revenues.

            Google Cloud revenues grew 28% to $33.1 billion, demonstrating strong
            momentum in enterprise adoption.
        """,
    }


@pytest.fixture
def sample_business_analysis():
    """Sample business analysis response."""
    return {
        "operational_overview": {
            "description": "Google operates multiple technology platforms",
            "industry_classification": "Technology Services",
            "primary_markets": ["SEARCH", "ADVERTISING", "CLOUD"],
            "target_customers": "Consumers and enterprise clients",
            "business_model": "Advertising and subscription-based services",
        },
        "key_products": [
            {
                "name": "Google Search",
                "description": "Web search engine",
                "significance": "Core revenue driver",
            }
        ],
        "competitive_advantages": [
            {
                "advantage": "Search algorithm superiority",
                "description": "Advanced search technology",
                "competitors": ["Microsoft", "Amazon"],
                "sustainability": "Continuous innovation",
            }
        ],
        "strategic_initiatives": [
            {
                "name": "AI integration",
                "description": "Integrating AI across products",
                "impact": "Enhanced user experience",
                "timeframe": "Ongoing",
                "resource_allocation": "Significant investment",
            }
        ],
        "business_segments": [
            {
                "name": "Google Search",
                "description": "Search and advertising",
                "strategic_importance": "Core business",
                "segment_type": "SEARCH",
                "market_position": "Market leader",
                "growth_outlook": "Stable growth",
                "key_competitors": ["Microsoft Bing"],
                "relative_size": "Largest segment",
                "market_trends": "AI-powered search",
                "product_differentiation": "Superior algorithm",
            }
        ],
        "geographic_segments": [
            {
                "name": "United States",
                "description": "US operations",
                "strategic_importance": "Key market",
                "region": "NORTH_AMERICA",
                "market_position": "Strong position",
                "growth_outlook": "Steady growth",
                "key_competitors": ["Microsoft"],
                "relative_size": "Large market",
                "market_characteristics": "Mature market",
                "regulatory_environment": "Complex",
                "expansion_strategy": "AI focus",
            }
        ],
        "supply_chain": {
            "description": "Technology infrastructure",
            "key_suppliers": ["Hardware vendors", "Data centers"],
            "sourcing_strategy": "Diversified sourcing",
            "risks": "Supply chain disruptions",
        },
        "partnerships": [
            {
                "name": "Device partnerships",
                "description": "Android device manufacturers",
                "partnership_type": "Strategic",
                "strategic_value": "Market reach",
            }
        ],
    }


def create_mock_google_response(
    content: str | None = None, usage_metadata: Mock | None = None
) -> Mock:
    """Create a mock Google GenAI response."""
    mock_response = Mock()
    mock_response.text = content or '{"test": "response"}'
    mock_response.usage_metadata = usage_metadata
    return mock_response


def create_mock_usage_metadata(
    prompt_tokens: int = 1000, output_tokens: int = 500
) -> Mock:
    """Create mock usage metadata."""
    mock_usage = Mock()
    mock_usage.prompt_token_count = prompt_tokens
    mock_usage.candidates_token_count = output_tokens
    return mock_usage


@pytest.mark.unit
class TestGoogleProviderConstruction:
    """Test Google provider construction and initialization."""

    @patch("src.infrastructure.llm.google_provider.genai.Client")
    @patch("src.infrastructure.llm.google_provider.settings")
    def test_constructor_with_default_settings(self, mock_settings, mock_genai_client):
        """Test creating Google provider with default settings."""
        # Arrange
        mock_settings.google_api_key = "test-google-key"
        mock_settings.llm_model = "default"  # Use default as in settings
        mock_settings.llm_temperature = 0.1

        # Act
        provider = GoogleProvider()

        # Assert
        mock_genai_client.assert_called_once_with(api_key="test-google-key")
        assert provider.model == "default"
        assert provider.api_key == "test-google-key"

    @patch("src.infrastructure.llm.google_provider.genai.Client")
    def test_constructor_with_custom_parameters(self, mock_genai_client):
        """Test creating Google provider with custom parameters."""
        # Arrange
        api_key = "custom-google-key"
        model = "gemini-1.5-pro"

        # Act
        provider = GoogleProvider(api_key=api_key, model=model)

        # Assert
        mock_genai_client.assert_called_once_with(api_key=api_key)
        assert provider.model == model
        assert provider.api_key == api_key

    @patch("src.infrastructure.llm.google_provider.settings")
    def test_constructor_missing_api_key_raises_error(self, mock_settings):
        """Test that missing API key raises ValueError."""
        # Arrange
        mock_settings.google_api_key = None

        # Act & Assert
        with pytest.raises(ValueError, match="Google API key is required"):
            GoogleProvider()

    @patch("src.infrastructure.llm.google_provider.genai.Client")
    @patch("src.infrastructure.llm.google_provider.settings")
    def test_constructor_initializes_section_schemas(
        self, mock_settings, mock_genai_client
    ):
        """Test that constructor initializes section schemas correctly."""
        # Arrange
        mock_settings.google_api_key = "test-key"
        mock_settings.llm_model = "gemini-pro"

        # Act
        provider = GoogleProvider()

        # Assert
        assert hasattr(provider, "section_schemas")
        assert isinstance(provider.section_schemas, dict)
        assert "Item 1 - Business" in provider.section_schemas
        assert "Item 1A - Risk Factors" in provider.section_schemas


@pytest.mark.unit
class TestGoogleProviderSuccessfulExecution:
    """Test successful execution scenarios for Google provider."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch(
                "src.infrastructure.llm.google_provider.genai.Client"
            ) as mock_client_class,
            patch("src.infrastructure.llm.google_provider.settings") as mock_settings,
        ):
            mock_settings.google_api_key = "test-google-key"
            mock_settings.llm_model = "default"
            mock_settings.llm_temperature = 0.1

            self.mock_client = AsyncMock()
            mock_client_class.return_value = self.mock_client
            self.provider = GoogleProvider()

    @pytest.mark.asyncio
    async def test_analyze_filing_success_comprehensive(
        self, sample_filing_sections, company_name, filing_type
    ):
        """Test successful comprehensive filing analysis."""
        # Arrange
        # Mock section analysis responses
        section_responses = [
            SectionAnalysisResponse(
                section_name="Item 1 - Business",
                section_summary="Business analysis summary",
                consolidated_insights=[
                    "Strong market position",
                    "Diversified portfolio",
                ],
                overall_sentiment=0.8,
                critical_findings=["Market leadership in search"],
                sub_sections=[],
                processing_time_ms=1500,
                sub_section_count=0,
            ),
            SectionAnalysisResponse(
                section_name="Item 1A - Risk Factors",
                section_summary="Risk factors analysis",
                consolidated_insights=[
                    "Competition risks present",
                    "Regulatory challenges",
                ],
                overall_sentiment=-0.3,
                critical_findings=["Regulatory scrutiny increasing"],
                sub_sections=[],
                processing_time_ms=1200,
                sub_section_count=0,
            ),
            SectionAnalysisResponse(
                section_name="Item 7 - Management Discussion & Analysis",
                section_summary="MDA analysis summary",
                consolidated_insights=["Revenue growth", "Cloud expansion"],
                overall_sentiment=0.6,
                critical_findings=["Strong cloud performance"],
                sub_sections=[],
                processing_time_ms=1800,
                sub_section_count=0,
            ),
        ]

        # Mock overall analysis response
        overall_response = OverallAnalysisResponse(
            filing_summary="Google Inc. demonstrates strong technology platform growth",
            executive_summary="Comprehensive analysis shows dominant search position",
            key_insights=["Search dominance", "Cloud growth", "AI innovation"],
            financial_highlights=["Revenue increased 9% to $307.4B", "Cloud grew 28%"],
            risk_factors=["Regulatory scrutiny", "Competition"],
            opportunities=["AI integration", "Cloud expansion"],
            confidence_score=0.9,
        )

        async def mock_analyze_section(*args, **kwargs):
            # Return responses based on section name
            if "Business" in args[1]:
                return section_responses[0]
            elif "Risk Factors" in args[1]:
                return section_responses[1]
            elif "Management Discussion" in args[1]:
                return section_responses[2]
            else:
                return section_responses[0]

        with (
            patch.object(
                self.provider, "analyze_section", side_effect=mock_analyze_section
            ),
            patch.object(
                self.provider,
                "_generate_overall_analysis",
                return_value=overall_response,
            ),
        ):
            # Act
            result = await self.provider.analyze_filing(
                sample_filing_sections, filing_type, company_name
            )

            # Assert
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert result.company_name == company_name
            assert result.filing_type == filing_type.value
            assert result.total_sections_analyzed == 3
            assert result.total_sub_sections_analyzed == 0
            assert result.confidence_score == 0.9
            assert len(result.key_insights) == 3
            assert len(result.financial_highlights) == 2
            assert len(result.section_analyses) == 3

    @pytest.mark.asyncio
    async def test_analyze_section_with_structured_schema(
        self, company_name, filing_type, sample_business_analysis
    ):
        """Test successful section analysis with structured schema."""
        # Arrange
        section_text = "Google Inc. operates multiple technology platforms..."
        section_name = "Item 1 - Business"

        # Mock subsection analysis response
        mock_subsection_response = SubsectionAnalysisResponse(
            sub_section_name="Operational Overview",
            processing_time_ms=800,
            schema_type="OperationalOverview",
            analysis=sample_business_analysis["operational_overview"],
            parent_section=section_name,
            subsection_focus="Focused analysis of operational overview aspects",
        )

        # Mock section summary response
        mock_summary_response = SectionAnalysisResponse(
            section_name=section_name,
            section_summary="Comprehensive business analysis",
            consolidated_insights=["Strong platform position", "Diversified revenue"],
            overall_sentiment=0.7,
            critical_findings=["Search market leadership"],
            sub_sections=[mock_subsection_response],
            processing_time_ms=1500,
            sub_section_count=1,
        )

        with (
            patch.object(
                self.provider,
                "_analyze_with_structured_schema",
                return_value=[mock_subsection_response],
            ),
            patch.object(
                self.provider,
                "_generate_section_summary",
                return_value=mock_summary_response,
            ),
        ):
            # Act
            result = await self.provider.analyze_section(
                section_text, section_name, filing_type, company_name
            )

            # Assert
            assert isinstance(result, SectionAnalysisResponse)
            assert result.section_name == section_name
            assert result.sub_section_count == 1
            assert len(result.sub_sections) == 1
            assert result.sub_sections[0].sub_section_name == "Operational Overview"

    @pytest.mark.asyncio
    async def test_analyze_section_without_schema(self, company_name, filing_type):
        """Test section analysis for sections without specific schemas."""
        # Arrange
        section_text = "Some section content without specific schema"
        section_name = "Item 5 - Market Price"  # Not in SECTION_SCHEMAS

        # Mock section summary response
        mock_summary_response = SectionAnalysisResponse(
            section_name=section_name,
            section_summary="Section analysis without specific schema",
            consolidated_insights=["General insights"],
            overall_sentiment=0.0,
            critical_findings=["No specific findings"],
            sub_sections=[],
            processing_time_ms=500,
            sub_section_count=0,
        )

        with patch.object(
            self.provider,
            "_generate_section_summary",
            return_value=mock_summary_response,
        ):
            # Act
            result = await self.provider.analyze_section(
                section_text, section_name, filing_type, company_name
            )

            # Assert
            assert isinstance(result, SectionAnalysisResponse)
            assert result.section_name == section_name
            assert result.sub_section_count == 0
            assert len(result.sub_sections) == 0

    @pytest.mark.asyncio
    async def test_extract_subsection_text_success(self, company_name):
        """Test successful subsection text extraction."""
        # Arrange
        section_text = "Full section content with business information..."
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        extracted_text = "Relevant text for operational overview analysis"
        mock_response = create_mock_google_response(extracted_text)
        self.mock_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = await self.provider._extract_subsection_text(
            section_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
        )

        # Assert
        assert result == extracted_text
        self.mock_client.aio.models.generate_content.assert_called_once()
        call_args = self.mock_client.aio.models.generate_content.call_args
        assert (
            call_args[1]["model"] == "default"
        )  # Should match the model from settings
        assert len(call_args[1]["contents"]) == 2
        assert "text extraction specialist" in call_args[1]["contents"][0]

    @pytest.mark.asyncio
    async def test_extract_subsection_text_fallback_on_error(self, company_name):
        """Test that text extraction falls back to original text on error."""
        # Arrange
        section_text = "Original section text"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        self.mock_client.aio.models.generate_content.side_effect = Exception(
            "API error"
        )

        # Act
        result = await self.provider._extract_subsection_text(
            section_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
        )

        # Assert
        assert result == section_text  # Should return original text

    @pytest.mark.asyncio
    async def test_analyze_individual_subsection_success(
        self, company_name, filing_type, sample_business_analysis
    ):
        """Test successful individual subsection analysis."""
        # Arrange
        subsection_text = "Business operational overview content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        mock_response = create_mock_google_response(
            json.dumps(sample_business_analysis["operational_overview"])
        )
        self.mock_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = await self.provider._analyze_individual_subsection(
            subsection_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
            filing_type,
        )

        # Assert
        assert isinstance(result, SubsectionAnalysisResponse)
        assert result.sub_section_name == "Operational Overview"
        assert result.schema_type == "OperationalOverview"
        assert result.parent_section == section_name
        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0
        assert "operational overview" in result.subsection_focus.lower()

    @pytest.mark.asyncio
    async def test_generate_section_summary_success(self, company_name, filing_type):
        """Test successful section summary generation."""
        # Arrange
        sub_sections = [
            SubsectionAnalysisResponse(
                sub_section_name="Operational Overview",
                processing_time_ms=800,
                schema_type="OperationalOverview",
                analysis={"description": "Business operations"},
                parent_section="Item 1 - Business",
                subsection_focus="Business operations focus",
            )
        ]

        section_name = "Item 1 - Business"

        summary_data = {
            "section_name": section_name,
            "section_summary": "Comprehensive business analysis summary",
            "consolidated_insights": [
                "Strong market position",
                "Diversified portfolio",
            ],
            "overall_sentiment": 0.8,
            "critical_findings": ["Market leadership in search"],
        }

        mock_response = create_mock_google_response(json.dumps(summary_data))
        self.mock_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = await self.provider._generate_section_summary(
            sub_sections, section_name, filing_type, company_name
        )

        # Assert
        assert isinstance(result, SectionAnalysisResponse)
        assert result.section_name == section_name
        assert result.section_summary == summary_data["section_summary"]
        assert len(result.consolidated_insights) == 2
        assert result.overall_sentiment == 0.8
        assert len(result.sub_sections) == 1
        assert result.sub_section_count == 1

    @pytest.mark.asyncio
    async def test_generate_overall_analysis_success(self, company_name, filing_type):
        """Test successful overall analysis generation."""
        # Arrange
        section_analyses = [
            SectionAnalysisResponse(
                section_name="Item 1 - Business",
                section_summary="Business analysis",
                consolidated_insights=["Market leadership"],
                overall_sentiment=0.7,
                critical_findings=["Strong position"],
                sub_sections=[],
                processing_time_ms=1000,
                sub_section_count=0,
            )
        ]

        overall_data = {
            "filing_summary": "Google Inc. demonstrates strong performance",
            "executive_summary": "Detailed executive summary",
            "key_insights": ["Search dominance", "Cloud growth", "AI innovation"],
            "financial_highlights": ["Revenue up 9%", "Strong margins"],
            "risk_factors": ["Regulatory risks", "Competition"],
            "opportunities": ["AI growth", "Cloud expansion"],
            "confidence_score": 0.9,
        }

        mock_response = create_mock_google_response(json.dumps(overall_data))
        self.mock_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = await self.provider._generate_overall_analysis(
            section_analyses, filing_type, company_name
        )

        # Assert
        assert isinstance(result, OverallAnalysisResponse)
        assert result.filing_summary == overall_data["filing_summary"]
        assert len(result.key_insights) == 3
        assert len(result.financial_highlights) == 2
        assert result.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, company_name):
        """Test that token usage is properly tracked and logged."""
        # Arrange
        section_text = "Test section content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        usage_metadata = create_mock_usage_metadata(
            prompt_tokens=1500, output_tokens=800
        )
        mock_response = create_mock_google_response("Extracted text", usage_metadata)
        self.mock_client.aio.models.generate_content.return_value = mock_response

        with patch("src.infrastructure.llm.google_provider.logger") as mock_logger:
            # Act
            await self.provider._extract_subsection_text(
                section_text,
                subsection_name,
                OperationalOverview,
                section_name,
                company_name,
            )

            # Assert
            mock_logger.warning.assert_called_with(
                "Tokens used: %d prompt and %d output", 1500, 800
            )

    @pytest.mark.asyncio
    async def test_concurrent_subsection_analysis(
        self, company_name, filing_type, sample_business_analysis
    ):
        """Test that subsection analysis runs concurrently."""
        # Arrange
        section_text = "Business section with multiple subsections"
        section_name = "Item 1 - Business"

        # Mock multiple subsection responses
        operational_response = SubsectionAnalysisResponse(
            sub_section_name="Operational Overview",
            processing_time_ms=800,
            schema_type="OperationalOverview",
            analysis=sample_business_analysis["operational_overview"],
            parent_section=section_name,
            subsection_focus="Operational overview focus",
        )

        products_response = SubsectionAnalysisResponse(
            sub_section_name="Key Products",
            processing_time_ms=700,
            schema_type="KeyProduct",
            analysis={"products": sample_business_analysis["key_products"]},
            parent_section=section_name,
            subsection_focus="Key products focus",
        )

        # Mock extract and analyze methods
        async def mock_extract_text(*args, **kwargs):
            return "Extracted text"

        async def mock_analyze_subsection(*args, **kwargs):
            # Return different responses based on subsection name
            if "operational_overview" in args[1]:
                return operational_response
            else:
                return products_response

        with (
            patch.object(
                self.provider, "_extract_subsection_text", side_effect=mock_extract_text
            ),
            patch.object(
                self.provider,
                "_analyze_individual_subsection",
                side_effect=mock_analyze_subsection,
            ),
        ):
            # Act
            result = await self.provider._analyze_with_structured_schema(
                section_text,
                section_name,
                BusinessAnalysisSection,
                filing_type,
                company_name,
            )

            # Assert - BusinessAnalysisSection has multiple subsections
            assert len(result) >= 2
            assert any(r.sub_section_name == "Operational Overview" for r in result)
            assert any(r.sub_section_name == "Key Products" for r in result)

    @pytest.mark.asyncio
    async def test_analysis_with_focus_areas(
        self, sample_filing_sections, company_name, filing_type
    ):
        """Test filing analysis with specific focus areas."""
        # Arrange
        analysis_focus = ["financial_performance", "risk_assessment"]

        section_response = SectionAnalysisResponse(
            section_name="Item 7 - Management Discussion & Analysis",
            section_summary="MDA summary focused on financial performance",
            consolidated_insights=["Strong financial metrics", "Revenue growth"],
            overall_sentiment=0.6,
            critical_findings=["Revenue increase"],
            sub_sections=[],
            processing_time_ms=1000,
            sub_section_count=0,
        )

        overall_response = OverallAnalysisResponse(
            filing_summary="Focused analysis on financial performance and risks",
            executive_summary="Executive summary with focus areas",
            key_insights=["Financial strength", "Risk management"],
            financial_highlights=["Revenue up 9%"],
            risk_factors=["Regulatory risks"],
            opportunities=["Growth potential"],
            confidence_score=0.85,
        )

        with (
            patch.object(
                self.provider, "analyze_section", return_value=section_response
            ),
            patch.object(
                self.provider,
                "_generate_overall_analysis",
                return_value=overall_response,
            ),
        ):
            # Act
            result = await self.provider.analyze_filing(
                {"Item 7 - Management Discussion & Analysis": "MDA content"},
                filing_type,
                company_name,
                analysis_focus,
            )

            # Assert
            assert "financial performance and risks" in result.filing_summary.lower()
            assert result.confidence_score == 0.85


@pytest.mark.unit
class TestGoogleProviderErrorHandling:
    """Test error handling scenarios for Google provider."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch(
                "src.infrastructure.llm.google_provider.genai.Client"
            ) as mock_client_class,
            patch("src.infrastructure.llm.google_provider.settings") as mock_settings,
        ):
            mock_settings.google_api_key = "test-google-key"
            mock_settings.llm_model = "default"
            mock_settings.llm_temperature = 0.1

            self.mock_client = AsyncMock()
            mock_client_class.return_value = self.mock_client
            self.provider = GoogleProvider()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, company_name, filing_type):
        """Test handling of API errors."""
        # Arrange
        self.mock_client.aio.models.generate_content.side_effect = Exception(
            "API error"
        )

        section_text = "Test content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        # Act
        result = await self.provider._extract_subsection_text(
            section_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
        )

        # Assert - should fallback to original text
        assert result == section_text

    @pytest.mark.asyncio
    async def test_individual_subsection_error_handling(
        self, company_name, filing_type
    ):
        """Test error handling in individual subsection analysis."""
        # Arrange
        self.mock_client.aio.models.generate_content.side_effect = Exception(
            "Analysis failed"
        )

        subsection_text = "Test content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        # Act
        result = await self.provider._analyze_individual_subsection(
            subsection_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
            filing_type,
        )

        # Assert - should return fallback response
        assert isinstance(result, SubsectionAnalysisResponse)
        assert "Analysis failed" in result.subsection_focus
        assert result.schema_type == "OperationalOverview"

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, company_name, filing_type):
        """Test handling of empty responses from API."""
        # Arrange - Mock response with empty text that should trigger the ValueError
        mock_response = Mock()
        mock_response.text = (
            ""  # Empty text should trigger ValueError in implementation
        )
        mock_response.usage_metadata = None
        self.mock_client.aio.models.generate_content.return_value = mock_response

        subsection_text = "Test content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        # Act
        result = await self.provider._analyze_individual_subsection(
            subsection_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
            filing_type,
        )

        # Assert - should return fallback response for empty content
        assert isinstance(result, SubsectionAnalysisResponse)
        assert "Analysis failed" in result.subsection_focus

    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, company_name, filing_type):
        """Test handling of invalid JSON responses."""
        # Arrange
        mock_response = create_mock_google_response(content="invalid json {")
        self.mock_client.aio.models.generate_content.return_value = mock_response

        subsection_text = "Test content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        # Act
        result = await self.provider._analyze_individual_subsection(
            subsection_text,
            subsection_name,
            OperationalOverview,
            section_name,
            company_name,
            filing_type,
        )

        # Assert - should return fallback response
        assert isinstance(result, SubsectionAnalysisResponse)
        assert "Analysis failed" in result.subsection_focus

    @pytest.mark.asyncio
    async def test_section_summary_generation_error_handling(
        self, company_name, filing_type
    ):
        """Test error handling in section summary generation."""
        # Arrange
        sub_sections = [
            SubsectionAnalysisResponse(
                sub_section_name="Test",
                processing_time_ms=800,
                schema_type="TestSchema",
                analysis={},
                parent_section="Test Section",
                subsection_focus="Test focus",
            )
        ]

        self.mock_client.aio.models.generate_content.side_effect = Exception(
            "Summary failed"
        )

        # Act
        result = await self.provider._generate_section_summary(
            sub_sections, "Test Section", filing_type, company_name
        )

        # Assert - should return fallback response
        assert isinstance(result, SectionAnalysisResponse)
        assert result.section_name == "Test Section"
        assert "Analysis completed" in result.section_summary
        assert len(result.sub_sections) == 1

    @pytest.mark.asyncio
    async def test_overall_analysis_generation_error_handling(
        self, company_name, filing_type
    ):
        """Test error handling in overall analysis generation."""
        # Arrange
        section_analyses = [
            SectionAnalysisResponse(
                section_name="Test Section",
                section_summary="Test summary",
                consolidated_insights=[],
                overall_sentiment=0.0,
                critical_findings=[],
                sub_sections=[],
                processing_time_ms=1000,
                sub_section_count=0,
            )
        ]

        self.mock_client.aio.models.generate_content.side_effect = Exception(
            "Overall analysis failed"
        )

        # Act
        result = await self.provider._generate_overall_analysis(
            section_analyses, filing_type, company_name
        )

        # Assert - should return fallback response
        assert isinstance(result, OverallAnalysisResponse)
        assert company_name in result.filing_summary
        assert result.confidence_score == 0.8  # Default fallback confidence

    @pytest.mark.asyncio
    async def test_token_usage_unavailable_handling(self, company_name):
        """Test graceful handling when token usage info is unavailable."""
        # Arrange
        section_text = "Test content"
        subsection_name = "operational_overview"
        section_name = "Item 1 - Business"

        # Mock response with no usage metadata
        mock_response = create_mock_google_response(
            "Extracted text", usage_metadata=None
        )
        self.mock_client.aio.models.generate_content.return_value = mock_response

        with patch("src.infrastructure.llm.google_provider.logger") as mock_logger:
            # Act
            result = await self.provider._extract_subsection_text(
                section_text,
                subsection_name,
                OperationalOverview,
                section_name,
                company_name,
            )

            # Assert - should not crash and should not log token usage
            assert result == "Extracted text"
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_single_analysis_on_subsection_failure(
        self, company_name, filing_type, sample_business_analysis
    ):
        """Test fallback to single analysis when all subsections fail."""
        # Arrange
        section_text = "Business section content"
        section_name = "Item 1 - Business"

        # Mock all extractions to fail
        async def mock_extract_fail(*args, **kwargs):
            raise Exception("Extraction failed")

        # Mock successful fallback analysis
        mock_response = create_mock_google_response(
            json.dumps(sample_business_analysis)
        )

        with (
            patch.object(
                self.provider, "_extract_subsection_text", side_effect=mock_extract_fail
            ),
        ):
            self.mock_client.aio.models.generate_content.return_value = mock_response

            # Act
            result = await self.provider._analyze_with_structured_schema(
                section_text,
                section_name,
                BusinessAnalysisSection,
                filing_type,
                company_name,
            )

            # Assert - should fall back to single analysis
            assert len(result) >= 1
            # Should contain fallback responses for failed subsections
            assert any("Analysis failed" in r.subsection_focus for r in result)


@pytest.mark.unit
class TestGoogleProviderEdgeCases:
    """Test edge cases and boundary conditions for Google provider."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch(
                "src.infrastructure.llm.google_provider.genai.Client"
            ) as mock_client_class,
            patch("src.infrastructure.llm.google_provider.settings") as mock_settings,
        ):
            mock_settings.google_api_key = "test-google-key"
            mock_settings.llm_model = "default"
            mock_settings.llm_temperature = 0.1

            self.mock_client = AsyncMock()
            mock_client_class.return_value = self.mock_client
            self.provider = GoogleProvider()

    @pytest.mark.asyncio
    async def test_empty_filing_sections_handling(self, company_name, filing_type):
        """Test handling of empty filing sections dictionary."""
        # Arrange
        empty_sections = {}

        # Mock overall analysis to return default values for empty filing
        mock_overall_response = OverallAnalysisResponse(
            filing_summary="No filing content to analyze",
            executive_summary="Empty filing provided",
            key_insights=[],
            financial_highlights=[],
            risk_factors=[],
            opportunities=[],
            confidence_score=0.0,
        )

        with patch.object(
            self.provider,
            "_generate_overall_analysis",
            return_value=mock_overall_response,
        ):
            # Act
            result = await self.provider.analyze_filing(
                empty_sections, filing_type, company_name
            )

            # Assert
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert result.total_sections_analyzed == 0
            assert len(result.section_analyses) == 0

    @pytest.mark.asyncio
    async def test_sections_with_only_whitespace(self, company_name, filing_type):
        """Test handling of sections containing only whitespace."""
        # Arrange
        whitespace_sections = {
            "Item 1 - Business": "   \n\t   ",
            "Item 1A - Risk Factors": "",
            "Valid Section": "This has actual content",
        }

        mock_section_response = SectionAnalysisResponse(
            section_name="Valid Section",
            section_summary="Valid section analysis",
            consolidated_insights=["Valid insight"],
            overall_sentiment=0.0,
            critical_findings=["Valid finding"],
            sub_sections=[],
            processing_time_ms=500,
            sub_section_count=0,
        )

        mock_overall_response = OverallAnalysisResponse(
            filing_summary="Analysis of valid sections only",
            executive_summary="Executive summary",
            key_insights=["Valid insight"],
            financial_highlights=["No financial data"],
            risk_factors=["No risks identified"],
            opportunities=["Limited opportunities"],
            confidence_score=0.5,
        )

        with (
            patch.object(
                self.provider, "analyze_section", return_value=mock_section_response
            ),
            patch.object(
                self.provider,
                "_generate_overall_analysis",
                return_value=mock_overall_response,
            ),
        ):
            # Act
            result = await self.provider.analyze_filing(
                whitespace_sections, filing_type, company_name
            )

            # Assert - should only analyze sections with content
            assert result.total_sections_analyzed == 1
            assert len(result.section_analyses) == 1
            assert result.section_analyses[0].section_name == "Valid Section"

    @pytest.mark.asyncio
    async def test_analysis_timestamp_accuracy(self, company_name, filing_type):
        """Test that analysis timestamps are accurate and in correct format."""
        # Arrange
        sections = {"Item 1 - Business": "Business content"}

        mock_section_response = SectionAnalysisResponse(
            section_name="Item 1 - Business",
            section_summary="Timestamped analysis",
            consolidated_insights=["Timestamp test"],
            overall_sentiment=0.0,
            critical_findings=["Timestamp verified"],
            sub_sections=[],
            processing_time_ms=500,
            sub_section_count=0,
        )

        mock_overall_response = OverallAnalysisResponse(
            filing_summary="Timestamp test analysis",
            executive_summary="Testing timestamp functionality",
            key_insights=["Timestamp insight"],
            financial_highlights=["No financial data"],
            risk_factors=["No risks"],
            opportunities=["Timestamp accuracy"],
            confidence_score=1.0,
        )

        before_analysis = datetime.now(UTC)

        with (
            patch.object(
                self.provider, "analyze_section", return_value=mock_section_response
            ),
            patch.object(
                self.provider,
                "_generate_overall_analysis",
                return_value=mock_overall_response,
            ),
        ):
            # Act
            result = await self.provider.analyze_filing(
                sections, filing_type, company_name
            )

        after_analysis = datetime.now(UTC)

        # Assert
        assert isinstance(result, ComprehensiveAnalysisResponse)

        # Parse the timestamp and verify it's within expected range
        analysis_timestamp = datetime.fromisoformat(
            result.analysis_timestamp.replace('Z', '+00:00')
        )
        assert before_analysis <= analysis_timestamp <= after_analysis

        # Verify ISO format
        assert 'T' in result.analysis_timestamp
        assert result.analysis_timestamp.endswith(('Z', '+00:00', '-00:00'))

    @pytest.mark.asyncio
    async def test_processing_time_measurement_accuracy(
        self, company_name, filing_type
    ):
        """Test that processing time measurements are reasonably accurate."""
        # Arrange
        sections = {"Item 1 - Business": "Business content"}

        # Mock responses with artificial delay
        async def delayed_section_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return SectionAnalysisResponse(
                section_name="Item 1 - Business",
                section_summary="Delayed analysis",
                consolidated_insights=["Timing test"],
                overall_sentiment=0.0,
                critical_findings=["Timing verified"],
                sub_sections=[],
                processing_time_ms=100,  # Should be overridden
                sub_section_count=0,
            )

        async def delayed_overall_analysis(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return OverallAnalysisResponse(
                filing_summary="Timing test analysis",
                executive_summary="Testing timing functionality",
                key_insights=["Timing insight"],
                financial_highlights=["No financial data"],
                risk_factors=["No risks"],
                opportunities=["Timing accuracy"],
                confidence_score=1.0,
            )

        with (
            patch.object(
                self.provider, "analyze_section", side_effect=delayed_section_analysis
            ),
            patch.object(
                self.provider,
                "_generate_overall_analysis",
                side_effect=delayed_overall_analysis,
            ),
        ):
            # Act
            result = await self.provider.analyze_filing(
                sections, filing_type, company_name
            )

            # Assert
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert result.total_processing_time_ms is not None
            # Should be at least 150ms (100 + 50 from delays) but allow for some variance
            assert result.total_processing_time_ms >= 100
            # Should be reasonable (less than 10 seconds for this test)
            assert result.total_processing_time_ms < 10000


@pytest.mark.unit
class TestSentimentUtility:
    """Test sentiment conversion utility function."""

    def test_sentiment_to_score_numeric_values(self):
        """Test sentiment_to_score with numeric values."""
        from src.infrastructure.llm.google_provider import sentiment_to_score

        # Test integer input
        assert sentiment_to_score(1) == 1.0
        assert sentiment_to_score(0) == 0.0
        assert sentiment_to_score(-1) == -1.0

        # Test float input
        assert sentiment_to_score(0.5) == 0.5
        assert sentiment_to_score(-0.3) == -0.3

    def test_sentiment_to_score_string_values(self):
        """Test sentiment_to_score with string values."""
        from src.infrastructure.llm.google_provider import sentiment_to_score

        # Test positive sentiments
        assert sentiment_to_score("Optimistic") == 1.0
        assert sentiment_to_score("Positive") == 1.0

        # Test neutral sentiments
        assert sentiment_to_score("Neutral") == 0.0
        assert sentiment_to_score("Cautious") == 0.0

        # Test negative sentiment
        assert sentiment_to_score("Negative") == -1.0

        # Test unknown sentiment
        assert sentiment_to_score("Unknown") == 0.0
