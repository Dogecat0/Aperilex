"""Unified analysis type enumeration used across the application layers."""

from __future__ import annotations

from enum import Enum


class AnalysisType(str, Enum):
    """Canonical analysis types recognised by the platform."""

    COMPREHENSIVE = "COMPREHENSIVE"
    FINANCIAL = "FINANCIAL"
    RISK = "RISK"
    COMPETITION = "COMPETITION"
    BUSINESS = "BUSINESS"
    TREND = "TREND"
    SENTIMENT = "SENTIMENT"
    CUSTOM = "CUSTOM"

    @classmethod
    def from_raw(cls, value: str) -> AnalysisType:
        """Normalise raw database/provider values into the unified enum.

        Args:
            value: Raw analysis type value (case-insensitive)

        Returns:
            Normalised ``AnalysisType``

        Raises:
            ValueError: If the value cannot be normalised
        """

        if value is None:
            raise ValueError("Analysis type value cannot be None")

        normalized = value.strip().lower()

        alias_map: dict[str, AnalysisType] = {
            # Legacy comprehensive aliases
            "summary": cls.COMPREHENSIVE,
            "filing_analysis": cls.COMPREHENSIVE,
            "comprehensive": cls.COMPREHENSIVE,
            # Legacy focused aliases -> new buckets
            "financial_highlights": cls.FINANCIAL,
            "key_metrics": cls.FINANCIAL,
            "risk_factors": cls.RISK,
            "competitive_analysis": cls.COMPETITION,
            "comparison": cls.COMPETITION,
            "historical_trend": cls.TREND,
            "business_focused": cls.BUSINESS,
            "business": cls.BUSINESS,
            # Retain sentiment-focused analyses
            "sentiment": cls.SENTIMENT,
            # Custom entries
            "custom_query": cls.CUSTOM,
            "custom": cls.CUSTOM,
        }

        if normalized in alias_map:
            return alias_map[normalized]

        try:
            return cls(value.strip().upper())
        except ValueError as exc:  # noqa: B904
            raise ValueError(f"Unknown analysis type: {value}") from exc
