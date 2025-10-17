"""Command DTOs for write operations.

This module contains concrete command implementations that extend BaseCommand
for business write operations. Commands represent intent to change system state
and include all necessary data and validation for the operation.

Commands available:
- AnalyzeFilingCommand: Trigger comprehensive analysis on SEC filings
- ImportFilingsCommand: Batch import SEC filings from Edgar
- KPIExtractCommand: Queue KPI-focused walkthrough output
- RiskDeltaCommand: Queue risk delta walkthrough output
- MdaQuizCommand: Queue MD&A-focused walkthrough output
"""

# ruff: noqa: I001

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.commands.kpi_extract import KPIExtractCommand
from src.application.handlers.schemas.commands.mda_quiz import MdaQuizCommand
from src.application.handlers.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.application.handlers.schemas.commands.risk_delta import RiskDeltaCommand

__all__ = [
    "AnalyzeFilingCommand",
    "ImportFilingsCommand",
    "ImportStrategy",
    "KPIExtractCommand",
    "RiskDeltaCommand",
    "MdaQuizCommand",
]
