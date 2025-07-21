"""Query DTOs for read operations.

This module contains concrete query implementations that extend BaseQuery
for business read operations. Queries represent requests for data without
changing system state and include pagination support.

Queries available:
- GetFilingQuery: Retrieve specific filing details
- ListFilingsQuery: List filings with filtering and pagination
- GetAnalysisQuery: Retrieve specific analysis results
- ListAnalysesQuery: List analyses with filtering and pagination
"""

from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.queries.list_filings import ListFilingsQuery

__all__ = [
    "GetFilingQuery",
    "ListFilingsQuery",
    "GetAnalysisQuery",
    "ListAnalysesQuery",
]
