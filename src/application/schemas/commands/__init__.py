"""Command DTOs for write operations.

This module contains concrete command implementations that extend BaseCommand
for business write operations. Commands represent intent to change system state
and include all necessary data and validation for the operation.

Commands available:
- AnalyzeFilingCommand: Trigger comprehensive analysis on SEC filings
- GenerateInsightsCommand: Derive insights from multiple analyses
- BatchAnalyzeCommand: Analyze multiple filings in batch operations
"""

from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand

__all__ = [
    "AnalyzeFilingCommand",
]
