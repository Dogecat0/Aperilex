"""Query DTOs for read operations.

This module contains concrete query implementations that extend BaseQuery
for business read operations. Queries represent requests for data without
changing system state and include pagination support.

Queries available:
- GetFilingQuery: Retrieve specific filing details
- GetAnalysisQuery: Retrieve specific analysis results
- ListAnalysesQuery: List analyses with filtering and pagination
- ListCompanyFilingsQuery: List filings for a company with filtering and pagination
- ListRecentFilingsQuery: List recent filings across all companies
"""

from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.queries.list_company_filings import ListCompanyFilingsQuery

__all__ = [
    "GetFilingQuery",
    "GetAnalysisQuery",
    "ListAnalysesQuery",
    "ListCompanyFilingsQuery",
]
