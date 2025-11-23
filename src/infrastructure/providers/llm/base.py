"""Base classes and utilities for LLM providers with 3-level hierarchy support."""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import cache
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, Field, conlist, model_validator
from pydantic import BaseModel as PydanticBaseModel

from src.application.interfaces.llm import (
    FinancialAnalysisRequest,
    FinancialAnalysisResponse,
    ILLMProvider,
    LLMPrompt,
    LLMRequest,
    LLMResponse,
)
from src.shared.config.providers import LLMConfig
from src.shared.enums import FilingType
from src.shared.models import LLMModelInfo, TokenUsage
from src.shared.models.analysis import build_default_section_walkthrough

from . import schemas


# Base response model with minimal common fields
class BaseSubSectionAnalysisResponse(BaseModel):
    """Base response model for all schema-specific responses."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    sub_section_name: str = Field(..., description="Semantic name of the sub-section")
    processing_time_ms: int | None = Field(
        None, description="Processing time in milliseconds"
    )
    schema_type: str = Field(..., description="Type of schema used")


# Generic analysis response class
class SubsectionAnalysisResponse(BaseSubSectionAnalysisResponse):
    """Generic subsection analysis response for individual schema components."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    schema_type: str = Field(..., description="Type of subsection schema")
    analysis: dict[str, Any] | list[Any] = Field(
        ...,
        description="Subsection analysis content which may be an object or a list",
    )
    parent_section: str = Field(..., description="Name of parent section")
    subsection_focus: str = Field(
        ..., description="Specific focus area of this subsection"
    )
    token_usage: TokenUsage | None = Field(
        default=None, description="Token usage for this subsection call"
    )
    cost: float | None = Field(
        default=None, description="Estimated cost for this subsection call in USD"
    )


# Union type for all possible sub-section response types
SubSectionAnalysisResponse = SubsectionAnalysisResponse


if TYPE_CHECKING:
    CriticalFindings = list[str]
else:
    CriticalFindings = conlist(str, max_length=5)


@dataclass(frozen=True, slots=True)
class SubsectionDefinition:
    """Schema-bound metadata for a subsection analysis task."""

    name: str
    schema: type[PydanticBaseModel]
    human_label: str | None = None
    is_collection: bool = False
    collection_item_schema: type[PydanticBaseModel] | None = None

    @property
    def schema_label(self) -> str:
        """Return the schema name that should be exposed to downstream consumers."""

        if self.collection_item_schema is not None:
            return self.collection_item_schema.__name__
        return self.schema.__name__


@dataclass(frozen=True)
class WalkthroughPromptContext:
    """Prompt scaffolding for generating guided walkthrough artifacts."""

    section_key: str
    title: str
    learning_module_key: str
    module_stage: str
    focus: str
    why_it_matters: str
    estimated_duration_minutes: int | None


class WalkthroughLessonReference(BaseModel):
    """Lesson linkage emitted alongside walkthrough artifacts."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    lesson_id: str = Field(..., description="Stable identifier for the lesson")
    learning_module_key: str = Field(
        ..., description="Module key aligned with the learning curriculum"
    )
    module_stage: str = Field(
        ..., description="Module stage (e.g. orientation, walkthrough, reinforce)"
    )
    title: str | None = Field(
        default=None, description="Optional learner-facing lesson title"
    )


class WalkthroughHighlight(BaseModel):
    """Highlight payload expected from guided walkthrough generation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable identifier for the highlight")
    title: str = Field(..., description="Short headline describing the highlight")
    summary: str = Field(..., description="Narrative summary for the highlight")
    source_reference: str = Field(
        ..., description="Precise citation (section header plus paragraph indicator)"
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1",
    )
    severity: str | None = Field(
        default=None,
        description="Optional severity label (reuse existing risk taxonomy values)",
    )
    lesson_reference: WalkthroughLessonReference = Field(
        ..., description="Lesson linkage powering downstream learning flows"
    )
    quote: str | None = Field(
        default=None,
        description="Optional supporting quote surfaced from the filing",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional taxonomy tags associated with the highlight",
    )


class WalkthroughComprehensionCheck(BaseModel):
    """Comprehension check emitted as part of the walkthrough."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable identifier for the comprehension check")
    question: str = Field(..., description="Learner-facing question text")
    correct_answer: str = Field(..., description="Correct answer to the question")
    distractors: list[str] = Field(
        ..., min_length=2, description="Incorrect yet plausible answer choices"
    )
    explanation: str = Field(
        ..., description="Explanation reinforcing why the correct answer is right"
    )
    lesson_reference: WalkthroughLessonReference = Field(
        ..., description="Lesson linkage for remediation or deeper study"
    )


class WalkthroughGuidancePayload(BaseModel):
    """Guidance copy framing the walkthrough focus."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    focus: str = Field(..., description="Primary focus area for the walkthrough")
    why_it_matters: str = Field(
        ..., description="Explanation of why the focus matters to the learner"
    )


class SectionWalkthroughPayload(BaseModel):
    """Structured walkthrough payload emitted by the LLM."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    guidance: WalkthroughGuidancePayload = Field(
        ..., description="Guidance copy anchoring the learner"
    )
    highlights: list[WalkthroughHighlight] = Field(
        ..., min_length=5, description="Highlights surfaced during the walkthrough"
    )
    comprehension_checks: list[WalkthroughComprehensionCheck] = Field(
        ...,
        min_length=5,
        description="Comprehension checks validating retention",
    )
    learning_module_key: str = Field(
        ..., description="Learning module key associated with this walkthrough"
    )
    module_stage: str = Field(
        ..., description="Learning module stage associated with this walkthrough"
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        ge=1,
        description="Optional estimated completion time in minutes",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Citations corresponding to surfaced highlights",
    )


@cache
def _walkthrough_prompt_contexts() -> dict[str, WalkthroughPromptContext]:
    """Cache default walkthrough prompt contexts keyed by canonical section names."""

    contexts: dict[str, WalkthroughPromptContext] = {}
    for section_name in SECTION_SCHEMAS.keys():
        template = build_default_section_walkthrough(section_name, 0)
        if template is None:
            continue

        canonical = _canonical_section_key(section_name)
        if canonical in contexts:
            continue

        contexts[canonical] = WalkthroughPromptContext(
            section_key=template.section_key,
            title=template.title,
            learning_module_key=template.learning_module_key,
            module_stage=template.module_stage,
            focus=template.guidance.focus,
            why_it_matters=template.guidance.why_it_matters,
            estimated_duration_minutes=template.estimated_duration_minutes,
        )
    return contexts


def _resolve_walkthrough_prompt_context(
    section_name: str,
) -> WalkthroughPromptContext | None:
    """Resolve the prompt context for the provided section name."""

    if not section_name:
        return None

    canonical = _canonical_section_key(section_name)
    if not canonical:
        return None

    contexts = _walkthrough_prompt_contexts()
    return contexts.get(canonical)


class SectionSummaryResponse(BaseModel):
    """Section summary response without sub-sections (for OpenAI structured output)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

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
    critical_findings: CriticalFindings = Field(
        ..., description="Critical findings that need attention"
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Source citations supporting the section deliverables",
    )
    walkthrough: SectionWalkthroughPayload | None = Field(
        default=None,
        description="Guided walkthrough payload for the section",
    )


class SectionAnalysisResponse(BaseModel):
    """Unified section analysis response combining summary and sub-sections."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

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
    critical_findings: CriticalFindings = Field(
        ..., description="Critical findings that need attention"
    )
    sub_sections: Sequence[SubSectionAnalysisResponse] = Field(
        ..., description="Detailed sub-section analyses"
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Source citations aligned with walkthrough highlights",
    )
    walkthrough: SectionWalkthroughPayload | None = Field(
        default=None,
        description="Guided walkthrough payload generated for this section",
    )
    processing_time_ms: int | None = Field(
        None, description="Processing time in milliseconds"
    )
    sub_section_count: int = Field(..., description="Number of sub-sections analyzed")
    token_usage: TokenUsage | None = Field(
        default=None,
        description="Token usage for analyzing this section including subsections",
    )
    cost: float | None = Field(
        default=None,
        description="Estimated cost for analyzing this section in USD",
    )


class OverallAnalysisResponse(BaseModel):
    """Overall analysis response for internal processing."""

    filing_summary: str = Field(
        ..., description="3-4 sentence summary of entire filing"
    )
    key_insights: list[str] = Field(
        ...,
        description="7-10 most important insights blending quantitative and qualitative signals",
    )
    opportunities: list[str] = Field(
        ..., description="Forward-looking opportunities mentioned"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Confidence in analysis"
    )


class ComprehensiveAnalysisResponse(BaseModel):
    """Comprehensive filing analysis response for API consumption."""

    # Consolidated overall analysis
    filing_summary: str = Field(
        ..., description="3-4 sentence summary of entire filing"
    )
    key_insights: list[str] = Field(
        ...,
        description="7-10 most important insights blending quantitative and qualitative signals",
    )
    opportunities: list[str] = Field(
        ..., description="Forward-looking opportunities mentioned"
    )
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
    token_usage: TokenUsage | None = Field(
        default=None,
        description="Token usage for the overall aggregation call",
    )
    cost: float | None = Field(
        default=None,
        description="Estimated cost for the overall aggregation call in USD",
    )
    filing_type: str = Field(..., description="Type of SEC filing")
    company_name: str = Field(..., description="Name of the company")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")


class BaseLLMProvider(ABC, ILLMProvider):
    """Base implementation for LLM providers with 3-level hierarchy support."""

    def __init__(
        self,
        config: LLMConfig,
        model_info: LLMModelInfo,
    ):
        """Initialize base LLM provider.

        Args:
            config: LLM configuration
            model_info: Model information
        """
        self.config = config
        self.model_info = model_info

    def _resolve_section_schema(
        self, section_name: str
    ) -> type[PydanticBaseModel] | None:
        """Return the schema best matching the provided section heading."""

        direct = SECTION_SCHEMAS.get(section_name)
        if direct is not None:
            return direct

        canonical_key = _canonical_section_key(section_name)
        if not canonical_key:
            return None

        match = CANONICAL_SECTION_SCHEMAS.get(canonical_key)
        if match is not None:
            return match

        for key, schema in CANONICAL_SECTION_SCHEMAS.items():
            if not key:
                continue
            if canonical_key.startswith(key) or key.startswith(canonical_key):
                return schema
            if key in canonical_key or canonical_key in key:
                return schema

        return None

    @abstractmethod
    async def analyze_filing_sections(
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

    async def analyze_filing(
        self,
        request: FinancialAnalysisRequest,
    ) -> FinancialAnalysisResponse:
        """Analyze a financial filing using LLM.

        Args:
            request: Financial analysis request

        Returns:
            Financial analysis response
        """
        import time

        start_time = time.time()

        # Parse filing content to extract sections
        filing_sections = self._parse_filing_sections(request.filing_content)

        # Convert analysis_type to FilingType
        filing_type = self._get_filing_type(request.analysis_type)

        # Get company name from additional context
        company_name = request.additional_context.get("company_name", "Unknown Company")

        # Perform hierarchical analysis
        focus_areas_raw: Any = request.additional_context.get("focus_areas", [])
        # Ensure focus_areas is a list
        if isinstance(focus_areas_raw, str):
            focus_areas: list[str] = [focus_areas_raw]
        elif isinstance(focus_areas_raw, list):
            focus_areas = focus_areas_raw
        else:
            focus_areas = []

        comprehensive_response = await self.analyze_filing_sections(
            filing_sections=filing_sections,
            filing_type=filing_type,
            company_name=company_name,
            analysis_focus=focus_areas,
        )

        # Convert to FinancialAnalysisResponse
        processing_time_ms = int((time.time() - start_time) * 1000)

        return FinancialAnalysisResponse(
            schema_version=1,
            filing_id=request.filing_id,
            analysis_type=request.analysis_type,
            summary=comprehensive_response.filing_summary,
            insights=comprehensive_response.key_insights,
            metrics={
                "total_sections": float(comprehensive_response.total_sections_analyzed),
                "total_subsections": float(
                    comprehensive_response.total_sub_sections_analyzed
                ),
                "confidence_score": comprehensive_response.confidence_score,
            },
            confidence_score=comprehensive_response.confidence_score,
            processing_time_ms=processing_time_ms,
        )

    async def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Generate a completion from the LLM using simplified request.

        Args:
            request: LLM request with prompt and parameters

        Returns:
            LLM response with completion
        """
        prompt = LLMPrompt(
            schema_version=1,
            system_prompt=request.system_prompt or "You are a helpful assistant.",
            user_prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 1000,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
        )

        return await self.generate_completion(prompt)

    async def validate_prompt(self, prompt: LLMPrompt) -> bool:
        """Validate a prompt before sending to LLM.

        Args:
            prompt: Prompt to validate

        Returns:
            True if prompt is valid
        """
        # Basic validation
        if not prompt.user_prompt:
            return False
        if prompt.temperature < 0 or prompt.temperature > 2:
            return False
        if prompt.max_tokens < 1:
            return False
        return True

    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy.

        Returns:
            True if provider is healthy
        """
        try:
            # Try a simple completion
            test_prompt = LLMPrompt(
                schema_version=1,
                system_prompt="You are a test assistant.",
                user_prompt="Say 'OK'",
                max_tokens=10,
                temperature=0,
            )
            response = await self.generate_completion(test_prompt)
            return bool(response.content)
        except Exception:
            return False

    async def get_model_info(self) -> LLMModelInfo:
        """Get information about the current model.

        Returns:
            Model information
        """
        return self.model_info

    def _parse_filing_sections(self, filing_content: str) -> dict[str, str]:
        """Parse filing content to extract sections.

        Args:
            filing_content: Raw filing content

        Returns:
            Dictionary of section_name -> section_text
        """
        # Simple section parsing - can be enhanced
        sections = {}
        current_section = None
        current_content: list[str] = []

        for line in filing_content.split("\n"):
            # Check for section headers (simple pattern matching)
            if line.strip().startswith("Item "):
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = line.strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Add last section
        if current_section:
            sections[current_section] = "\n".join(current_content)

        # If no sections found, treat entire content as one section
        if not sections:
            sections["Full Document"] = filing_content

        return sections

    def _get_filing_type(self, analysis_type: str) -> FilingType:
        """Convert analysis type to FilingType enum.

        Args:
            analysis_type: Analysis type string

        Returns:
            FilingType enum value
        """
        mapping = {
            "10-K": FilingType.FORM_10K,
            "10-Q": FilingType.FORM_10Q,
            "8-K": FilingType.FORM_8K,
            "fundamental": FilingType.FORM_10K,  # Default to 10-K for fundamental
        }
        return mapping.get(analysis_type, FilingType.FORM_10K)

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
SECTION_SCHEMAS: dict[str, type[PydanticBaseModel]] = cast(
    dict[str, type[PydanticBaseModel]],
    {
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
    },
)


def _canonical_section_key(name: str) -> str:
    """Return a canonical token for the provided section heading."""

    if not name:
        return ""

    lowered = name.lower().replace("&", "and")
    lowered = re.sub(r"\([^)]*\)", " ", lowered)
    lowered = re.sub(r"\s+\d+$", "", lowered)
    collapsed = re.sub(r"\s+", " ", lowered).strip()
    return re.sub(r"[^a-z0-9]", "", collapsed)


CANONICAL_SECTION_SCHEMAS: dict[str, type[PydanticBaseModel]] = {
    _canonical_section_key(section_name): schema
    for section_name, schema in SECTION_SCHEMAS.items()
}

CANONICAL_SECTION_SCHEMAS.update(
    {
        "balancesheets": schemas.BalanceSheetAnalysisSection,
        "condensedconsolidatedbalancesheets": schemas.BalanceSheetAnalysisSection,
        "consolidatedbalancesheets": schemas.BalanceSheetAnalysisSection,
        "statementsofoperations": schemas.IncomeStatementAnalysisSection,
        "condensedstatementsofoperations": schemas.IncomeStatementAnalysisSection,
        "condensedconsolidatedstatementsofoperations": schemas.IncomeStatementAnalysisSection,
        "statementsofcomprehensiveincome": schemas.IncomeStatementAnalysisSection,
        "condensedconsolidatedstatementsofcomprehensiveincome": schemas.IncomeStatementAnalysisSection,
        "statementsofcashflows": schemas.CashFlowAnalysisSection,
        "condensedstatementsofcashflows": schemas.CashFlowAnalysisSection,
        "condensedconsolidatedstatementsofcashflows": schemas.CashFlowAnalysisSection,
        "item2managementsdiscussionandanalysisoffinancialconditionandresultsofoperations": schemas.MDAAnalysisSection,
        "partiitem2managementdiscussionandanalysisoffinancialconditionandresultsofoperations": schemas.MDAAnalysisSection,
        "item7managementsdiscussionandanalysisoffinancialconditionandresultsofoperations": schemas.MDAAnalysisSection,
    }
)


@cache
def _build_collection_schema(
    field_name: str, item_schema: type[PydanticBaseModel]
) -> type[PydanticBaseModel]:
    """Create (and cache) a wrapper model enforcing a list of `item_schema` entries."""

    key = field_name or item_schema.__name__
    formatted = "".join(part.capitalize() for part in key.split("_") if part)
    class_name = f"{formatted or item_schema.__name__}List"

    class CollectionSchema(BaseModel):
        items: list[item_schema]  # type: ignore[valid-type]

        @model_validator(mode="before")
        @classmethod
        def _coerce_root(cls, value: Any) -> Any:
            if isinstance(value, list):
                return {"items": value}
            return value

    CollectionSchema.__name__ = class_name
    return CollectionSchema


def extract_subsection_definitions(
    schema_class: type[PydanticBaseModel],
) -> list[SubsectionDefinition]:
    """Extract subsection schema definitions from a main section schema.

    This method introspects the schema to identify all subsection fields that are
    themselves Pydantic models, enabling targeted analysis of each subsection.

    Args:
        schema_class: The main section schema class

    Returns:
        List of SubsectionDefinition entries describing each subsection schema
    """
    from enum import Enum

    subsections: list[SubsectionDefinition] = []

    for field_name, field_info in schema_class.model_fields.items():
        annotation = field_info.annotation
        field_type = annotation
        is_collection = False
        item_schema: type[PydanticBaseModel] | None = None

        origin = get_origin(field_type)
        if origin is Annotated:
            field_type = get_args(field_type)[0]

        origin = get_origin(field_type)
        if origin is Union:
            args = tuple(arg for arg in get_args(field_type) if arg is not type(None))
            if len(args) == 1:
                field_type = args[0]

        origin = get_origin(field_type)
        if origin in (list, tuple):
            args = get_args(field_type)
            if args:
                field_type = args[0]
                is_collection = True

        try:
            if (
                isinstance(field_type, type)
                and issubclass(field_type, PydanticBaseModel)
                and not issubclass(field_type, Enum)
            ):
                if is_collection:
                    item_schema = field_type
                    collection_schema = _build_collection_schema(field_name, field_type)
                    subsections.append(
                        SubsectionDefinition(
                            name=field_name,
                            schema=collection_schema,
                            is_collection=True,
                            collection_item_schema=item_schema,
                        )
                    )
                else:
                    subsections.append(
                        SubsectionDefinition(name=field_name, schema=field_type)
                    )
        except TypeError:
            continue

    return subsections


def create_human_readable_name(subsection_name: str) -> str:
    """Convert underscore-separated name to human-readable title case."""
    return subsection_name.replace("_", " ").title()


def create_analysis_prompt(
    human_readable_name: str,
    company_name: str,
    filing_type: FilingType,
    section_name: str,
    section_text: str,
    *,
    is_collection: bool = False,
) -> str:
    """Create standardized prompt for subsection analysis from full section text."""
    collection_instruction = ""
    if is_collection:
        collection_instruction = (
            "\n4. Return the structured analysis as a JSON object with an `items` array that captures every distinct "
            "entry required by the schema; never collapse the array into a single object."
        )

    return f"""You are reviewing the entire {section_name} section from {company_name}'s {filing_type.value} filing.

Instructions:
1. Locate the passages that are directly relevant to the {human_readable_name} topic.
2. Base your structured analysis exclusively on that relevant context, preserving necessary citations or figures.
3. If information is missing, state the limitation clearly rather than fabricating data.{collection_instruction}

Full Section Text:
{section_text}

Provide a detailed analysis for the {human_readable_name} schema using only the relevant context you identified."""


def create_fallback_subsection_response(
    subsection: SubsectionDefinition,
    section_name: str,
    error: str,
    processing_time_ms: int = 0,
) -> SubsectionAnalysisResponse:
    """Create a fallback response for failed subsection analysis."""
    human_readable_name = subsection.human_label or create_human_readable_name(
        subsection.name
    )
    empty_payload: dict[str, Any] | list[Any]
    if subsection.is_collection:
        empty_payload = []
    else:
        empty_payload = {}

    return SubsectionAnalysisResponse(
        sub_section_name=human_readable_name,
        processing_time_ms=processing_time_ms,
        schema_type=subsection.schema_label,
        analysis=empty_payload,
        parent_section=section_name,
        subsection_focus=f"Analysis failed: {error}",
    )


async def run_concurrent_subsection_analysis(
    subsection_definitions: Sequence[SubsectionDefinition],
    section_text: str,
    section_name: str,
    company_name: str,
    filing_type: FilingType,
    analyze_subsection_func: Callable[..., Awaitable[SubsectionAnalysisResponse]],
) -> list[SubsectionAnalysisResponse]:
    """Run concurrent analysis of all subsections in a section.

    This function encapsulates the common pattern of:
    1. Creating concurrent tasks for each subsection
    2. Running structured subsection analysis for each task
    3. Handling exceptions and creating fallback responses
    4. Filtering valid responses

    Args:
        subsection_definitions: Sequence of subsection definitions to analyze
        section_text: Full text of the parent section
        section_name: Name of the parent section
        company_name: Company name for context
        filing_type: Type of SEC filing
        analyze_subsection_func: Function to analyze a subsection

    Returns:
        List of valid SubsectionAnalysisResponse objects
    """

    async def analyze_subsection_task(
        subsection: SubsectionDefinition,
    ) -> SubsectionAnalysisResponse:
        """Concurrent task for analyzing a single subsection."""
        try:
            result = await analyze_subsection_func(
                subsection=subsection,
                section_text=section_text,
                section_name=section_name,
                company_name=company_name,
                filing_type=filing_type,
            )
            return result
        except Exception as e:
            return create_fallback_subsection_response(
                subsection=subsection,
                section_name=section_name,
                error=str(e),
            )

    # Run all subsection analyses concurrently
    tasks = [
        asyncio.create_task(analyze_subsection_task(definition))
        for definition in subsection_definitions
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
    sub_sections: Sequence[SubsectionAnalysisResponse],
    section_name: str,
    filing_type: FilingType,
    company_name: str,
    section_text: str | None = None,
) -> tuple[str, str]:
    """Create standardized prompts for section summary generation.

    Returns:
        Tuple of (system_prompt, user_prompt)
    """

    def _serialise_analysis_payload(raw_payload: Any) -> str:
        """Convert structured subsection output into a compact prompt fragment."""

        if raw_payload is None:
            return ""

        payload: Any = raw_payload
        if isinstance(payload, BaseModel):
            payload = payload.model_dump()

        if isinstance(payload, str):
            text = payload.strip()
        else:
            try:
                text = json.dumps(payload, ensure_ascii=False)
            except TypeError:
                text = str(payload)

        max_length = 800
        if len(text) > max_length:
            text = text[:max_length].rstrip() + "..."
        return text

    formatted_sub_sections: list[str] = []

    for sub in sub_sections:
        payload: Any = getattr(sub, "analysis", None)

        fragment = _serialise_analysis_payload(payload)

        if not fragment:
            fragment = "No structured findings were extracted."

        formatted_sub_sections.append(
            f"- {sub.sub_section_name} ({sub.schema_type}): {fragment}"
        )

    sub_sections_summary = "\n".join(formatted_sub_sections) or (
        "- No structured sub-section analyses were generated."
    )

    excerpt_block = ""
    if section_text:
        excerpt = section_text.strip()
        if excerpt:
            max_chars = 6000
            if len(excerpt) > max_chars:
                excerpt = excerpt[:max_chars].rstrip() + "..."
            excerpt_block = f"Relevant Section Text (excerpt):\n{excerpt}"

    walkthrough_context = _resolve_walkthrough_prompt_context(section_name)

    system_prompt = (
        "You are a financial analyst. Provide a consolidated summary of the section "
        "using the evidence below. Quote actual figures and qualitative details when available. "
        "In addition to the summary, produce guided learning artifacts (guidance, highlights, comprehension checks) "
        "that will coach a learner through this section."
    )

    deliverables_block = (
        "Deliverables:\n"
        "- section_summary: 4-6 sentences synthesizing the section narrative and context.\n"
        "- consolidated_insights: 5-7 bullet points capturing the most material cross-sectional signals.\n"
        "- critical_findings: 3-5 bullet points highlighting the most urgent risks or issues; never exceed 5 entries.\n"
        "- overall_sentiment: Float between -1 and 1 describing aggregate tone for the section.\n\n"
    )

    guideline_block = (
        "Guidelines:\n"
        "- Deliver a cohesive narrative, cite specific metrics when they appear, and avoid placeholder language.\n"
        "- If a data point is unavailable, explain the gap rather than inventing numbers.\n"
        "- Do not invent citations or emit placeholders such as 'TBD'."
    )

    walkthrough_block = ""
    if walkthrough_context:
        walkthrough_lines = [
            "Guided Walkthrough Requirements:",
            f'- Emit `walkthrough.learning_module_key` exactly as "{walkthrough_context.learning_module_key}" '
            f'and `walkthrough.module_stage` exactly as "{walkthrough_context.module_stage}".',
            "- Provide `walkthrough.guidance.focus` and `walkthrough.guidance.why_it_matters` as polished, filing-specific prose.",
            "- Populate `walkthrough.highlights` with exactly 5 entries; each entry must include `id`, `title`, `summary`, "
            "`source_reference` (section header + paragraph indicator), `confidence` (0-1), optional `severity`, "
            "`lesson_reference` (lesson_id, learning_module_key, module_stage, optional title), and optional `quote` and `tags`.",
            "- Provide `walkthrough.comprehension_checks` with exactly 5 entries; each entry must include `id`, `question`, "
            "`correct_answer`, `distractors` (minimum two), `explanation`, and `lesson_reference` "
            "(lesson_id, learning_module_key, module_stage, optional title).",
            "- Align comprehension checks to highlights one-to-one in the same display order; each check should reinforce the paired highlight's concept so learners review a highlight and immediately answer the related question.",
            "- Produce a `citations` array listing every `source_reference` surfaced in the highlights (one citation per highlight).",
            f'- Anchor the learner by covering the focus "{walkthrough_context.focus}" and explaining why it matters using '
            f'"{walkthrough_context.why_it_matters}" as context.',
            "- Use realistic kebab-case identifiers for highlights and checks; never emit placeholders.",
        ]
        if walkthrough_context.estimated_duration_minutes:
            walkthrough_lines.append(
                f"- Assume the walkthrough requires approximately "
                f"{walkthrough_context.estimated_duration_minutes} minutes to complete."
            )
        walkthrough_block = "\n".join(walkthrough_lines)

    prompt_fragments = [
        f"Based on the following sub-section analyses for the {section_name} section of "
        f"{company_name}'s {filing_type.value} filing, provide a comprehensive section summary that "
        f"integrates quantitative and qualitative signals.",
        f"Sub-section Analyses:\n{sub_sections_summary}",
        excerpt_block,
        deliverables_block.strip(),
        guideline_block,
        walkthrough_block,
    ]

    user_prompt = "\n\n".join(fragment for fragment in prompt_fragments if fragment)

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
        f"        Deliverables:\n"
        f"        - filing_summary: 3-4 sentences capturing the company's overall performance, strategic developments, and notable risks.\n"
        f"        - key_insights: 7-10 bullet points combining quantitative results and qualitative context. Anchor insights in actual metrics when available and explain material risk or operational signals in plain language.\n"
        f"        - opportunities: 3-5 bullet points highlighting forward-looking opportunities or strategic levers implied by the filing.\n"
        f"        - confidence_score: Float between 0 and 1 indicating analysis confidence.\n"
        f"        Avoid placeholder variables (X, Y, Z). If specific numbers are unavailable, use concrete descriptive statements instead."
    )

    return system_prompt, user_prompt
