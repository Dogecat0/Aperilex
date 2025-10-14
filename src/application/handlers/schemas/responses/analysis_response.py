"""DTOs for analysis responses following the v3 `/api/analyses` contract."""

from __future__ import annotations

from datetime import date as summary_date
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.base.schema import SchemaVersionedModel
from src.application.handlers.schemas.responses.paginated_response import (
    PaginationMetadata,
)
from src.shared.enums import AnalysisStatus, AnalysisType

if TYPE_CHECKING:  # pragma: no cover - imported only for typing
    from src.application.interfaces.repositories import AnalysisData


class SummaryCompany(BaseModel):
    """Company descriptor embedded in the analysis summary."""

    name: str | None = Field(default=None, description="Company legal name")
    cik: str | None = Field(default=None, description="Company CIK identifier")
    ticker: str | None = Field(default=None, description="Exchange ticker symbol")

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryFiling(BaseModel):
    """Filing metadata embedded in the analysis summary."""

    type: str | None = Field(default=None, description="SEC filing type (e.g. 10-Q)")
    date: summary_date | None = Field(default=None, description="Filing date")
    analysis_template: str | None = Field(
        default=None, description="Template that drove the analysis pipeline"
    )
    accession_number: str | None = Field(
        default=None, description="EDGAR accession number for the analysed filing"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryConfidence(BaseModel):
    """Confidence signal for an analysis."""

    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score scaled 0..1",
    )
    bucket: str | None = Field(
        default=None,
        description="Qualitative confidence bucket (low|medium|high)",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SentimentSectionScore(BaseModel):
    """Sentiment score for an analysed filing section."""

    section: str = Field(description="Section label")
    score: float | None = Field(default=None, description="Sentiment score for section")

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummarySentiment(BaseModel):
    """Aggregate sentiment metrics for an analysis."""

    average: float | None = Field(default=None, description="Overall sentiment score")
    sections: list[SentimentSectionScore] = Field(
        default_factory=list,
        description="Per-section sentiment breakdown",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryInsightCounts(BaseModel):
    """Insight counters extracted from the analysis summary."""

    key_insights: int | None = Field(
        default=None, ge=0, description="Number of key insights"
    )
    opportunities: int | None = Field(
        default=None, ge=0, description="Number of opportunities"
    )
    critical_findings: int | None = Field(
        default=None, ge=0, description="Number of critical findings"
    )
    sections_analyzed: int | None = Field(
        default=None, ge=0, description="Number of filing sections analysed"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryProcessing(BaseModel):
    """Processing metadata for the analysis run."""

    duration_seconds: float | None = Field(
        default=None, ge=0.0, description="Seconds spent generating the analysis"
    )
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp for the analysis run"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummarySectionSegment(BaseModel):
    """Segmented overview card powering the filing summary surface."""

    id: str | None = Field(
        default=None,
        description="Stable identifier for the summary segment",
    )
    title: str = Field(description="Headline describing the segment focus")
    anchor: str = Field(
        description="Destination tab anchor (overview|sections|numbers|sentiment)"
    )
    summary: str | None = Field(
        default=None,
        description="Short narrative aligned to the segment",
    )
    supporting_points: list[str] = Field(
        default_factory=list,
        description="Supporting highlights reinforcing the segment narrative",
    )
    featured_metric: SummarySegmentFeaturedMetric | None = Field(
        default=None,
        description="Optional quantitative metric to feature within the segment",
    )
    cta_label: str | None = Field(
        default=None,
        description="Optional call-to-action label overriding default button copy",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummarySegmentFeaturedMetric(BaseModel):
    """Quantitative highlight rendered within a summary segment."""

    id: str = Field(description="Stable identifier for the metric")
    label: str = Field(description="Human readable metric label")
    current: str | None = Field(
        default=None,
        description="Formatted representation of the current value",
    )
    delta: str | None = Field(
        default=None,
        description="Formatted representation of the change versus prior period",
    )
    trend: Literal["up", "down", "flat"] | None = Field(
        default=None,
        description="Directional trend derived from the metric delta",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryHeadlineMetricDisplay(BaseModel):
    """Display formatting for a headline metric."""

    current: str | None = Field(
        default=None, description="Formatted representation of the current value"
    )
    previous: str | None = Field(
        default=None, description="Formatted representation of the prior value"
    )
    delta: str | None = Field(
        default=None, description="Formatted representation of the change"
    )
    delta_text: str | None = Field(
        default=None, description="Narrative description of the change"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryHeadlineMetric(BaseModel):
    """Hero metric surfaced in the summary."""

    id: str | None = Field(
        default=None, description="Stable identifier for the headline metric"
    )
    name: str = Field(description="Display name for the metric")
    category: str | None = Field(
        default=None, description="Metric grouping (liquidity, growth, etc.)"
    )
    unit: str | None = Field(default=None, description="Unit associated with values")
    current_value: float | None = Field(
        default=None, description="Current numeric value when available"
    )
    previous_value: float | None = Field(
        default=None, description="Previous numeric value when available"
    )
    delta_value: float | None = Field(
        default=None,
        description="Numeric delta between current and previous values when available",
    )
    display: SummaryHeadlineMetricDisplay = Field(
        default_factory=SummaryHeadlineMetricDisplay,
        description="Human-friendly representations of the metric values",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the metric if provided by the LLM",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryRiskHighlight(BaseModel):
    """Curated risk highlight for the summary."""

    id: str | None = Field(
        default=None, description="Stable identifier for the risk highlight"
    )
    title: str = Field(description="Title describing the risk or action")
    severity: str | None = Field(
        default=None, description="Severity level reported by the LLM"
    )
    probability: str | None = Field(
        default=None, description="Probability tier reported by the LLM"
    )
    summary: str | None = Field(
        default=None, description="Short narrative describing the highlight"
    )
    recommended_action: str | None = Field(
        default=None, description="Recommended action or mitigation steps"
    )
    related_sections: list[str] = Field(
        default_factory=list,
        description="Filing sections that informed this highlight",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryRiskHighlights(BaseModel):
    """Collection of curated risk highlights."""

    critical_actions: list[SummaryRiskHighlight] = Field(
        default_factory=list,
        description="High severity items requiring action",
    )
    signals_to_monitor: list[SummaryRiskHighlight] = Field(
        default_factory=list,
        description="Medium/low severity items to monitor",
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SentimentWeakestSection(BaseModel):
    """Descriptor for the weakest sentiment section."""

    section: str = Field(description="Section name")
    score: float | None = Field(
        default=None, description="Sentiment score for the weakest section"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummarySentimentRollup(BaseModel):
    """Enhanced sentiment rollup data for UI widgets."""

    overall: float | None = Field(
        default=None, description="Weighted sentiment across all sections"
    )
    weakest_section: SentimentWeakestSection | None = Field(
        default=None, description="Weakest scoring section information"
    )
    previous_overall: float | None = Field(
        default=None, description="Previous overall sentiment for comparison"
    )
    prior_analysis_delta: float | None = Field(
        default=None, description="Delta vs previous overall sentiment if known"
    )
    trend: str | None = Field(
        default=None,
        description="Trend direction compared to previous analysis (up|down|flat)",
    )
    confidence_band: str | None = Field(
        default=None, description="Confidence band for the aggregated sentiment"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class SummaryTimelineEvent(BaseModel):
    """Timeline event extracted from structured analysis data."""

    id: str | None = Field(default=None, description="Stable identifier for the event")
    occurred_at: datetime | None = Field(
        default=None, description="Timestamp associated with the event"
    )
    type: str | None = Field(
        default=None,
        description="Event type classification (metric|risk|milestone, etc.)",
    )
    severity: str | None = Field(
        default=None, description="Optional severity tier for the event"
    )
    title: str | None = Field(
        default=None, description="Short title describing the event"
    )
    summary: str | None = Field(
        default=None, description="Narrative summary of the timeline event"
    )
    source_section: str | None = Field(
        default=None, description="Section that produced the timeline entry"
    )
    related_metrics: list[str] = Field(
        default_factory=list,
        description="Metric identifiers linked to the event",
    )
    actions: list[str] = Field(
        default_factory=list, description="Follow-up actions linked to the event"
    )

    model_config = ConfigDict(extra="ignore", frozen=True)


class AnalysisSummary(BaseModel):
    """Structured summary exposed on `/api/analyses` list responses."""

    company: SummaryCompany = Field(
        default_factory=SummaryCompany,
        description="Company metadata extracted from the filing",
    )
    filing: SummaryFiling = Field(
        default_factory=SummaryFiling,
        description="Filing metadata used during analysis",
    )
    confidence: SummaryConfidence = Field(
        default_factory=SummaryConfidence,
        description="Confidence metrics generated by the pipeline",
    )
    sentiment: SummarySentiment = Field(
        default_factory=SummarySentiment,
        description="Sentiment scores calculated from the filing",
    )
    insight_counts: SummaryInsightCounts = Field(
        default_factory=SummaryInsightCounts,
        description="Key insight counters summarising the analysis",
    )
    processing: SummaryProcessing = Field(
        default_factory=SummaryProcessing,
        description="Analyst pipeline processing metadata",
    )
    summary_sections: list[SummarySectionSegment] = Field(
        default_factory=list,
        description="Segmented overview cards for the summary surface",
    )
    filing_summary: str | None = Field(
        default=None, description="Canonical filing summary narrative"
    )
    key_insights: list[str] = Field(
        default_factory=list,
        description="Curated key insight bullet points for the filing",
    )
    opportunities: list[str] = Field(
        default_factory=list,
        description="Identified opportunities extracted from the analysis",
    )
    critical_findings: list[str] = Field(
        default_factory=list,
        description="Critical findings requiring attention",
    )
    headline_metrics: list[SummaryHeadlineMetric] = Field(
        default_factory=list,
        description="Headline metrics for quick reference",
    )
    risk_highlights: SummaryRiskHighlights = Field(
        default_factory=SummaryRiskHighlights,
        description="Grouped risk highlight collections",
    )
    insight_timeline: list[SummaryTimelineEvent] = Field(
        default_factory=list,
        description="Ordered narrative of significant filing events",
    )
    sentiment_rollup: SummarySentimentRollup = Field(
        default_factory=SummarySentimentRollup,
        description="Enhanced sentiment aggregation for the filing",
    )

    model_config = ConfigDict(extra="allow", frozen=True)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> AnalysisSummary:
        """Hydrate a summary from a JSON payload safely."""
        if not payload:
            return cls()
        return cls.model_validate(payload)


class AnalysisResponse(SchemaVersionedModel):
    """Response DTO returned by both list and detail analysis endpoints."""

    schema_version: int = Field(default=3, ge=1)
    analysis_id: UUID = Field(description="Analysis identifier")
    filing_id: UUID = Field(description="Associated filing identifier")
    analysis_type: AnalysisType = Field(description="Type of analysis performed")
    status: AnalysisStatus = Field(description="Lifecycle status for the analysis")
    created_at: datetime = Field(description="Timestamp when the analysis was created")
    created_by: str | None = Field(
        default=None, description="User identifier that initiated the analysis"
    )
    summary: AnalysisSummary = Field(
        default_factory=AnalysisSummary,
        description="Compact summary payload shipped on list responses",
    )
    full_results: dict[str, Any] | None = Field(
        default=None,
        description="Full analysis artifact from blob storage when requested",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def from_data(
        cls,
        analysis: AnalysisData,
        *,
        summary_payload: dict[str, Any] | None = None,
        full_results: dict[str, Any] | None = None,
    ) -> AnalysisResponse:
        """Construct an `AnalysisResponse` from repository data."""
        summary_source = (
            summary_payload if summary_payload is not None else analysis.summary
        )
        if summary_source is None:
            raise ValueError(
                f"Analysis {analysis.id} is missing a persisted summary payload"
            )
        summary = AnalysisSummary.from_payload(summary_source)

        created_at = analysis.created_at or datetime.utcnow()

        return cls(
            analysis_id=analysis.id,
            filing_id=analysis.filing_id,
            analysis_type=AnalysisType.from_raw(analysis.analysis_type),
            status=analysis.status,
            created_at=created_at,
            created_by=analysis.created_by,
            summary=summary,
            full_results=full_results,
        )


class AnalysesListResponse(SchemaVersionedModel):
    """Envelope returned by the `/api/analyses` list endpoint."""

    schema_version: int = Field(default=3, ge=1)
    items: list[AnalysisResponse] = Field(
        default_factory=list,
        description="Analyses for the requested page",
    )
    pagination: PaginationMetadata = Field(
        description="Pagination block describing current cursor information"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


__all__ = [
    "AnalysesListResponse",
    "AnalysisResponse",
    "AnalysisSummary",
    "SummaryCompany",
    "SummaryConfidence",
    "SummaryFiling",
    "SummaryInsightCounts",
    "SummaryProcessing",
    "SummarySentiment",
    "SentimentSectionScore",
    "SummarySegmentFeaturedMetric",
]
