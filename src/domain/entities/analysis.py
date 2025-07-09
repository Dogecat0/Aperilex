"""Analysis entity for filing analysis results."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""

    FINANCIAL_SUMMARY = "financial_summary"
    RISK_ANALYSIS = "risk_analysis"
    RATIO_ANALYSIS = "ratio_analysis"
    TREND_ANALYSIS = "trend_analysis"
    PEER_COMPARISON = "peer_comparison"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    KEY_METRICS = "key_metrics"
    ANOMALY_DETECTION = "anomaly_detection"
    CUSTOM = "custom"


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
        created_by: UUID,
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
            created_by: User ID who initiated the analysis
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
        self._created_at = created_at or datetime.utcnow()
        self._insights: list[dict[str, Any]] = []

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
    def created_by(self) -> UUID:
        """Get creator user ID."""
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

    @property
    def insights(self) -> list[dict[str, Any]]:
        """Get analysis insights."""
        import copy

        return copy.deepcopy(self._insights)

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

    def get_summary(self) -> str:
        """Get analysis summary.

        Returns:
            Summary text if available, empty string otherwise
        """
        return str(self._results.get("summary", ""))

    def get_key_findings(self) -> list[str]:
        """Get key findings from analysis.

        Returns:
            List of key findings
        """
        findings = self._results.get("key_findings", [])
        if isinstance(findings, list):
            return [str(f) for f in findings]
        return []

    def get_risks(self) -> list[dict[str, Any]]:
        """Get identified risks.

        Returns:
            List of risk items
        """
        risks = self._results.get("risks", [])
        if isinstance(risks, list):
            return risks
        return []

    def get_opportunities(self) -> list[dict[str, Any]]:
        """Get identified opportunities.

        Returns:
            List of opportunity items
        """
        opportunities = self._results.get("opportunities", [])
        if isinstance(opportunities, list):
            return opportunities
        return []

    def get_metrics(self) -> dict[str, Any]:
        """Get calculated metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = self._results.get("metrics", {})
        if isinstance(metrics, dict):
            return metrics
        return {}

    def add_insight(self, key: str, value: Any) -> None:
        """Add an insight to results.

        Args:
            key: Insight key
            value: Insight value
        """
        if not key or not key.strip():
            raise ValueError("Insight key cannot be empty")

        self._results[key.strip()] = value

        # Also add to insights list if it's a structured insight
        if isinstance(value, dict) and "type" in value:
            self._insights.append(
                {
                    "id": str(uuid4()),
                    "key": key.strip(),
                    "timestamp": datetime.utcnow().isoformat(),
                    **value,
                }
            )

    def add_metric(self, name: str, value: Any, unit: str | None = None) -> None:
        """Add a metric to results.

        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit of measure
        """
        if not name or not name.strip():
            raise ValueError("Metric name cannot be empty")

        if "metrics" not in self._results:
            self._results["metrics"] = {}

        metric_data = {"value": value}
        if unit:
            metric_data["unit"] = unit

        self._results["metrics"][name.strip()] = metric_data

    def add_risk(
        self,
        description: str,
        severity: str,
        probability: str | None = None,
        impact: str | None = None,
    ) -> None:
        """Add a risk item.

        Args:
            description: Risk description
            severity: Risk severity (high, medium, low)
            probability: Risk probability
            impact: Potential impact
        """
        if not description or not description.strip():
            raise ValueError("Risk description cannot be empty")

        if "risks" not in self._results:
            self._results["risks"] = []

        risk_item = {
            "id": str(uuid4()),
            "description": description.strip(),
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if probability:
            risk_item["probability"] = probability
        if impact:
            risk_item["impact"] = impact

        self._results["risks"].append(risk_item)

    def update_confidence_score(self, score: float) -> None:
        """Update confidence score.

        Args:
            score: New confidence score (0.0 to 1.0)
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")

        self._confidence_score = score

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata entry.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

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

        return (
            f"Analysis: {self._analysis_type.value}{confidence_str} "
            f"- {self._created_at.date()}"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Analysis(id={self._id}, filing_id={self._filing_id}, "
            f"type={self._analysis_type}, created_at={self._created_at})"
        )
