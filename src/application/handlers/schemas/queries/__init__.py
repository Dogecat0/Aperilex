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

# ruff: noqa: I001

from src.application.handlers.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.handlers.schemas.queries.get_filing import GetFilingQuery
from src.application.handlers.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.handlers.schemas.queries.get_templates import GetTemplatesQuery
from src.application.handlers.schemas.queries.list_company_filings import (
    ListCompanyFilingsQuery,
    FilingSortField,
    SortDirection,
)
from src.application.handlers.schemas.queries.search_filings import SearchFilingsQuery

__all__ = [
    "GetFilingQuery",
    "GetAnalysisQuery",
    "ListAnalysesQuery",
    "GetTemplatesQuery",
    "ListCompanyFilingsQuery",
    "FilingSortField",
    "SearchFilingsQuery",
    "SortDirection",
]
