"""
SEC filing analysis enumeration.
"""

from enum import Enum


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""

    FILING_ANALYSIS = "filing_analysis"  # Complete filing analysis from LLM
    COMPREHENSIVE = (
        "comprehensive"  # Comprehensive analysis (alias for filing_analysis)
    )
    CUSTOM_QUERY = "custom_query"  # Custom analysis based on user query
    COMPARISON = "comparison"  # Multi-filing or peer comparison
    HISTORICAL_TREND = "historical_trend"  # Time-series analysis across filings
