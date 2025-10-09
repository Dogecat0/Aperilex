"""Application layer schemas for commands, queries, and responses.

This package contains Data Transfer Objects (DTOs) for the application layer,
providing contracts between the presentation layer and domain layer.

The schemas are organized by purpose:
- commands/: Command DTOs that extend BaseCommand for write operations
- queries/: Query DTOs that extend BaseQuery for read operations
- responses/: Response DTOs for application layer results

These DTOs focus on business workflows and use domain value objects,
while maintaining clear separation from HTTP-specific presentation concerns.
"""

# ruff: noqa: I001

# Re-export the main schema categories for convenience
from src.application.handlers.schemas.commands import *  # noqa: F403, F401

# Also export specific key classes for direct import
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.queries import *  # noqa: F403, F401
from src.application.handlers.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.handlers.schemas.queries.get_filing import GetFilingQuery
from src.application.handlers.schemas.queries.list_analyses import (
    AnalysisSortField,
    ListAnalysesQuery,
    SortDirection as AnalysesSortDirection,
)
from src.application.handlers.schemas.queries.list_company_filings import (
    FilingSortField,
    ListCompanyFilingsQuery,
    SortDirection as CompanyFilingsSortDirection,
)
from src.application.handlers.schemas.responses import *  # noqa: F403, F401
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysesListResponse,
    AnalysisResponse,
)
from src.application.handlers.schemas.responses.error_response import (
    ErrorResponse,
    ErrorType,
)
from src.application.handlers.schemas.responses.filing_response import FilingResponse
from src.application.handlers.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse

__all__ = [
    # Commands
    "AnalyzeFilingCommand",
    "AnalysisTemplate",
    # Queries
    "GetFilingQuery",
    "GetAnalysisQuery",
    "ListAnalysesQuery",
    "ListCompanyFilingsQuery",
    "AnalysisSortField",
    "AnalysesSortDirection",
    "CompanyFilingsSortDirection",
    "FilingSortField",
    # Responses
    "FilingResponse",
    "AnalysisResponse",
    "AnalysesListResponse",
    "TaskResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMetadata",
    "ErrorType",
]
