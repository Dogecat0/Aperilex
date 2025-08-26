"""Comprehensive tests for Base LLM Provider utilities and models."""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.domain.value_objects import FilingType
from src.infrastructure.llm.base import (
    SCHEMA_TYPE_MAP,
    SUBSECTION_NAME_MAP,
    AnalysisResponse,
    BaseLLMProvider,
    BaseSubSectionAnalysisResponse,
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
    SectionSummaryResponse,
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
from src.infrastructure.llm.schemas.business import OperationalOverview


@pytest.mark.unit
class TestBaseModels:
    """Test Base LLM Provider models and validation."""

    def test_base_subsection_analysis_response_validation(self):
        """Test BaseSubSectionAnalysisResponse model validation."""
        # Arrange
        valid_data = {
            "sub_section_name": "Business Overview",
            "processing_time_ms": 1500,
            "schema_type": "BusinessAnalysisSection",
        }

        # Act
        response = BaseSubSectionAnalysisResponse(**valid_data)

        # Assert
        assert response.sub_section_name == "Business Overview"
        assert response.processing_time_ms == 1500
        assert response.schema_type == "BusinessAnalysisSection"

    def test_base_subsection_analysis_response_optional_processing_time(self):
        """Test that processing_time_ms is optional."""
        # Arrange
        data = {
            "sub_section_name": "Risk Assessment",
            "schema_type": "RiskFactorsAnalysisSection",
        }

        # Act
        response = BaseSubSectionAnalysisResponse(**data)

        # Assert
        assert response.sub_section_name == "Risk Assessment"
        assert response.processing_time_ms is None
        assert response.schema_type == "RiskFactorsAnalysisSection"

    def test_analysis_response_from_schema(self):
        """Test AnalysisResponse.from_schema class method."""
        # Arrange
        schema_instance = OperationalOverview(
            description="Test business operations",
            industry_classification="Technology",
            primary_markets=["Software"],  # Using correct enum value
            target_customers="Enterprise clients",
            business_model="SaaS platform",
        )

        # Act
        response = AnalysisResponse.from_schema(
            schema_instance=schema_instance,
            sub_section_name="Operations",
            processing_time_ms=800,
        )

        # Assert
        assert response.sub_section_name == "Operations"
        assert response.processing_time_ms == 800
        assert response.schema_type == "OperationalOverview"
        assert response.analysis == schema_instance

    def test_subsection_analysis_response_validation(self):
        """Test SubsectionAnalysisResponse model validation."""
        # Arrange
        data = {
            "sub_section_name": "Financial Performance",
            "processing_time_ms": 1200,
            "schema_type": "MDAAnalysisSection",
            "analysis": {"revenue": "Strong growth", "margins": "Improved"},
            "parent_section": "Item 7 - Management Discussion & Analysis",
            "subsection_focus": "Financial metrics analysis",
        }

        # Act
        response = SubsectionAnalysisResponse(**data)

        # Assert
        assert response.sub_section_name == "Financial Performance"
        assert response.analysis == {"revenue": "Strong growth", "margins": "Improved"}
        assert response.parent_section == "Item 7 - Management Discussion & Analysis"
        assert response.subsection_focus == "Financial metrics analysis"

    def test_section_summary_response_sentiment_validation(self):
        """Test SectionSummaryResponse sentiment score validation."""
        # Valid sentiment scores
        valid_data = {
            "section_name": "Item 1 - Business",
            "section_summary": "Strong business position",
            "consolidated_insights": ["Market leadership", "Growth potential"],
            "overall_sentiment": 0.7,
            "critical_findings": ["Key strength identified"],
        }

        response = SectionSummaryResponse(**valid_data)
        assert response.overall_sentiment == 0.7

        # Test sentiment bounds
        with pytest.raises(ValidationError):
            invalid_data = valid_data.copy()
            invalid_data["overall_sentiment"] = 1.5  # Above max
            SectionSummaryResponse(**invalid_data)

        with pytest.raises(ValidationError):
            invalid_data = valid_data.copy()
            invalid_data["overall_sentiment"] = -1.5  # Below min
            SectionSummaryResponse(**invalid_data)

    def test_comprehensive_analysis_response_confidence_validation(self):
        """Test ComprehensiveAnalysisResponse confidence score validation."""
        # Base valid data
        base_data = {
            "filing_summary": "Test summary",
            "executive_summary": "Executive overview",
            "key_insights": ["Insight 1", "Insight 2"],
            "financial_highlights": ["Revenue growth"],
            "risk_factors": ["Market risk"],
            "opportunities": ["Expansion"],
            "confidence_score": 0.8,
            "section_analyses": [],
            "total_sections_analyzed": 0,
            "total_sub_sections_analyzed": 0,
            "total_processing_time_ms": 1000,
            "filing_type": "10-K",
            "company_name": "Test Corp",
            "analysis_timestamp": "2023-01-01T12:00:00Z",
        }

        # Valid confidence score
        response = ComprehensiveAnalysisResponse(**base_data)
        assert response.confidence_score == 0.8

        # Invalid confidence scores
        with pytest.raises(ValidationError):
            invalid_data = base_data.copy()
            invalid_data["confidence_score"] = 1.1  # Above max
            ComprehensiveAnalysisResponse(**invalid_data)

        with pytest.raises(ValidationError):
            invalid_data = base_data.copy()
            invalid_data["confidence_score"] = -0.1  # Below min
            ComprehensiveAnalysisResponse(**invalid_data)


@pytest.mark.unit
class TestBaseLLMProvider:
    """Test BaseLLMProvider abstract methods."""

    def test_base_llm_provider_is_abstract(self):
        """Test that BaseLLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider()

    def test_base_llm_provider_sentiment_calculation(self):
        """Test _calculate_sentiment_score method."""

        # Create a concrete implementation for testing
        class TestProvider(BaseLLMProvider):
            async def analyze_filing(
                self, filing_sections, filing_type, company_name, analysis_focus=None
            ):
                pass

            async def analyze_section(
                self, section_text, section_name, filing_type, company_name
            ):
                pass

        provider = TestProvider()

        # Test positive sentiment
        positive_text = (
            "strong growth, increased revenue, improved margins, excellent performance"
        )
        positive_score = provider._calculate_sentiment_score(positive_text)
        assert positive_score > 0

        # Test negative sentiment
        negative_text = (
            "significant decline, decreased revenue, major losses, poor performance"
        )
        negative_score = provider._calculate_sentiment_score(negative_text)
        assert negative_score < 0

        # Test neutral sentiment (no keywords)
        neutral_text = (
            "the company operates in various markets with standard procedures"
        )
        neutral_score = provider._calculate_sentiment_score(neutral_text)
        assert neutral_score == 0.0

        # Test mixed sentiment (should balance out)
        mixed_text = "strong growth but facing challenges and increased competition"
        mixed_score = provider._calculate_sentiment_score(mixed_text)
        assert -1.0 <= mixed_score <= 1.0

    def test_sentiment_score_dampening_short_text(self):
        """Test that short texts have dampened sentiment scores."""

        class TestProvider(BaseLLMProvider):
            async def analyze_filing(
                self, filing_sections, filing_type, company_name, analysis_focus=None
            ):
                pass

            async def analyze_section(
                self, section_text, section_name, filing_type, company_name
            ):
                pass

        provider = TestProvider()

        # Short positive text (less than 100 characters)
        short_text = "excellent growth"  # 16 characters
        short_score = provider._calculate_sentiment_score(short_text)

        # Longer positive text
        long_text = "excellent growth " * 10  # More than 100 characters
        long_score = provider._calculate_sentiment_score(long_text)

        # Short text should have dampened score
        assert abs(short_score) < abs(long_score)


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions in base module."""

    def test_create_analysis_response_valid_schema(self):
        """Test create_analysis_response with valid schema type."""
        # Arrange - Create a complete BusinessAnalysisSection structure with required items
        result = {
            "operational_overview": {
                "description": "Test operations",
                "industry_classification": "Technology",
                "primary_markets": ["Software"],
                "target_customers": "Enterprise",
                "business_model": "SaaS",
            },
            "key_products": [
                {
                    "name": "Test Product",
                    "description": "Test description",
                    "significance": "Test significance",
                }
            ],
            "competitive_advantages": [
                {
                    "advantage": "Test advantage",
                    "description": "Test description",
                    "competitors": ["Competitor"],
                    "sustainability": "Test sustainability",
                }
            ],
            "strategic_initiatives": [
                {
                    "name": "Test initiative",
                    "description": "Test description",
                    "impact": "Test impact",
                    "timeframe": "Test timeframe",
                    "resource_allocation": "Test resources",
                }
            ],
            "business_segments": [
                {
                    "name": "Test segment",
                    "description": "Test description",
                    "strategic_importance": "Test importance",
                    "segment_type": "Technology",
                    "market_position": "Test position",
                    "growth_outlook": "Test outlook",
                    "key_competitors": ["Competitor"],
                    "relative_size": "Test size",
                    "market_trends": "Test trends",
                    "product_differentiation": "Test differentiation",
                }
            ],
            "geographic_segments": [
                {
                    "name": "Test region",
                    "description": "Test description",
                    "strategic_importance": "Test importance",
                    "region": "North America",
                    "market_position": "Test position",
                    "growth_outlook": "Test outlook",
                    "key_competitors": ["Competitor"],
                    "relative_size": "Test size",
                    "market_characteristics": "Test characteristics",
                    "regulatory_environment": "Test environment",
                    "expansion_strategy": "Test strategy",
                }
            ],
            "supply_chain": {
                "description": "Test supply chain",
                "key_suppliers": ["Supplier"],
                "sourcing_strategy": "Strategic",
                "risks": "Minimal",
            },
            "partnerships": [
                {
                    "name": "Test partnership",
                    "description": "Test description",
                    "partnership_type": "Strategic",
                    "strategic_value": "Test value",
                }
            ],
        }

        # Act
        response = create_analysis_response(
            schema_type="BusinessAnalysisSection",
            result=result,
            sub_section_name="Business Operations",
            processing_time_ms=1000,
        )

        # Assert
        assert isinstance(response, AnalysisResponse)
        assert response.sub_section_name == "Business Operations"
        assert response.processing_time_ms == 1000
        assert response.schema_type == "BusinessAnalysisSection"

    def test_create_analysis_response_invalid_schema(self):
        """Test create_analysis_response with invalid schema type."""
        with pytest.raises(ValueError, match="Unknown schema type"):
            create_analysis_response(
                schema_type="NonExistentSchema", result={}, sub_section_name="Test"
            )

    def test_extract_subsection_schemas(self):
        """Test extract_subsection_schemas function."""
        from src.infrastructure.llm.schemas.business import BusinessAnalysisSection

        # Act
        subsections = extract_subsection_schemas(BusinessAnalysisSection)

        # Assert
        assert isinstance(subsections, dict)
        assert len(subsections) > 0
        # Should include operational_overview and other business subsections
        assert "operational_overview" in subsections
        # All values should be BaseModel subclasses
        for schema_class in subsections.values():
            assert issubclass(schema_class, BaseModel)

    def test_extract_subsection_schemas_no_subsections(self):
        """Test extract_subsection_schemas with schema that has no subsections."""

        # Create a simple schema with no BaseModel fields
        class SimpleSchema(BaseModel):
            title: str = Field(..., description="Simple title")
            count: int = Field(..., description="Simple count")

        # Act
        subsections = extract_subsection_schemas(SimpleSchema)

        # Assert
        assert isinstance(subsections, dict)
        assert len(subsections) == 0

    def test_create_human_readable_name(self):
        """Test create_human_readable_name function."""
        # Test underscore conversion
        assert (
            create_human_readable_name("operational_overview") == "Operational Overview"
        )
        assert create_human_readable_name("key_products") == "Key Products"
        assert create_human_readable_name("business_segments") == "Business Segments"

        # Test already readable names
        assert create_human_readable_name("overview") == "Overview"
        assert create_human_readable_name("analysis") == "Analysis"

    def test_create_extraction_prompt(self):
        """Test create_extraction_prompt function."""
        # Act
        prompt = create_extraction_prompt(
            section_name="Item 1 - Business",
            subsection_name="operational_overview",
            section_text="Full business section text here...",
            subsection_schema=OperationalOverview,
        )

        # Assert
        assert isinstance(prompt, str)
        assert "Item 1 - Business" in prompt
        assert "operational_overview" in prompt
        assert "Full business section text here..." in prompt
        assert "Extract" in prompt

    def test_create_analysis_prompt(self):
        """Test create_analysis_prompt function."""
        # Act
        prompt = create_analysis_prompt(
            human_readable_name="Operational Overview",
            company_name="Apple Inc.",
            filing_type=FilingType.FORM_10K,
            section_name="Item 1 - Business",
            subsection_text="Operational text content...",
        )

        # Assert
        assert isinstance(prompt, str)
        assert "Apple Inc." in prompt
        assert "10-K" in prompt
        assert "Item 1 - Business" in prompt
        assert "Operational Overview" in prompt
        assert "Operational text content..." in prompt

    def test_create_section_analysis_prompt(self):
        """Test create_section_analysis_prompt function."""
        # Act
        prompt = create_section_analysis_prompt(
            section_name="Item 1A - Risk Factors",
            company_name="Microsoft Corp",
            filing_type=FilingType.FORM_10Q,
            section_text="Risk factors content...",
        )

        # Assert
        assert isinstance(prompt, str)
        assert "Item 1A - Risk Factors" in prompt
        assert "Microsoft Corp" in prompt
        assert "10-Q" in prompt
        assert "Risk factors content..." in prompt

    def test_create_fallback_subsection_response(self):
        """Test create_fallback_subsection_response function."""
        # Act
        response = create_fallback_subsection_response(
            subsection_name="operational_overview",
            subsection_schema=OperationalOverview,
            section_name="Item 1 - Business",
            error="API connection failed",
            processing_time_ms=500,
        )

        # Assert
        assert isinstance(response, SubsectionAnalysisResponse)
        assert response.sub_section_name == "Operational Overview"
        assert response.schema_type == "OperationalOverview"
        assert response.parent_section == "Item 1 - Business"
        assert "API connection failed" in response.subsection_focus
        assert response.processing_time_ms == 500
        assert response.analysis == {}

    def test_create_section_summary_prompts(self):
        """Test create_section_summary_prompts function."""
        # Arrange
        mock_subsections = [
            SubsectionAnalysisResponse(
                sub_section_name="Operations",
                processing_time_ms=800,
                schema_type="OperationalOverview",
                analysis={"description": "test"},
                parent_section="Item 1 - Business",
                subsection_focus="Operations focus",
            )
        ]

        # Act
        system_prompt, user_prompt = create_section_summary_prompts(
            sub_sections=mock_subsections,
            section_name="Item 1 - Business",
            filing_type=FilingType.FORM_10K,
            company_name="Tesla Inc.",
        )

        # Assert
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert "financial analyst" in system_prompt.lower()
        assert "Tesla Inc." in user_prompt
        assert "Item 1 - Business" in user_prompt
        assert "10-K" in user_prompt

    def test_create_overall_analysis_prompts(self):
        """Test create_overall_analysis_prompts function."""
        # Arrange
        mock_section_analyses = [
            Mock(spec=SectionAnalysisResponse),
            Mock(spec=SectionAnalysisResponse),
        ]
        mock_section_analyses[0].section_name = "Item 1 - Business"
        mock_section_analyses[0].section_summary = "Strong business overview"
        mock_section_analyses[1].section_name = "Item 1A - Risk Factors"
        mock_section_analyses[1].section_summary = "Manageable risk profile"

        # Act without focus areas
        system_prompt, user_prompt = create_overall_analysis_prompts(
            section_analyses=mock_section_analyses,
            filing_type=FilingType.FORM_10K,
            company_name="Amazon Inc.",
            analysis_focus=None,
        )

        # Assert
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert "senior financial analyst" in system_prompt.lower()
        assert "Amazon Inc." in user_prompt
        assert "10-K" in user_prompt
        assert "Strong business overview" in user_prompt
        assert "Manageable risk profile" in user_prompt

    def test_create_overall_analysis_prompts_with_focus(self):
        """Test create_overall_analysis_prompts with focus areas."""
        # Arrange
        mock_section_analyses = [Mock(spec=SectionAnalysisResponse)]
        mock_section_analyses[0].section_name = "Item 1 - Business"
        mock_section_analyses[0].section_summary = "Business summary"

        # Act with focus areas
        system_prompt, user_prompt = create_overall_analysis_prompts(
            section_analyses=mock_section_analyses,
            filing_type=FilingType.FORM_10Q,
            company_name="Google Inc.",
            analysis_focus=["financial_performance", "risk_assessment"],
        )

        # Assert
        assert "Focus areas: financial_performance, risk_assessment" in user_prompt
        assert "Google Inc." in user_prompt
        assert "10-Q" in user_prompt


@pytest.mark.unit
class TestConstants:
    """Test constants and mappings."""

    def test_schema_type_map_completeness(self):
        """Test that SCHEMA_TYPE_MAP contains expected schemas."""
        expected_keys = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]

        for key in expected_keys:
            assert key in SCHEMA_TYPE_MAP
            # Each value should be a BaseModel subclass
            assert issubclass(SCHEMA_TYPE_MAP[key], BaseModel)

    def test_subsection_name_map_completeness(self):
        """Test that SUBSECTION_NAME_MAP contains expected mappings."""
        expected_mappings = {
            "BusinessAnalysisSection": "Business Analysis",
            "RiskFactorsAnalysisSection": "Risk Assessment",
            "MDAAnalysisSection": "Management Discussion",
            "BalanceSheetAnalysisSection": "Balance Sheet Review",
            "IncomeStatementAnalysisSection": "Income Statement Review",
            "CashFlowAnalysisSection": "Cash Flow Review",
        }

        for schema_type, expected_name in expected_mappings.items():
            assert schema_type in SUBSECTION_NAME_MAP
            assert SUBSECTION_NAME_MAP[schema_type] == expected_name


@pytest.mark.unit
class TestConcurrentAnalysis:
    """Test concurrent subsection analysis utilities."""

    @pytest.mark.asyncio
    async def test_run_concurrent_subsection_analysis_success(self):
        """Test successful concurrent subsection analysis."""
        # Arrange
        mock_subsection_schemas = {
            "operational_overview": OperationalOverview,
            "key_products": Mock(),
        }

        async def mock_extract_text(*args, **kwargs):
            return "Extracted text for analysis"

        async def mock_analyze_subsection(*args, **kwargs):
            # args order: subsection_text, subsection_name, subsection_schema, section_name, company_name, filing_type
            return SubsectionAnalysisResponse(
                sub_section_name=args[1].replace("_", " ").title(),
                processing_time_ms=800,
                schema_type=args[2].__name__,
                analysis={"test": "data"},
                parent_section="Item 1 - Business",
                subsection_focus="Test focus",
            )

        # Act
        results = await run_concurrent_subsection_analysis(
            subsection_schemas=mock_subsection_schemas,
            section_text="Section text content",
            section_name="Item 1 - Business",
            company_name="Test Company",
            filing_type=FilingType.FORM_10K,
            extract_text_func=mock_extract_text,
            analyze_subsection_func=mock_analyze_subsection,
        )

        # Assert - Only the valid schemas should return results
        assert len(results) >= 1  # At least the operational_overview should work
        assert all(isinstance(r, SubsectionAnalysisResponse) for r in results)
        assert any(r.sub_section_name == "Operational Overview" for r in results)

    @pytest.mark.asyncio
    async def test_run_concurrent_subsection_analysis_with_failures(self):
        """Test concurrent analysis with some failures."""
        # Arrange
        mock_subsection_schemas = {"success_section": Mock(), "failure_section": Mock()}

        async def mock_extract_text(*args, **kwargs):
            return "Extracted text"

        async def mock_analyze_subsection(*args, **kwargs):
            # args order: subsection_text, subsection_name, subsection_schema, section_name, company_name, filing_type
            if "failure" in args[1]:
                raise Exception("Analysis failed")
            return SubsectionAnalysisResponse(
                sub_section_name="Success Section",
                processing_time_ms=500,
                schema_type="TestSchema",
                analysis={"result": "success"},
                parent_section="Test Section",
                subsection_focus="Success focus",
            )

        # Act
        results = await run_concurrent_subsection_analysis(
            subsection_schemas=mock_subsection_schemas,
            section_text="Section text",
            section_name="Test Section",
            company_name="Test Co",
            filing_type=FilingType.FORM_10K,
            extract_text_func=mock_extract_text,
            analyze_subsection_func=mock_analyze_subsection,
        )

        # Assert - Should have at least one result (the success case)
        assert len(results) >= 1
        success_results = [
            r for r in results if "Success Section" in r.sub_section_name
        ]
        assert len(success_results) >= 1  # At least the success case should work

    @pytest.mark.asyncio
    async def test_run_concurrent_subsection_analysis_empty_schemas(self):
        """Test concurrent analysis with empty subsection schemas."""
        # Act
        results = await run_concurrent_subsection_analysis(
            subsection_schemas={},
            section_text="Section text",
            section_name="Test Section",
            company_name="Test Co",
            filing_type=FilingType.FORM_10K,
            extract_text_func=Mock(),
            analyze_subsection_func=Mock(),
        )

        # Assert
        assert results == []
