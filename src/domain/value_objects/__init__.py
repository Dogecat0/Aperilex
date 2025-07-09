"""Domain value objects for Aperilex SEC filing analysis.

This module contains value objects that provide validation and type safety
for the analysis system. Complex business logic has been removed to avoid
duplication with edgartools functionality.

Core value objects:
- AccessionNumber: SEC filing identifier validation
- CIK: Central Index Key validation
- FilingType: Filing type enumeration
- Money: Financial calculations with precision
- ProcessingStatus: Analysis pipeline state management
- Ticker: Stock ticker validation

For detailed SEC data processing, use edgartools directly.
"""

from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.money import Money
from src.domain.value_objects.processing_status import ProcessingStatus
from src.domain.value_objects.ticker import Ticker

__all__ = [
    "AccessionNumber",
    "CIK",
    "FilingType",
    "Money",
    "ProcessingStatus",
    "Ticker",
]
