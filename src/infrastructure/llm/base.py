"""Base abstraction for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from src.domain.value_objects import FilingType
from src.infrastructure.llm import schemas


# Base response model with minimal common fields
class BaseSubSectionAnalysisResponse(BaseModel):
    """Base response model for all schema-specific responses."""

    model_config = {"extra": "forbid"}

    sub_section_name: str = Field(..., description="Semantic name of the sub-section")
    processing_time_ms: int | None = Field(
        None, description="Processing time in milliseconds"
    )
    schema_type: str = Field(..., description="Type of schema used")


# Generic analysis response class
class AnalysisResponse(BaseSubSectionAnalysisResponse):
    """Generic analysis response for any schema type."""

    analysis: BaseModel = Field(..., description="Analysis structured content")

    @classmethod
    def from_schema(
        cls,
        schema_instance: BaseModel,
        sub_section_name: str,
        processing_time_ms: int | None = None,
        **kwargs: Any,
    ) -> "AnalysisResponse":
        """Create response from schema instance.

        Args:
            schema_instance: Validated schema instance
            sub_section_name: Name of the sub-section
            processing_time_ms: Processing time in milliseconds
            **kwargs: Additional response fields

        Returns:
            AnalysisResponse with populated fields
        """
        return cls(
            analysis=schema_instance,
            schema_type=schema_instance.__class__.__name__,
            sub_section_name=sub_section_name,
            processing_time_ms=processing_time_ms,
            **kwargs,
        )


# Schema type mapping for factory pattern
SCHEMA_TYPE_MAP: dict[str, type[BaseModel]] = {
    "BusinessAnalysisSection": schemas.BusinessAnalysisSection,
    "RiskFactorsAnalysisSection": schemas.RiskFactorsAnalysisSection,
    "MDAAnalysisSection": schemas.MDAAnalysisSection,
    "BalanceSheetAnalysisSection": schemas.BalanceSheetAnalysisSection,
    "IncomeStatementAnalysisSection": schemas.IncomeStatementAnalysisSection,
    "CashFlowAnalysisSection": schemas.CashFlowAnalysisSection,
}


def create_analysis_response(
    schema_type: str,
    result: dict[str, Any],
    sub_section_name: str,
    processing_time_ms: int | None = None,
    **kwargs: Any,
) -> AnalysisResponse:
    """Factory function to create analysis response from schema type.

    Args:
        schema_type: Type of schema (e.g., "BusinessAnalysisSection")
        result: Raw analysis result dictionary
        sub_section_name: Name of the sub-section
        processing_time_ms: Processing time in milliseconds
        **kwargs: Additional response fields

    Returns:
        AnalysisResponse with validated schema instance

    Raises:
        ValueError: If schema_type is not recognized
    """
    schema_class = SCHEMA_TYPE_MAP.get(schema_type)
    if not schema_class:
        raise ValueError(f"Unknown schema type: {schema_type}")

    schema_instance = schema_class.model_validate(result)
    return AnalysisResponse.from_schema(
        schema_instance=schema_instance,
        sub_section_name=sub_section_name,
        processing_time_ms=processing_time_ms,
        **kwargs,
    )


class SubsectionAnalysisResponse(BaseSubSectionAnalysisResponse):
    """Generic subsection analysis response for individual schema components."""

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {"additionalProperties": False},
    }

    schema_type: str = Field(..., description="Type of subsection schema")
    analysis: dict[str, Any] = Field(
        ...,
        description="Subsection analysis content",
        json_schema_extra={"additionalProperties": False},
    )
    parent_section: str = Field(..., description="Name of parent section")
    subsection_focus: str = Field(
        ..., description="Specific focus area of this subsection"
    )


# Union type for all possible sub-section response types
SubSectionAnalysisResponse = AnalysisResponse | SubsectionAnalysisResponse


class SectionSummaryResponse(BaseModel):
    """Section summary response without sub-sections (for OpenAI structured output)."""

    model_config = {"extra": "forbid"}

    section_name: str = Field(..., description="Name of the section")
    section_summary: str = Field(
        ..., description="Comprehensive summary of the entire section"
    )
    consolidated_insights: list[str] = Field(
        ..., description="5-7 consolidated insights from all sub-sections"
    )
    overall_sentiment: float = Field(
        ..., ge=-1, le=1, description="Overall sentiment for the section"
    )
    critical_findings: list[str] = Field(
        ..., description="Critical findings that need attention"
    )


class SectionAnalysisResponse(BaseModel):
    """Unified section analysis response combining summary and sub-sections."""

    model_config = {"extra": "forbid"}

    section_name: str = Field(..., description="Name of the section")
    section_summary: str = Field(
        ..., description="Comprehensive summary of the entire section"
    )
    consolidated_insights: list[str] = Field(
        ..., description="5-7 consolidated insights from all sub-sections"
    )
    overall_sentiment: float = Field(
        ..., ge=-1, le=1, description="Overall sentiment for the section"
    )
    critical_findings: list[str] = Field(
        ..., description="Critical findings that need attention"
    )
    sub_sections: list[SubSectionAnalysisResponse] = Field(
        ..., description="Detailed sub-section analyses"
    )
    processing_time_ms: int | None = Field(
        None, description="Processing time in milliseconds"
    )
    sub_section_count: int = Field(..., description="Number of sub-sections analyzed")


class OverallAnalysisResponse(BaseModel):
    """Overall analysis response for internal processing."""

    filing_summary: str = Field(
        ..., description="3-4 sentence summary of entire filing"
    )
    executive_summary: str = Field(..., description="2-3 paragraph executive summary")
    key_insights: list[str] = Field(..., description="7-10 most important insights")
    financial_highlights: list[str] = Field(
        ..., description="Key financial metrics and changes"
    )
    risk_factors: list[str] = Field(..., description="Main risk factors identified")
    opportunities: list[str] = Field(..., description="Growth opportunities mentioned")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Confidence in analysis"
    )


class ComprehensiveAnalysisResponse(BaseModel):
    """Comprehensive filing analysis response for API consumption."""

    # Consolidated overall analysis
    filing_summary: str = Field(
        ..., description="3-4 sentence summary of entire filing"
    )
    executive_summary: str = Field(..., description="2-3 paragraph executive summary")
    key_insights: list[str] = Field(..., description="7-10 most important insights")
    financial_highlights: list[str] = Field(
        ..., description="Key financial metrics and changes"
    )
    risk_factors: list[str] = Field(..., description="Main risk factors identified")
    opportunities: list[str] = Field(..., description="Growth opportunities mentioned")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Confidence in analysis"
    )

    # Section-specific analyses aggregated with sub-sections
    section_analyses: list[SectionAnalysisResponse] = Field(
        ..., description="Detailed section analyses"
    )

    # API-friendly metadata
    total_sections_analyzed: int = Field(
        ..., description="Total number of sections analyzed"
    )
    total_sub_sections_analyzed: int = Field(
        ..., description="Total number of sub-sections analyzed"
    )
    total_processing_time_ms: int | None = Field(
        None, description="Total processing time in milliseconds"
    )
    filing_type: str = Field(..., description="Type of SEC filing")
    company_name: str = Field(..., description="Name of the company")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def analyze_filing(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Analyze complete SEC filing using hierarchical analysis.

        This orchestrates the full analysis workflow:
        1. Analyze each section concurrently (which internally handles sub-sections)
        2. Generate overall analysis from all section results

        Args:
            filing_sections: Dictionary of section_name -> section_text
            filing_type: Type of SEC filing
            company_name: Name of the company
            analysis_focus: Optional list of focus areas

        Returns:
            Complete analysis result
        """
        pass

    @abstractmethod
    async def analyze_section(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Analyze a complete section using semantic sub-section analysis.

        The LLM will:
        1. Identify semantic sub-sections (e.g., 'geographic distribution', 'business segments')
        2. Analyze each sub-section concurrently
        3. Generate consolidated section summary

        Args:
            section_text: Full text content of the section
            section_name: Name of the section
            filing_type: Type of SEC filing
            company_name: Name of the company

        Returns:
            Complete section analysis with sub-section breakdown
        """
        pass

    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score from text using financial-specific keywords.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score between -1 and 1
        """
        # Enhanced financial-specific sentiment keywords
        positive_indicators = [
            "growth",
            "increase",
            "improvement",
            "strong",
            "positive",
            "exceed",
            "outperform",
            "expansion",
            "gain",
            "profit",
            "revenue up",
            "margin improvement",
            "record high",
            "robust",
            "resilient",
            "solid",
            "healthy",
            "successful",
            "optimistic",
            "confidence",
            "opportunities",
            "competitive advantage",
            "market leader",
            "innovation",
            "efficiency",
            "returns",
            "dividend",
            "cash flow",
            "earnings",
            "beat expectations",
            "guidance raised",
            "market share",
            "demand",
            "favorable",
            "momentum",
            "strategic",
            "breakthrough",
            "leadership",
            "performance",
            "value creation",
        ]

        negative_indicators = [
            "decline",
            "decrease",
            "loss",
            "weak",
            "negative",
            "below",
            "underperform",
            "contraction",
            "impairment",
            "revenue down",
            "margin pressure",
            "restructuring",
            "challenges",
            "headwinds",
            "volatile",
            "uncertainty",
            "concerns",
            "risks",
            "difficulties",
            "pressure",
            "slowdown",
            "disruption",
            "competition",
            "regulatory",
            "litigation",
            "default",
            "bankruptcy",
            "layoffs",
            "closure",
            "downturn",
            "recession",
            "deterioration",
            "warning",
            "miss expectations",
            "guidance lowered",
            "market decline",
            "debt",
            "unfavorable",
            "struggling",
            "crisis",
        ]

        # Neutral indicators that should not affect sentiment (unused in current implementation)
        # neutral_indicators = [
        #     "analysis", "discussion", "overview", "summary", "report", "filing",
        #     "section", "item", "management", "company", "business", "operations",
        #     "financial", "statements", "period", "quarter", "year", "fiscal",
        # ]

        text_lower = text.lower()

        # Count occurrences with weighted scoring
        positive_count = 0.0
        negative_count = 0.0

        for phrase in positive_indicators:
            count = text_lower.count(phrase)
            # Weight shorter, more specific phrases higher
            weight = 1.0 if len(phrase.split()) > 1 else 0.7
            positive_count += count * weight

        for phrase in negative_indicators:
            count = text_lower.count(phrase)
            # Weight shorter, more specific phrases higher
            weight = 1.0 if len(phrase.split()) > 1 else 0.7
            negative_count += count * weight

        # If no sentiment indicators found, return neutral
        if positive_count + negative_count == 0:
            return 0.0

        # Calculate normalized score
        score = (positive_count - negative_count) / (positive_count + negative_count)

        # Apply dampening for very short texts (less reliable)
        if len(text) < 100:
            score *= 0.5

        return round(score, 3)
