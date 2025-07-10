"""Base abstraction for LLM providers."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.domain.value_objects import FilingType


# Simplified unified response models for API consumption
class SubSectionAnalysisResponse(BaseModel):
    """Unified sub-section analysis response."""

    sub_section_name: str = Field(..., description="Semantic name of the sub-section")
    summary: str = Field(..., description="2-3 sentence summary of the sub-section")
    key_points: list[str] = Field(
        ..., description="3-5 key points from the sub-section"
    )
    sentiment_score: float = Field(
        ..., ge=-1, le=1, description="Sentiment score from -1 to 1"
    )
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Relevance score from 0 to 1"
    )
    notable_metrics: list[str] = Field(
        default_factory=list, description="Important metrics mentioned"
    )
    concerns: list[str] = Field(
        default_factory=list, description="Any concerns or risks identified"
    )
    opportunities: list[str] = Field(
        default_factory=list, description="Growth opportunities mentioned"
    )
    processing_time_ms: int | None = Field(
        None, description="Processing time in milliseconds"
    )


class SectionAnalysisResponse(BaseModel):
    """Unified section analysis response combining summary and sub-sections."""

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


# Result dataclasses
class SubSectionAnalysis(BaseModel):
    """Analysis result for a semantic sub-section of filing."""

    sub_section_name: (
        str  # Semantic name like 'Geographic Distribution', 'Product Lines'
    )
    summary: str
    key_points: list[str]
    sentiment_score: Decimal
    relevance_score: Decimal
    notable_metrics: list[str]
    concerns: list[str]


class SectionAnalysis(BaseModel):
    """Analysis result for a complete section."""

    section_name: str
    section_summary: str
    consolidated_insights: list[str]
    overall_sentiment: Decimal
    critical_findings: list[str]
    sub_sections: list[SubSectionAnalysis]


class AnalysisResult(BaseModel):
    """Complete analysis result from SEC filing."""

    filing_summary: str
    executive_summary: str
    key_insights: list[str]
    financial_highlights: list[str]
    risk_factors: list[str]
    opportunities: list[str]
    sentiment_score: Decimal
    confidence_score: Decimal
    section_analyses: list[SectionAnalysis]
    metadata: dict[str, Any]


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

    @abstractmethod
    async def analyze_sub_section(
        self,
        sub_section_text: str,
        sub_section_name: str,
        parent_section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SubSectionAnalysisResponse:
        """Analyze a single semantic sub-section (single LLM call).

        Args:
            sub_section_text: Text content of the semantic sub-section
            sub_section_name: Semantic name (e.g., 'Geographic Distribution', 'Product Lines')
            parent_section_name: Name of the parent section
            filing_type: Type of SEC filing
            company_name: Name of the company

        Returns:
            Sub-section analysis result
        """
        pass

    def _calculate_sentiment_score(self, text: str) -> Decimal:
        """Calculate sentiment score from text.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score between -1 and 1
        """
        # Financial-specific sentiment keywords
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
        ]

        text_lower = text.lower()
        positive_count = sum(
            1 for phrase in positive_indicators if phrase in text_lower
        )
        negative_count = sum(
            1 for phrase in negative_indicators if phrase in text_lower
        )

        if positive_count + negative_count == 0:
            return Decimal("0.0")

        score = (positive_count - negative_count) / (positive_count + negative_count)
        return Decimal(str(round(score, 3)))
