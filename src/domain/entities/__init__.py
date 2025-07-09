"""Domain entities for Aperilex SEC filing analysis.

This module contains the core entities for the analysis system:
- Analysis: Stores analysis results and insights
- Company: Minimal reference entity for company identification
- Filing: Tracks processing status of SEC filings

For detailed filing data, use edgartools directly.
"""

from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing

__all__ = [
    "Analysis",
    "AnalysisType",
    "Company",
    "Filing",
]
