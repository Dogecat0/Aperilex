"""Unit tests for base LLM provider functionality."""

import pytest

from src.domain.value_objects import FilingType
from src.infrastructure.llm.base import (
    SECTION_SCHEMAS,
    SUBSECTION_NAME_MAP,
    AnalysisResponse,
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
    SubsectionAnalysisResponse,
    create_analysis_prompt,
    create_analysis_response,
    create_extraction_prompt,
    create_fallback_subsection_response,
    create_human_readable_name,
    create_overall_analysis_prompts,
    create_section_analysis_prompt,
    create_section_summary_prompts,
    extract_subsection_schemas,
    run_concurrent_subsection_analysis,
)
from src.infrastructure.llm.schemas.business import BusinessAnalysisSection
from src.infrastructure.llm.schemas.mda import MDAAnalysisSection
from src.infrastructure.llm.schemas.risk_factors import RiskFactorsAnalysisSection


class TestSectionSchemas:
    """Test section schema mappings."""

    def test_section_schemas_mapping(self):
        """Test that section schemas are properly mapped."""
        assert "Item 1 - Business" in SECTION_SCHEMAS
        assert "Item 1A - Risk Factors" in SECTION_SCHEMAS
        assert "Item 7 - Management Discussion & Analysis" in SECTION_SCHEMAS

        assert SECTION_SCHEMAS["Item 1 - Business"] == BusinessAnalysisSection
        assert SECTION_SCHEMAS["Item 1A - Risk Factors"] == RiskFactorsAnalysisSection
        assert (
            SECTION_SCHEMAS["Item 7 - Management Discussion & Analysis"]
            == MDAAnalysisSection
        )

    def test_subsection_name_mapping(self):
        """Test subsection name mappings."""
        assert SUBSECTION_NAME_MAP["BusinessAnalysisSection"] == "Business Analysis"
        assert SUBSECTION_NAME_MAP["RiskFactorsAnalysisSection"] == "Risk Assessment"
        assert SUBSECTION_NAME_MAP["MDAAnalysisSection"] == "Management Discussion"


class TestSchemaExtraction:
    """Test schema extraction utilities."""

    def test_extract_subsection_schemas(self):
        """Test extraction of subsection schemas from main schema."""
        subsections = extract_subsection_schemas(MDAAnalysisSection)

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

    def test_create_human_readable_name(self):
        """Test conversion of underscore names to human readable."""
        assert (
            create_human_readable_name("operational_overview") == "Operational Overview"
        )
        assert (
            create_human_readable_name("financial_performance")
            == "Financial Performance"
        )
        assert create_human_readable_name("risk_factors") == "Risk Factors"


class TestPromptCreation:
    """Test prompt creation utilities."""

    def test_create_extraction_prompt(self):
        """Test creation of text extraction prompts."""
        prompt = create_extraction_prompt(
            section_name="Item 7 - Management Discussion & Analysis",
            subsection_name="operational_overview",
            section_text="Sample section text with operational details.",
            subsection_schema=MDAAnalysisSection,
        )

        assert "Item 7 - Management Discussion & Analysis" in prompt
        assert "operational_overview" in prompt
        assert "Sample section text with operational details." in prompt

    def test_create_analysis_prompt(self):
        """Test creation of analysis prompts."""
        prompt = create_analysis_prompt(
            human_readable_name="Operational Overview",
            company_name="Apple Inc.",
            filing_type=FilingType.FORM_10K,
            section_name="Item 7 - Management Discussion & Analysis",
            subsection_text="Sample subsection text.",
        )

        assert "Operational Overview" in prompt
        assert "Apple Inc." in prompt
        assert "10-K" in prompt
        assert "Item 7 - Management Discussion & Analysis" in prompt
        assert "Sample subsection text." in prompt

    def test_create_section_analysis_prompt(self):
        """Test creation of section analysis prompts."""
        prompt = create_section_analysis_prompt(
            section_name="Item 1 - Business",
            company_name="Apple Inc.",
            filing_type=FilingType.FORM_10K,
            section_text="Business section text.",
        )

        assert "Item 1 - Business" in prompt
        assert "Apple Inc." in prompt
        assert "10-K" in prompt
        assert "Business section text." in prompt

    def test_create_section_summary_prompts(self):
        """Test creation of section summary prompts."""
        mock_subsections = [
            SubsectionAnalysisResponse(
                sub_section_name="Operational Overview",
                schema_type="MDAAnalysisSection",
                analysis={"key": "value"},
                parent_section="Item 7 - Management Discussion & Analysis",
                subsection_focus="Operations",
                processing_time_ms=100,
            )
        ]

        system_prompt, user_prompt = create_section_summary_prompts(
            sub_sections=mock_subsections,
            section_name="Item 7 - Management Discussion & Analysis",
            filing_type=FilingType.FORM_10K,
            company_name="Apple Inc.",
        )

        assert "financial analyst" in system_prompt.lower()
        assert "Apple Inc." in user_prompt
        assert "10-K" in user_prompt
        assert "Item 7 - Management Discussion & Analysis" in user_prompt

    def test_create_overall_analysis_prompts(self):
        """Test creation of overall analysis prompts."""
        mock_sections = [
            SectionAnalysisResponse(
                section_name="Item 1 - Business",
                section_summary="Strong business model",
                consolidated_insights=["Market leadership"],
                overall_sentiment=0.7,
                critical_findings=["Competitive pressure"],
                sub_sections=[],
                sub_section_count=0,
                processing_time_ms=100,
            )
        ]

        system_prompt, user_prompt = create_overall_analysis_prompts(
            section_analyses=mock_sections,
            filing_type=FilingType.FORM_10K,
            company_name="Apple Inc.",
        )

        assert "senior financial analyst" in system_prompt.lower()
        assert "Apple Inc." in user_prompt
        assert "10-K" in user_prompt
        assert "Strong business model" in user_prompt


class TestAnalysisResponse:
    """Test analysis response models."""

    def test_create_analysis_response(self):
        """Test creation of analysis response from schema type."""
        result = {
            "operational_overview": {
                "description": "Global technology company",
                "industry_classification": "Technology",
                "primary_markets": ["Technology"],
                "target_customers": "Consumers and businesses",
                "business_model": "Product sales and services",
            },
            "key_products": [
                {
                    "name": "iPhone",
                    "description": "Smartphone product line",
                    "significance": "Primary revenue driver",
                }
            ],
            "competitive_advantages": [
                {
                    "advantage": "Brand loyalty",
                    "description": "Strong customer retention",
                    "competitors": ["Samsung"],
                    "sustainability": "High",
                }
            ],
            "strategic_initiatives": [
                {
                    "name": "AI Integration",
                    "description": "Integrating AI across products",
                    "impact": "Enhanced user experience",
                    "timeframe": "2024-2025",
                    "resource_allocation": "Significant R&D investment",
                }
            ],
            "business_segments": [
                {
                    "name": "Consumer Electronics",
                    "description": "iPhone, iPad, Mac products",
                    "segment_type": "Technology",
                    "strategic_importance": "Core business",
                    "market_position": "Market leader",
                    "growth_outlook": "Positive",
                    "key_competitors": ["Samsung"],
                    "relative_size": "Large",
                    "market_trends": "AI adoption",
                    "product_differentiation": "Ecosystem integration",
                }
            ],
            "geographic_segments": [
                {
                    "name": "Americas",
                    "description": "North and South America",
                    "region": "North America",
                    "strategic_importance": "Primary market",
                    "market_position": "Dominant",
                    "growth_outlook": "Stable",
                    "key_competitors": ["Samsung"],
                    "relative_size": "Large",
                    "market_characteristics": "Mature market",
                    "regulatory_environment": "Favorable",
                    "expansion_strategy": "Service growth",
                }
            ],
            "supply_chain": {
                "description": "Global supply chain",
                "key_suppliers": ["TSMC"],
                "sourcing_strategy": "Diversified",
                "risks": "Geopolitical",
            },
            "partnerships": [
                {
                    "name": "App Store",
                    "description": "Developer ecosystem",
                    "partnership_type": "Platform",
                    "strategic_value": "Revenue sharing",
                }
            ],
        }

        response = create_analysis_response(
            schema_type="BusinessAnalysisSection",
            result=result,
            sub_section_name="Business Analysis",
            processing_time_ms=150,
        )

        assert isinstance(response, AnalysisResponse)
        assert response.sub_section_name == "Business Analysis"
        assert response.schema_type == "BusinessAnalysisSection"
        assert response.processing_time_ms == 150
        assert isinstance(response.analysis, BusinessAnalysisSection)

    def test_create_analysis_response_unknown_schema(self):
        """Test that unknown schema type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown schema type"):
            create_analysis_response(
                schema_type="UnknownSchema",
                result={},
                sub_section_name="Test",
            )

    def test_create_fallback_subsection_response(self):
        """Test creation of fallback response for failed analysis."""
        response = create_fallback_subsection_response(
            subsection_name="operational_overview",
            subsection_schema=MDAAnalysisSection,
            section_name="Item 7 - Management Discussion & Analysis",
            error="API Error",
            processing_time_ms=50,
        )

        assert isinstance(response, SubsectionAnalysisResponse)
        assert response.sub_section_name == "Operational Overview"
        assert response.schema_type == "MDAAnalysisSection"
        assert response.parent_section == "Item 7 - Management Discussion & Analysis"
        assert "Analysis failed: API Error" in response.subsection_focus
        assert response.processing_time_ms == 50
        assert response.analysis == {}


class TestBaseLLMProvider:
    """Test base LLM provider functionality."""

    def test_calculate_sentiment_score_positive(self):
        """Test sentiment calculation for positive text."""
        provider = MockLLMProvider()

        positive_text = "strong growth improvement increase profit revenue up"
        score = provider._calculate_sentiment_score(positive_text)

        assert score > 0
        assert -1 <= score <= 1

    def test_calculate_sentiment_score_negative(self):
        """Test sentiment calculation for negative text."""
        provider = MockLLMProvider()

        negative_text = "decline loss weak decrease challenges risks"
        score = provider._calculate_sentiment_score(negative_text)

        assert score < 0
        assert -1 <= score <= 1

    def test_calculate_sentiment_score_neutral(self):
        """Test sentiment calculation for neutral text."""
        provider = MockLLMProvider()

        neutral_text = "company business operations management report analysis"
        score = provider._calculate_sentiment_score(neutral_text)

        assert score == 0.0

    def test_calculate_sentiment_score_mixed(self):
        """Test sentiment calculation for mixed text."""
        provider = MockLLMProvider()

        mixed_text = "growth opportunities but challenges and risks remain"
        score = provider._calculate_sentiment_score(mixed_text)

        # Should be close to neutral with slight bias
        assert -1 <= score <= 1

    def test_calculate_sentiment_score_short_text_dampening(self):
        """Test that short texts have dampened sentiment scores."""
        provider = MockLLMProvider()

        short_positive = "strong"  # Very short text
        long_positive = "strong " * 50  # Longer text with same sentiment

        short_score = provider._calculate_sentiment_score(short_positive)
        long_score = provider._calculate_sentiment_score(long_positive)

        # Short text should have dampened score
        assert abs(short_score) < abs(long_score)


class MockLLMProvider(BaseLLMProvider):
    """Mock implementation of BaseLLMProvider for testing."""

    async def analyze_filing(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Mock implementation."""
        return ComprehensiveAnalysisResponse(
            filing_summary="Mock summary",
            executive_summary="Mock executive summary",
            key_insights=["Mock insight"],
            financial_highlights=["Mock highlight"],
            risk_factors=["Mock risk"],
            opportunities=["Mock opportunity"],
            confidence_score=0.8,
            section_analyses=[],
            total_sections_analyzed=0,
            total_sub_sections_analyzed=0,
            total_processing_time_ms=100,
            filing_type=filing_type.value,
            company_name=company_name,
            analysis_timestamp="2024-01-01T00:00:00Z",
        )

    async def analyze_section(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Mock implementation."""
        return SectionAnalysisResponse(
            section_name=section_name,
            section_summary="Mock summary",
            consolidated_insights=["Mock insight"],
            overall_sentiment=0.0,
            critical_findings=["Mock finding"],
            sub_sections=[],
            sub_section_count=0,
            processing_time_ms=100,
        )


@pytest.mark.asyncio
async def test_run_concurrent_subsection_analysis():
    """Test concurrent subsection analysis utility."""

    # Mock extract and analyze functions
    async def mock_extract_text(
        section_text, subsection_name, subsection_schema, section_name, company_name
    ):
        return f"Extracted text for {subsection_name}"

    async def mock_analyze_subsection(
        subsection_text,
        subsection_name,
        subsection_schema,
        section_name,
        company_name,
        filing_type,
    ):
        return SubsectionAnalysisResponse(
            sub_section_name=create_human_readable_name(subsection_name),
            schema_type=subsection_schema.__name__,
            analysis={"mock": "analysis"},
            parent_section=section_name,
            subsection_focus="Mock focus",
            processing_time_ms=100,
        )

    # Test data
    subsection_schemas = {
        "operational_overview": MDAAnalysisSection,
        "financial_performance": MDAAnalysisSection,
    }

    results = await run_concurrent_subsection_analysis(
        subsection_schemas=subsection_schemas,
        section_text="Sample section text",
        section_name="Item 7 - Management Discussion & Analysis",
        company_name="Apple Inc.",
        filing_type=FilingType.FORM_10K,
        extract_text_func=mock_extract_text,
        analyze_subsection_func=mock_analyze_subsection,
    )

    assert len(results) == 2
    assert all(isinstance(r, SubsectionAnalysisResponse) for r in results)
    assert results[0].sub_section_name == "Operational Overview"
    assert results[1].sub_section_name == "Financial Performance"
