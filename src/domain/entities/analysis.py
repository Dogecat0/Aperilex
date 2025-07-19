"""Analysis entity for filing analysis results."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""

    FILING_ANALYSIS = "filing_analysis"  # Complete filing analysis from LLM
    CUSTOM_QUERY = "custom_query"  # Custom analysis based on user query
    COMPARISON = "comparison"  # Multi-filing or peer comparison
    HISTORICAL_TREND = "historical_trend"  # Time-series analysis across filings


class Analysis:
    """Analysis result entity.

    Represents the results of an analysis performed on a filing,
    including LLM-generated insights and calculated metrics.
    """

    def __init__(
        self,
        id: UUID,
        filing_id: UUID,
        analysis_type: AnalysisType,
        created_by: str | None,
        results: dict[str, Any] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        confidence_score: float | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """Initialize an Analysis entity.

        Args:
            id: Unique identifier for the analysis
            filing_id: ID of the filing analyzed
            analysis_type: Type of analysis performed
            created_by: Identifier of who initiated the analysis (e.g., API key, email)
            results: Analysis results data
            llm_provider: LLM provider used (e.g., "openai", "anthropic")
            llm_model: Specific model used (e.g., "gpt-4", "claude-3")
            confidence_score: Confidence in results (0.0 to 1.0)
            metadata: Additional analysis metadata
            created_at: Timestamp of analysis creation
        """
        self._id = id
        self._filing_id = filing_id
        self._analysis_type = analysis_type
        self._created_by = created_by
        self._results = results or {}
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        self._confidence_score = confidence_score
        self._metadata = metadata or {}
        self._created_at = created_at or datetime.now(UTC)

        self._validate_invariants()

    @property
    def id(self) -> UUID:
        """Get analysis ID."""
        return self._id

    @property
    def filing_id(self) -> UUID:
        """Get filing ID."""
        return self._filing_id

    @property
    def analysis_type(self) -> AnalysisType:
        """Get analysis type."""
        return self._analysis_type

    @property
    def created_by(self) -> str | None:
        """Get creator identifier."""
        return self._created_by

    @property
    def results(self) -> dict[str, Any]:
        """Get analysis results."""
        return self._results.copy()

    @property
    def llm_provider(self) -> str | None:
        """Get LLM provider."""
        return self._llm_provider

    @property
    def llm_model(self) -> str | None:
        """Get LLM model."""
        return self._llm_model

    @property
    def confidence_score(self) -> float | None:
        """Get confidence score."""
        return self._confidence_score

    @property
    def metadata(self) -> dict[str, Any]:
        """Get analysis metadata."""
        return self._metadata.copy()

    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at

    def is_filing_analysis(self) -> bool:
        """Check if this is a comprehensive filing analysis.

        Returns:
            True if analysis type is FILING_ANALYSIS
        """
        return self._analysis_type == AnalysisType.FILING_ANALYSIS

    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence.

        Returns:
            True if confidence score >= 0.8
        """
        if self._confidence_score is None:
            return False
        return self._confidence_score >= 0.8

    def is_medium_confidence(self) -> bool:
        """Check if analysis has medium confidence.

        Returns:
            True if confidence score between 0.5 and 0.8
        """
        if self._confidence_score is None:
            return False
        return 0.5 <= self._confidence_score < 0.8

    def is_low_confidence(self) -> bool:
        """Check if analysis has low confidence.

        Returns:
            True if confidence score < 0.5
        """
        if self._confidence_score is None:
            return True  # No score = low confidence
        return self._confidence_score < 0.5

    def get_filing_summary(self) -> str:
        """Get filing summary from comprehensive analysis.

        Returns:
            Filing summary text if available, empty string otherwise
        """
        return str(self._results.get("filing_summary", ""))

    def get_executive_summary(self) -> str:
        """Get executive summary from comprehensive analysis.

        Returns:
            Executive summary text if available, empty string otherwise
        """
        return str(self._results.get("executive_summary", ""))

    def get_key_insights(self) -> list[str]:
        """Get key insights from analysis.

        Returns:
            List of key insights
        """
        insights: Any = self._results.get("key_insights", [])
        if isinstance(insights, list):
            return [str(i) for i in insights]
        return []

    def get_risk_factors(self) -> list[str]:
        """Get risk factors from analysis.

        Returns:
            List of risk factors
        """
        risks = self._results.get("risk_factors", [])
        if isinstance(risks, list):
            return [str(r) for r in risks]
        return []

    def get_opportunities(self) -> list[str]:
        """Get identified opportunities.

        Returns:
            List of opportunities
        """
        opportunities = self._results.get("opportunities", [])
        if isinstance(opportunities, list):
            return [str(o) for o in opportunities]
        return []

    def get_financial_highlights(self) -> list[str]:
        """Get financial highlights from analysis.

        Returns:
            List of financial highlights
        """
        highlights = self._results.get("financial_highlights", [])
        if isinstance(highlights, list):
            return [str(h) for h in highlights]
        return []

    def get_section_analyses(self) -> list[dict[str, Any]]:
        """Get section analyses from comprehensive filing analysis.

        Returns:
            List of section analysis data
        """
        sections = self._results.get("section_analyses", [])
        if isinstance(sections, list):
            return sections
        return []

    def get_section_by_name(self, section_name: str) -> dict[str, Any] | None:
        """Get a specific section analysis by name.

        Args:
            section_name: Name of the section to retrieve

        Returns:
            Section analysis data or None if not found
        """
        for section in self.get_section_analyses():
            if section.get("section_name") == section_name:
                return section
        return None

    def update_results(self, results: dict[str, Any]) -> None:
        """Update analysis results.

        Args:
            results: New results data to merge with existing
        """
        self._results.update(results)

    def update_confidence_score(self, score: float) -> None:
        """Update confidence score.

        Args:
            score: New confidence score (0.0 to 1.0)
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")

        self._confidence_score = score

    def get_total_sub_sections(self) -> int:
        """Get total number of sub-sections analyzed.

        Returns:
            Total sub-sections count across all sections
        """
        total = 0
        for section in self.get_section_analyses():
            sub_sections = section.get("sub_sections", [])
            if isinstance(sub_sections, list):
                total += len(sub_sections)
        return total

    def get_analysis_depth(self) -> str:
        """Get analysis depth indicator based on content.

        Returns:
            Analysis depth (shallow, medium, comprehensive)
        """
        if self.is_filing_analysis():
            sections = len(self.get_section_analyses())
            sub_sections = self.get_total_sub_sections()
            if sections == 0 or sub_sections == 0:
                return "shallow"
            elif sections < 3 or sub_sections < 10:
                return "medium"
            else:
                return "comprehensive"
        else:
            # For custom queries, base on results size
            return "custom"

    def to_api_response(self) -> dict[str, Any]:
        """Convert analysis to API-friendly response format.

        Returns:
            Dictionary suitable for API responses
        """
        response = {
            "id": str(self._id),
            "filing_id": str(self._filing_id),
            "analysis_type": self._analysis_type.value,
            "created_by": str(self._created_by),
            "created_at": self._created_at.isoformat(),
            "llm_provider": self._llm_provider,
            "llm_model": self._llm_model,
            "confidence_score": self._confidence_score,
            "metadata": {
                **self._metadata,
                "processing_time_seconds": self.get_processing_time(),
            },
        }

        # For filing analysis, include the comprehensive results
        if self.is_filing_analysis():
            response.update(self._results)
        else:
            response["results"] = self._results

        return response

    def get_summary_for_api(self) -> dict[str, Any]:
        """Get condensed summary for API list responses.

        Returns:
            Condensed analysis summary
        """
        summary = {
            "id": str(self._id),
            "filing_id": str(self._filing_id),
            "analysis_type": self._analysis_type.value,
            "created_at": self._created_at.isoformat(),
            "confidence_score": self._confidence_score,
        }

        if self.is_filing_analysis():
            summary.update(
                {
                    "filing_summary": self.get_filing_summary(),
                    "key_insights_count": len(self.get_key_insights()),
                    "risk_factors_count": len(self.get_risk_factors()),
                    "opportunities_count": len(self.get_opportunities()),
                    "sections_analyzed": len(self.get_section_analyses()),
                }
            )
        else:
            summary["summary"] = self._results.get("summary", "")

        return summary

    def get_processing_time(self) -> float | None:
        """Get processing time if recorded.

        Returns:
            Processing time in seconds or None
        """
        return self._metadata.get("processing_time_seconds")

    def set_processing_time(self, seconds: float) -> None:
        """Set processing time.

        Args:
            seconds: Processing time in seconds
        """
        if seconds < 0:
            raise ValueError("Processing time cannot be negative")

        self._metadata["processing_time_seconds"] = seconds

    def is_llm_generated(self) -> bool:
        """Check if analysis was LLM-generated.

        Returns:
            True if LLM provider is specified
        """
        return self._llm_provider is not None

    def _validate_invariants(self) -> None:
        """Validate domain invariants."""
        if self._confidence_score is not None:
            if not 0.0 <= self._confidence_score <= 1.0:
                raise ValueError("Confidence score must be between 0.0 and 1.0")

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, Analysis):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self._id)

    def __str__(self) -> str:
        """String representation."""
        confidence_str = ""
        if self._confidence_score is not None:
            confidence_str = f" (confidence: {self._confidence_score:.2f})"

        depth_str = ""
        if self.is_filing_analysis():
            depth_str = f" [{self.get_analysis_depth()}]"

        return (
            f"Analysis: {self._analysis_type.value}{confidence_str}{depth_str} "
            f"- {self._created_at.date()}"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Analysis(id={self._id}, filing_id={self._filing_id}, "
            f"type={self._analysis_type}, created_at={self._created_at})"
        )
