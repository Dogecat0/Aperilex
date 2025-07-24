"""Analysis Response DTO for application layer results."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.analysis import Analysis, AnalysisType


@dataclass(frozen=True)
class AnalysisResponse:
    """Response DTO for analysis information.

    This DTO provides a structured representation of analysis data optimized
    for application layer consumption, including results, confidence scores,
    and processing metadata.

    Attributes:
        analysis_id: Unique identifier for the analysis
        filing_id: ID of the filing that was analyzed
        analysis_type: Type of analysis performed
        created_by: Identifier of who initiated the analysis
        created_at: Timestamp when analysis was created
        confidence_score: Analysis confidence score (0.0 to 1.0)
        llm_provider: LLM provider used for analysis
        llm_model: Specific LLM model used
        processing_time_seconds: Time taken to complete analysis

        # Results data (included based on request)
        filing_summary: Brief summary of the filing (if available)
        executive_summary: Executive summary of analysis (if available)
        key_insights: List of key insights extracted (if available)
        risk_factors: List of identified risk factors (if available)
        opportunities: List of identified opportunities (if available)
        financial_highlights: List of financial highlights (if available)
        sections_analyzed: Number of sections analyzed
        full_results: Complete analysis results (if requested)
    """

    analysis_id: UUID
    filing_id: UUID
    analysis_type: str  # String representation for API consumption
    created_by: str | None
    created_at: datetime
    confidence_score: float | None
    llm_provider: str | None
    llm_model: str | None
    processing_time_seconds: float | None

    # Summary data (always included)
    filing_summary: str | None = None
    executive_summary: str | None = None
    key_insights: list[str] | None = None
    risk_factors: list[str] | None = None
    opportunities: list[str] | None = None
    financial_highlights: list[str] | None = None
    sections_analyzed: int | None = None

    # Full results (included only if explicitly requested)
    full_results: dict[str, Any] | None = None

    @classmethod
    def from_domain(
        cls, analysis: Analysis, include_full_results: bool = False
    ) -> "AnalysisResponse":
        """Create AnalysisResponse from domain Analysis entity.

        Args:
            analysis: Domain Analysis entity
            include_full_results: Whether to include complete analysis results

        Returns:
            AnalysisResponse with data from domain entity
        """
        return cls(
            analysis_id=analysis.id,
            filing_id=analysis.filing_id,
            analysis_type=analysis.analysis_type.value,
            created_by=analysis.created_by,
            created_at=analysis.created_at,
            confidence_score=analysis.confidence_score,
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            processing_time_seconds=analysis.get_processing_time(),
            # Extract key data from analysis results
            filing_summary=(
                analysis.get_filing_summary() if analysis.get_filing_summary() else None
            ),
            executive_summary=(
                analysis.get_executive_summary()
                if analysis.get_executive_summary()
                else None
            ),
            key_insights=(
                analysis.get_key_insights() if analysis.get_key_insights() else None
            ),
            risk_factors=(
                analysis.get_risk_factors() if analysis.get_risk_factors() else None
            ),
            opportunities=(
                analysis.get_opportunities() if analysis.get_opportunities() else None
            ),
            financial_highlights=(
                analysis.get_financial_highlights()
                if analysis.get_financial_highlights()
                else None
            ),
            sections_analyzed=(
                len(analysis.get_section_analyses())
                if analysis.get_section_analyses()
                else None
            ),
            # Include full results only if requested
            full_results=analysis.results if include_full_results else None,
        )

    @classmethod
    def summary_from_domain(cls, analysis: Analysis) -> "AnalysisResponse":
        """Create a summary-only AnalysisResponse from domain Analysis entity.

        This method creates a lightweight response suitable for list views
        that excludes full results and detailed analysis data.

        Args:
            analysis: Domain Analysis entity

        Returns:
            AnalysisResponse with summary data only
        """
        return cls(
            analysis_id=analysis.id,
            filing_id=analysis.filing_id,
            analysis_type=analysis.analysis_type.value,
            created_by=analysis.created_by,
            created_at=analysis.created_at,
            confidence_score=analysis.confidence_score,
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            processing_time_seconds=analysis.get_processing_time(),
            # Include only basic summary information
            sections_analyzed=(
                len(analysis.get_section_analyses())
                if analysis.get_section_analyses()
                else None
            ),
        )

    @property
    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence.

        Returns:
            True if confidence score >= 0.8
        """
        return self.confidence_score is not None and self.confidence_score >= 0.8

    @property
    def is_medium_confidence(self) -> bool:
        """Check if analysis has medium confidence.

        Returns:
            True if confidence score between 0.5 and 0.8
        """
        return self.confidence_score is not None and 0.5 <= self.confidence_score < 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Check if analysis has low confidence.

        Returns:
            True if confidence score < 0.5 or None
        """
        return self.confidence_score is None or self.confidence_score < 0.5

    @property
    def confidence_level(self) -> str:
        """Get confidence level as a string.

        Returns:
            "high", "medium", "low", or "unknown"
        """
        if self.confidence_score is None:
            return "unknown"
        elif self.is_high_confidence:
            return "high"
        elif self.is_medium_confidence:
            return "medium"
        else:
            return "low"

    @property
    def is_filing_analysis(self) -> bool:
        """Check if this is a comprehensive filing analysis.

        Returns:
            True if analysis type is FILING_ANALYSIS or COMPREHENSIVE
        """
        return self.analysis_type in (AnalysisType.FILING_ANALYSIS.value, AnalysisType.COMPREHENSIVE.value)

    @property
    def has_insights(self) -> bool:
        """Check if analysis has extracted insights.

        Returns:
            True if key_insights is not empty
        """
        return self.key_insights is not None and len(self.key_insights) > 0

    @property
    def has_risks(self) -> bool:
        """Check if analysis identified risk factors.

        Returns:
            True if risk_factors is not empty
        """
        return self.risk_factors is not None and len(self.risk_factors) > 0

    @property
    def has_opportunities(self) -> bool:
        """Check if analysis identified opportunities.

        Returns:
            True if opportunities is not empty
        """
        return self.opportunities is not None and len(self.opportunities) > 0

    def get_insights_summary(self) -> str:
        """Get a summary of available insights.

        Returns:
            String summarizing the types and counts of insights available
        """
        parts = []

        if self.has_insights and self.key_insights:
            parts.append(
                f"{len(self.key_insights)} insight{'s' if len(self.key_insights) != 1 else ''}"
            )

        if self.has_risks and self.risk_factors:
            parts.append(
                f"{len(self.risk_factors)} risk{'s' if len(self.risk_factors) != 1 else ''}"
            )

        if self.has_opportunities and self.opportunities:
            parts.append(
                f"{len(self.opportunities)} opportunit{'ies' if len(self.opportunities) != 1 else 'y'}"
            )

        if self.sections_analyzed:
            parts.append(
                f"{self.sections_analyzed} section{'s' if self.sections_analyzed != 1 else ''} analyzed"
            )

        return ", ".join(parts) if parts else "no insights available"
