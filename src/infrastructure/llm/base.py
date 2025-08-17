"""Base abstraction for LLM providers."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, Field
from pydantic import BaseModel as PydanticBaseModel

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
        ...,
        description="Key financial metrics with actual numbers/percentages from filing (e.g., 'Revenue grew 15% to $45.3B'). Use descriptive statements if specific numbers unavailable, never placeholder variables.",
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
        ...,
        description="Key financial metrics with actual numbers/percentages from filing (e.g., 'Revenue grew 15% to $45.3B'). Use descriptive statements if specific numbers unavailable, never placeholder variables.",
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


# Common constants and mappings for all providers
SECTION_SCHEMAS = {
    # 10-K sections
    "Item 1 - Business": schemas.BusinessAnalysisSection,
    "Item 1A - Risk Factors": schemas.RiskFactorsAnalysisSection,
    "Item 7 - Management Discussion & Analysis": schemas.MDAAnalysisSection,
    # 10-Q sections - Part I
    "Part I Item 2 - Management Discussion & Analysis": schemas.MDAAnalysisSection,
    # 10-Q sections - Part II
    "Part II Item 1A - Risk Factors": schemas.RiskFactorsAnalysisSection,
    # Financial statement schemas
    "Balance Sheet": schemas.BalanceSheetAnalysisSection,
    "Income Statement": schemas.IncomeStatementAnalysisSection,
    "Cash Flow Statement": schemas.CashFlowAnalysisSection,
}

SUBSECTION_NAME_MAP = {
    "BusinessAnalysisSection": "Business Analysis",
    "RiskFactorsAnalysisSection": "Risk Assessment",
    "MDAAnalysisSection": "Management Discussion",
    "BalanceSheetAnalysisSection": "Balance Sheet Review",
    "IncomeStatementAnalysisSection": "Income Statement Review",
    "CashFlowAnalysisSection": "Cash Flow Review",
}


def extract_subsection_schemas(
    schema_class: type[PydanticBaseModel],
) -> dict[str, type[PydanticBaseModel]]:
    """Extract subsection schemas from a main section schema.

    This method introspects the schema to identify all subsection fields that are
    themselves Pydantic models, enabling targeted analysis of each subsection.

    Args:
        schema_class: The main section schema class

    Returns:
        Dictionary mapping field names to their schema types
    """
    from enum import Enum

    subsections: dict[Any, Any] = {}

    for field_name, field_info in schema_class.model_fields.items():
        field_type = field_info.annotation

        # Handle Optional types (Union[Type, None])
        if get_origin(field_type) is Union:
            args = get_args(field_type)
            field_type = (
                args[0] if len(args) == 2 and type(None) in args else field_type
            )

        # Handle List types
        if get_origin(field_type) is list:
            field_type = get_args(field_type)[0]

        # Check if it's a BaseModel subclass (but not an Enum)
        try:
            if (
                isinstance(field_type, type)
                and issubclass(field_type, PydanticBaseModel)
                and not issubclass(field_type, Enum)
            ):
                subsections[field_name] = field_type
        except TypeError:
            # Handle cases where field_type might not be a proper type
            pass

    return subsections


def create_human_readable_name(subsection_name: str) -> str:
    """Convert underscore-separated name to human-readable title case."""
    return subsection_name.replace("_", " ").title()


def create_extraction_prompt(
    section_name: str,
    subsection_name: str,
    section_text: str,
    subsection_schema: type[PydanticBaseModel],
) -> str:
    """Create standardized prompt for text extraction."""
    field_descriptions = [
        f"{field}: {info.description or 'No description'}"
        for field, info in subsection_schema.model_fields.items()
    ]

    return f"""Extract the most relevant text from the following {section_name} section for analyzing the "{subsection_name}" subsection.

The {subsection_name} subsection should focus on these aspects:
{chr(10).join(field_descriptions)}

Full Section Text:
{section_text}

Extract only the text segments that are directly relevant to the {subsection_name} analysis. Include context but avoid unrelated content. If no directly relevant text is found, return the most contextually appropriate portions.

Return the extracted text without any additional commentary or formatting."""


def create_analysis_prompt(
    human_readable_name: str,
    company_name: str,
    filing_type: FilingType,
    section_name: str,
    subsection_text: str,
) -> str:
    """Create standardized prompt for subsection analysis."""
    return f"""Analyze the {human_readable_name} from {company_name}'s {filing_type.value} filing's {section_name} section.

Text:
{subsection_text}

Focus specifically on the {human_readable_name} aspects and provide a detailed analysis using the structured schema provided."""


def create_section_analysis_prompt(
    section_name: str,
    company_name: str,
    filing_type: FilingType,
    section_text: str,
) -> str:
    """Create standardized prompt for section analysis."""
    return f"""Analyze the {section_name} section from {company_name}'s {filing_type.value} filing.

Text:
{section_text}

Use the structured schema to guide your analysis and ensure comprehensive coverage of all relevant aspects."""


def create_fallback_subsection_response(
    subsection_name: str,
    subsection_schema: type[PydanticBaseModel],
    section_name: str,
    error: str,
    processing_time_ms: int = 0,
) -> SubsectionAnalysisResponse:
    """Create a fallback response for failed subsection analysis."""
    human_readable_name = create_human_readable_name(subsection_name)
    return SubsectionAnalysisResponse(
        sub_section_name=human_readable_name,
        processing_time_ms=processing_time_ms,
        schema_type=subsection_schema.__name__,
        analysis={},
        parent_section=section_name,
        subsection_focus=f"Analysis failed: {error}",
    )


async def run_concurrent_subsection_analysis(
    subsection_schemas: dict[str, type],
    section_text: str,
    section_name: str,
    company_name: str,
    filing_type: FilingType,
    extract_text_func: Callable[..., Any],
    analyze_subsection_func: Callable[..., Any],
) -> list[SubsectionAnalysisResponse]:
    """Run concurrent analysis of all subsections in a section.

    This function encapsulates the common pattern of:
    1. Creating concurrent tasks for each subsection
    2. Running text extraction and analysis for each
    3. Handling exceptions and creating fallback responses
    4. Filtering valid responses

    Args:
        subsection_schemas: Dict mapping subsection names to their schema types
        section_text: Full text of the parent section
        section_name: Name of the parent section
        company_name: Company name for context
        filing_type: Type of SEC filing
        extract_text_func: Function to extract text for a subsection
        analyze_subsection_func: Function to analyze a subsection

    Returns:
        List of valid SubsectionAnalysisResponse objects
    """

    async def analyze_subsection_task(
        subsection_name: str, subsection_schema: type
    ) -> SubsectionAnalysisResponse:
        """Concurrent task for analyzing a single subsection."""
        try:
            # Extract relevant text for this subsection
            subsection_text = await extract_text_func(
                section_text,
                subsection_name,
                subsection_schema,
                section_name,
                company_name,
            )

            # Analyze the subsection with its specific schema
            result = await analyze_subsection_func(
                subsection_text,
                subsection_name,
                subsection_schema,
                section_name,
                company_name,
                filing_type,
            )
            return result  # type: ignore[no-any-return]
        except Exception as e:
            return create_fallback_subsection_response(
                subsection_name, subsection_schema, section_name, str(e)
            )

    # Run all subsection analyses concurrently
    tasks = [
        analyze_subsection_task(subsection_name, subsection_schema)
        for subsection_name, subsection_schema in subsection_schemas.items()
    ]

    # Execute all tasks concurrently
    subsection_responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any failed responses and return valid ones
    valid_responses: list[SubsectionAnalysisResponse] = []
    for response in subsection_responses:
        if isinstance(response, SubsectionAnalysisResponse):
            valid_responses.append(response)

    return valid_responses


def create_section_summary_prompts(
    sub_sections: list[SubsectionAnalysisResponse],
    section_name: str,
    filing_type: FilingType,
    company_name: str,
) -> tuple[str, str]:
    """Create standardized prompts for section summary generation.

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    sub_sections_summary = "\n".join(
        [
            f"- {sub.sub_section_name}: {sub.schema_type} analysis completed"
            for sub in sub_sections
        ]
    )

    system_prompt = "You are a financial analyst. Provide a consolidated summary of the section based on sub-section analyses."

    user_prompt = (
        f"Based on the following sub-section analyses for the {section_name} section of {company_name}'s {filing_type.value} filing, provide a comprehensive section summary.\n\n"
        f"        Sub-section Summaries:\n"
        f"        {sub_sections_summary}\n\n"
        f"        Consolidate the insights and provide an overall assessment of this section."
    )

    return system_prompt, user_prompt


def create_overall_analysis_prompts(
    section_analyses: list[SectionAnalysisResponse],
    filing_type: FilingType,
    company_name: str,
    analysis_focus: list[str] | None = None,
) -> tuple[str, str]:
    """Create standardized prompts for overall analysis generation.

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    sections_summary = "\n".join(
        [
            f"- {section.section_name}: {section.section_summary}"
            for section in section_analyses
        ]
    )

    focus_text = f" Focus areas: {', '.join(analysis_focus)}" if analysis_focus else ""

    system_prompt = (
        "You are a senior financial analyst. Provide executive-level analysis of the complete filing. "
        "Always use actual financial data when available and avoid placeholder variables. "
        "If specific numbers aren't available, provide descriptive qualitative statements instead."
    )

    user_prompt = (
        f"Based on all section analyses of {company_name}'s {filing_type.value} filing, provide a comprehensive overall analysis.{focus_text}\n\n"
        f"        Section Summaries:\n"
        f"        {sections_summary}\n\n"
        f"        Provide an executive-level analysis that synthesizes insights from all sections.\n\n"
        f"        IMPORTANT for financial_highlights:\n"
        f"        - Extract actual financial numbers, percentages, and dollar amounts from the filing content\n"
        f"        - If specific numbers are mentioned in the sections, use those exact values\n"
        f"        - If precise numbers aren't available, provide descriptive statements without placeholder variables (X, Y, Z)\n"
        f"        - Examples of good financial highlights:\n"
        f'          * "Revenue increased 15% year-over-year to $45.3 billion"\n'
        f'          * "Operating margins improved significantly compared to prior year"\n'
        f'          * "Strong cash position with substantial liquidity reserves"\n'
        f"        - Never use placeholder letters like X%, Y%, Z billion, or A%"
    )

    return system_prompt, user_prompt
