"""Analysis request and result models for LLM processing."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.shared.enums.analysis import AnalysisType
from src.shared.enums.provider import LLMProvider
from src.shared.enums.status import AnalysisStatus
from src.shared.types.identifiers import AnalysisId, FilingId, TaskId, UserId

STRUCTURED_ANALYSIS_SCHEMA_VERSION = 3


class ModelTier(str, Enum):
    """LLM model tier for cost/performance trade-offs."""

    ECONOMY = "ECONOMY"  # Cheapest, fastest, lower quality
    STANDARD = "STANDARD"  # Balanced cost/quality
    PREMIUM = "PREMIUM"  # High quality, higher cost
    ULTRA = "ULTRA"  # Best quality, highest cost


class AnalysisRequest(BaseModel):
    """
    Request model for initiating an analysis.

    Contains all parameters needed to perform an LLM analysis
    on a filing document.
    """

    schema_version: int = Field(
        default=1, description="Schema version for backward compatibility"
    )

    # Core identifiers
    analysis_id: AnalysisId = Field(description="Unique analysis identifier (UUID)")
    filing_id: FilingId = Field(description="Filing to analyze (UUID)")
    task_id: TaskId = Field(description="Associated task ID (UUID)")
    user_id: UserId = Field(description="User requesting analysis (UUID)")

    # Analysis parameters
    analysis_type: AnalysisType = Field(
        default=AnalysisType.COMPREHENSIVE,
        description="Type of analysis to perform",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI, description="LLM provider to use"
    )
    model_tier: ModelTier = Field(
        default=ModelTier.STANDARD, description="Model tier for cost/quality trade-off"
    )

    # Model configuration
    model_name: str | None = Field(
        default=None, description="Specific model name override"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for response generation"
    )
    max_tokens: int | None = Field(
        default=None, description="Maximum tokens for response"
    )

    # Custom prompts (for CUSTOM analysis type)
    system_prompt: str | None = Field(
        default=None, description="System prompt override"
    )
    user_prompt: str | None = Field(
        default=None, description="User prompt for custom analysis"
    )

    # Response format
    response_format: str | None = Field(
        default=None, description="Desired response format (json, markdown, text)"
    )
    include_citations: bool = Field(
        default=False, description="Include source citations in response"
    )

    # Processing options
    streaming: bool = Field(default=False, description="Stream response tokens")
    timeout_seconds: int = Field(default=300, description="Request timeout in seconds")

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Request creation timestamp"
    )
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
        validate_assignment = True


class TokenUsage(BaseModel):
    """Token usage information for LLM processing."""

    prompt_tokens: int = Field(description="Number of tokens in the prompt")
    completion_tokens: int = Field(description="Number of tokens in the completion")
    total_tokens: int = Field(description="Total tokens used")


class SectionCostBreakdown(BaseModel):
    """Cost and token usage details for a single section analysis."""

    cost: float | None = Field(
        default=None,
        description="Estimated cost in USD attributed to this section",
    )
    token_usage: TokenUsage | None = Field(
        default=None, description="Tokens consumed while analyzing this section"
    )


class LessonReference(BaseModel):
    """Link a structured artifact to an instructional micro-lesson."""

    lesson_id: str = Field(description="Stable identifier for the lesson content")
    learning_module_key: str = Field(
        description="Module key that gates progression in the Learning Hub"
    )
    module_stage: str = Field(
        description="Module stage (e.g. orientation, fundamentals, assessment)"
    )
    title: str | None = Field(
        default=None, description="Optional lesson title for display surfaces"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("lesson_id", "learning_module_key", "module_stage")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        """Require non-empty strings for key lesson metadata."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        return value.strip()

    @field_validator("title")
    @classmethod
    def _validate_optional(cls, value: str | None) -> str | None:
        """Normalise optional title metadata."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title cannot be blank when provided")
        return stripped


class WalkthroughGuidance(BaseModel):
    """Copy blocks that frame the walkthrough focus."""

    focus: str = Field(description="Primary focus area for the section walkthrough")
    why_it_matters: str = Field(
        description="Narrative explaining the relevance of this focus area"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("focus", "why_it_matters")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        """Ensure guidance copy is provided."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("guidance text must be a non-empty string")
        return value.strip()


class HighlightCallout(BaseModel):
    """Key highlight surfaced during the guided walkthrough."""

    id: str = Field(description="Stable identifier for the highlight")
    title: str = Field(description="Short headline for the highlight")
    summary: str = Field(description="Narrative summary for the highlight")
    display_order: int = Field(
        ge=0,
        description="Zero-based order for rendering within the section walkthrough",
    )
    source_reference: str = Field(
        description="Source reference (section anchor, paragraph id, citation)"
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score emitted by the LLM pipeline",
    )
    severity: str | None = Field(
        default=None,
        description="Optional severity indicator (reuse risk severity labels when applicable)",
    )
    lesson_reference: LessonReference | None = Field(
        default=None, description="Linked lesson for deeper guidance"
    )
    quote: str | None = Field(
        default=None, description="Optional supporting quote pulled from the filing"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags aligned with lesson taxonomy and filters",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("id", "title", "summary", "source_reference")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        """Ensure required highlight strings are populated."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        return value.strip()

    @field_validator("quote")
    @classmethod
    def _normalize_quote(cls, value: str | None) -> str | None:
        """Normalise optional quote text."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped

    @field_validator("tags", mode="before")
    @classmethod
    def _ensure_tags(cls, value: Any) -> list[str]:
        """Coerce tag collections into a unique, trimmed list."""

        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("tags must be provided as a list")
        cleaned: list[str] = []
        for raw in value:
            text = str(raw).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned


class ComprehensionCheck(BaseModel):
    """Multiple-choice comprehension question anchored to the walkthrough."""

    id: str = Field(description="Stable identifier for the comprehension check")
    question: str = Field(description="Prompt presented to the learner")
    display_order: int = Field(
        ge=0,
        description="Zero-based order for rendering the comprehension checks",
    )
    correct_answer: str = Field(description="Exact text of the correct response")
    distractors: list[str] = Field(
        default_factory=list,
        description="Incorrect but plausible answer choices",
    )
    explanation: str = Field(description="Rationale reinforcing the correct answer")
    lesson_reference: LessonReference | None = Field(
        default=None,
        description="Linked lesson for remediation or additional depth",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("id", "question", "correct_answer", "explanation")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        """Ensure required comprehension strings are populated."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        return value.strip()

    @field_validator("distractors", mode="before")
    @classmethod
    def _validate_distractors(cls, value: Any) -> list[str]:
        """Require at least two distractors and normalise whitespace."""

        if value is None:
            raise ValueError("distractors must include at least two options")
        if not isinstance(value, list):
            raise TypeError("distractors must be provided as a list")
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        unique_items = list(dict.fromkeys(cleaned))
        if len(unique_items) < 2:
            raise ValueError("distractors must include at least two unique options")
        return unique_items

    @model_validator(mode="after")
    def _ensure_no_overlap(self) -> ComprehensionCheck:
        """Guarantee the correct answer does not duplicate distractors."""

        if self.correct_answer in self.distractors:
            raise ValueError("correct_answer must not appear in distractors")
        return self


class SectionWalkthrough(BaseModel):
    """Guided learning artifact for a filing section."""

    id: str = Field(description="Stable identifier for the section walkthrough")
    section_key: str = Field(
        description="Canonical section key (e.g. item_1a_risk_factors)"
    )
    title: str = Field(
        description="Display title shown in the walkthrough navigation"
    )
    display_order: int = Field(
        ge=0,
        description="Zero-based order for rendering across the filing walkthrough",
    )
    learning_module_key: str = Field(
        description="Module key this walkthrough unlocks or contributes toward"
    )
    module_stage: str = Field(
        description="Module stage categorising the walkthrough (e.g. foundation)"
    )
    guidance: WalkthroughGuidance = Field(
        description="Copy that sets expectations and relevance for the section"
    )
    highlights: list[HighlightCallout] = Field(
        default_factory=list,
        description="Curated highlights the learner should review within the section",
    )
    comprehension_checks: list[ComprehensionCheck] = Field(
        default_factory=list,
        description="Assessment questions validating section comprehension",
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        ge=1,
        description="Optional estimated completion time in minutes",
    )
    previous_comparison: dict[str, Any] | None = Field(
        default=None,
        description="Diff metadata comparing against the previous analysis run",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("id", "section_key", "title", "learning_module_key", "module_stage")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        """Ensure section walkthrough identifiers are populated."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        normalised = value.strip()
        if cls.__name__ == "SectionWalkthrough" and value is normalised:
            return normalised
        return normalised

    @field_validator("section_key")
    @classmethod
    def _normalise_section_key(cls, value: str) -> str:
        """Normalise section keys to trimmed canonical identifiers."""

        return value.strip()

    @field_validator("highlights", mode="before")
    @classmethod
    def _validate_highlights(cls, value: Any) -> list[HighlightCallout]:
        """Coerce highlight collections."""

        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())
        raise TypeError("highlights must be provided as a list")

    @field_validator("comprehension_checks", mode="before")
    @classmethod
    def _validate_checks(cls, value: Any) -> list[ComprehensionCheck]:
        """Coerce comprehension check collections."""

        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())
        raise TypeError("comprehension_checks must be provided as a list")

    @model_validator(mode="after")
    def _ensure_display_order(self) -> SectionWalkthrough:
        """Ensure display order increments without duplicates per collection."""

        self._validate_collection_order(self.highlights, "highlight")
        self._validate_collection_order(self.comprehension_checks, "comprehension")
        return self

    @staticmethod
    def _validate_collection_order(collection: list[Any], label: str) -> None:
        """Validate sequential display order for a collection."""

        seen: set[int] = set()
        for item in collection:
            order = getattr(item, "display_order", None)
            if not isinstance(order, int):
                raise ValueError(f"{label} items must define display_order as an int")
            if order in seen:
                raise ValueError(f"duplicate display_order detected for {label} items")
            seen.add(order)


class StructuredAnalysisData(BaseModel):
    """Structured analysis artifact persisted alongside narrative results."""

    schema_version: int = Field(
        default=STRUCTURED_ANALYSIS_SCHEMA_VERSION,
        description="Schema version for structured analysis data",
    )
    section_walkthroughs: dict[str, SectionWalkthrough] = Field(
        default_factory=dict,
        description="Guided walkthroughs keyed by canonical section identifiers",
    )

    model_config = ConfigDict(extra="allow", frozen=True)

    @field_validator("section_walkthroughs", mode="before")
    @classmethod
    def _coerce_walkthroughs(
        cls, value: Any
    ) -> dict[str, SectionWalkthrough]:
        """Coerce walkthrough collections into a dictionary keyed by section slug."""

        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        raise TypeError("section_walkthroughs must be provided as a mapping")

    @model_validator(mode="before")
    @classmethod
    def _inject_schema_version(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure structured artifacts carry the canonical schema version."""

        data = dict(values)
        version = data.get("schema_version")
        if not isinstance(version, int):
            data["schema_version"] = STRUCTURED_ANALYSIS_SCHEMA_VERSION
        return data

    @model_validator(mode="after")
    def _validate_walkthrough_keys(self) -> StructuredAnalysisData:
        """Ensure walkthrough keys align with their internal section identifiers."""

        for key, walkthrough in self.section_walkthroughs.items():
            if walkthrough.section_key != key:
                raise ValueError(
                    f"Walkthrough key '{key}' does not match section_key "
                    f"'{walkthrough.section_key}'"
                )
        return self


@dataclass(frozen=True)
class _WalkthroughTemplate:
    """Template metadata for generating default section walkthroughs."""

    title: str
    learning_module_key: str
    module_stage: str
    focus: str
    why_it_matters: str
    estimated_duration_minutes: int


_DEFAULT_SECTION_TEMPLATES: dict[str, _WalkthroughTemplate] = {
    "item 1 - business": _WalkthroughTemplate(
        title="Business Fundamentals Walkthrough",
        learning_module_key="orientation",
        module_stage="walkthrough",
        focus="Map the operating model, revenue mix, and moat signals.",
        why_it_matters="Clarity on the core business anchors every other section and uncovers competitive positioning gaps.",
        estimated_duration_minutes=8,
    ),
    "item 1a - risk factors": _WalkthroughTemplate(
        title="Risk Posture Review",
        learning_module_key="risk_mastery",
        module_stage="walkthrough",
        focus="Identify high-severity themes, mitigations, and monitoring cues.",
        why_it_matters="Prioritising risks helps direct diligence effort and spot red flags early.",
        estimated_duration_minutes=7,
    ),
    "part ii item 1a - risk factors": _WalkthroughTemplate(
        title="Risk Posture Review",
        learning_module_key="risk_mastery",
        module_stage="walkthrough",
        focus="Identify high-severity themes, mitigations, and monitoring cues.",
        why_it_matters="Prioritising risks helps direct diligence effort and spot red flags early.",
        estimated_duration_minutes=7,
    ),
    "item 7 - management discussion & analysis": _WalkthroughTemplate(
        title="MD&A Performance Story",
        learning_module_key="mda_foundations",
        module_stage="walkthrough",
        focus="Trace how management explains revenue, margin, and cash flow shifts.",
        why_it_matters="Understanding the narrative behind the numbers improves forecasting and stakeholder communication.",
        estimated_duration_minutes=9,
    ),
    "part i item 2 - management discussion & analysis": _WalkthroughTemplate(
        title="MD&A Performance Story",
        learning_module_key="mda_foundations",
        module_stage="walkthrough",
        focus="Trace how management explains revenue, margin, and cash flow shifts.",
        why_it_matters="Understanding the narrative behind the numbers improves forecasting and stakeholder communication.",
        estimated_duration_minutes=9,
    ),
    "balance sheet": _WalkthroughTemplate(
        title="Balance Sheet Health Check",
        learning_module_key="financial_statements",
        module_stage="walkthrough",
        focus="Evaluate liquidity, leverage, and capital structure resilience.",
        why_it_matters="Assessing balance sheet strength reveals runway, optionality, and solvency risks.",
        estimated_duration_minutes=6,
    ),
    "income statement": _WalkthroughTemplate(
        title="Income Statement Drivers",
        learning_module_key="financial_statements",
        module_stage="walkthrough",
        focus="Scan revenue growth, margin trends, and operating leverage signals.",
        why_it_matters="Spotting directionality in income statements informs strategic and financial planning.",
        estimated_duration_minutes=6,
    ),
    "cash flow statement": _WalkthroughTemplate(
        title="Cash Flow Mechanics",
        learning_module_key="financial_statements",
        module_stage="walkthrough",
        focus="Link operating cash generation with investing and financing flows.",
        why_it_matters="Cash flow context clarifies sustainability of capital allocation decisions.",
        estimated_duration_minutes=6,
    ),
}


def _slugify_section_key(value: str) -> str:
    """Normalise section keys for deterministic identifier construction."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "section"


def build_default_section_walkthrough(
    section_key: str,
    display_order: int,
) -> SectionWalkthrough | None:
    """Construct a default walkthrough scaffold for a known section."""

    template = _DEFAULT_SECTION_TEMPLATES.get(section_key.strip().lower())
    if template is None:
        return None

    return SectionWalkthrough(
        id=f"walkthrough-{_slugify_section_key(section_key)}",
        section_key=section_key,
        title=template.title,
        display_order=display_order,
        learning_module_key=template.learning_module_key,
        module_stage=template.module_stage,
        guidance=WalkthroughGuidance(
            focus=template.focus,
            why_it_matters=template.why_it_matters,
        ),
        highlights=[],
        comprehension_checks=[],
        estimated_duration_minutes=template.estimated_duration_minutes,
    )


def build_default_walkthrough_map(
    section_names: Sequence[str],
) -> dict[str, SectionWalkthrough]:
    """Generate default walkthroughs keyed by section name preserving order."""

    walkthroughs: dict[str, SectionWalkthrough] = {}
    for index, section_key in enumerate(section_names):
        walkthrough = build_default_section_walkthrough(section_key, index)
        if walkthrough is not None:
            walkthroughs[section_key] = walkthrough
    return walkthroughs


def _migrate_structured_analysis_to_v3(
    payload: dict[str, Any],
) -> dict[str, Any]:
    # TODO(guided-walkthrough-cutover): Remove once all persisted analyses have
    # schema_version >= 3 and no longer require default walkthrough scaffolding.
    """Upgrade legacy structured analysis payloads to schema v3."""

    data = dict(payload)

    existing_walkthroughs = data.get("section_walkthroughs")
    if not isinstance(existing_walkthroughs, dict) or not existing_walkthroughs:
        section_names: list[str] = []
        raw_sections = data.get("section_analyses")
        if isinstance(raw_sections, list):
            for entry in raw_sections:
                if isinstance(entry, dict):
                    section_name = entry.get("section_name")
                    if isinstance(section_name, str) and section_name.strip():
                        section_names.append(section_name.strip())

        walkthroughs = build_default_walkthrough_map(section_names)
        data["section_walkthroughs"] = {
            key: walkthrough.model_dump(mode="json")
            for key, walkthrough in walkthroughs.items()
        }
    else:
        data["section_walkthroughs"] = {
            str(key): value for key, value in existing_walkthroughs.items()
        }

    data["schema_version"] = STRUCTURED_ANALYSIS_SCHEMA_VERSION
    return data


try:  # pragma: no cover - defensive guard against duplicate registration
    from src.shared.versioning import schema_migrator

    schema_migrator.register(
        "StructuredAnalysisData",
        from_version=1,
        migration=_migrate_structured_analysis_to_v3,
    )
    schema_migrator.register(
        "StructuredAnalysisData",
        from_version=2,
        migration=_migrate_structured_analysis_to_v3,
    )
except ValueError:
    # Registration may occur multiple times in certain test re-import scenarios.
    pass


class AnalysisResult(BaseModel):
    """
    Result model for completed analysis.

    Contains the LLM response and all associated metadata
    from the analysis process.
    """

    schema_version: int = Field(
        default=3, description="Schema version for backward compatibility"
    )

    # Core identifiers
    analysis_id: AnalysisId = Field(description="Unique analysis identifier (UUID)")
    filing_id: FilingId = Field(description="Analyzed filing ID (UUID)")
    task_id: TaskId = Field(description="Associated task ID (UUID)")
    user_id: UserId = Field(description="User who requested analysis (UUID)")

    # Analysis results
    content: str = Field(description="Main analysis content/response")
    summary: str | None = Field(default=None, description="Brief summary of analysis")

    # Structured data (if applicable)
    structured_data: StructuredAnalysisData | None = Field(
        default=None, description="Structured extraction results"
    )
    # Citations have a known structure but can vary by source
    citations: list[dict[str, str | int]] | None = Field(
        default=None, description="Source citations from document"
    )

    # Analysis metadata
    analysis_type: AnalysisType = Field(description="Type of analysis performed")
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED, description="Analysis status"
    )

    # Model information
    llm_provider: LLMProvider = Field(description="LLM provider used")
    model_name: str = Field(description="Specific model used")
    model_version: str | None = Field(default=None, description="Model version")

    # Token usage and cost
    token_usage: TokenUsage = Field(description="Token usage statistics")
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    estimated_cost: float | None = Field(
        default=None, description="Estimated cost in USD"
    )

    # Quality metrics
    confidence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    quality_metrics: dict[str, float] | None = Field(
        default=None, description="Additional quality metrics"
    )
    costs_by_section: dict[str, SectionCostBreakdown] | None = Field(
        default=None, description="Token usage and cost by section"
    )

    # Timestamps
    created_at: datetime = Field(description="Result creation timestamp")
    completed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis completion timestamp"
    )
    expires_at: datetime | None = Field(
        default=None, description="Result expiration timestamp"
    )

    # Error information (if failed)
    error_message: str | None = Field(
        default=None, description="Error message if analysis failed"
    )
    error_code: str | None = Field(
        default=None, description="Error code for categorization"
    )

    # Additional metadata
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional result metadata"
    )

    @property
    def is_successful(self) -> bool:
        """Check if analysis was successful."""
        return self.status == AnalysisStatus.COMPLETED and not self.error_message

    @property
    def processing_time_seconds(self) -> float:
        """Get processing time in seconds."""
        return self.processing_time_ms / 1000.0

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
        validate_assignment = True

    @field_validator("structured_data", mode="before")
    @classmethod
    def _coerce_structured_data(
        cls, value: Any
    ) -> StructuredAnalysisData | None:
        """Coerce structured data payloads into the canonical model."""

        if value is None or isinstance(value, StructuredAnalysisData):
            return value

        if isinstance(value, dict):
            from src.shared.versioning import SchemaMigrationError, schema_migrator

            try:
                migrated = schema_migrator.migrate(
                    "StructuredAnalysisData",
                    value,
                    target_version=STRUCTURED_ANALYSIS_SCHEMA_VERSION,
                )
            except SchemaMigrationError as exc:  # pragma: no cover - surfaced upstream
                raise ValueError(
                    "structured_data payload could not be migrated to the current schema"
                ) from exc

            try:
                return StructuredAnalysisData(**migrated)
            except ValueError as exc:  # noqa: B904
                raise ValueError(
                    "structured_data payload is not compatible with StructuredAnalysisData"
                ) from exc

        raise TypeError("structured_data must be a mapping or StructuredAnalysisData")
