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

# Re-export the main schema categories for convenience
from src.application.schemas.commands import *  # noqa: F403, F401

# Also export specific key classes for direct import
from src.application.schemas.commands.analyze_filing import (
    AnalysisPriority,
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.schemas.queries import *  # noqa: F403, F401
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.list_analyses import (
    AnalysisSortField,
    ListAnalysesQuery,
)
from src.application.schemas.queries.list_filings import (
    FilingSortField,
    ListFilingsQuery,
    SortDirection,
)
from src.application.schemas.responses import *  # noqa: F403, F401
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.error_response import ErrorResponse, ErrorType
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.schemas.responses.task_response import TaskResponse, TaskStatus

__all__ = [
    # Commands
    "AnalyzeFilingCommand",
    "AnalysisTemplate",
    "AnalysisPriority",
    # Queries
    "GetFilingQuery",
    "ListFilingsQuery",
    "GetAnalysisQuery",
    "ListAnalysesQuery",
    "FilingSortField",
    "AnalysisSortField",
    "SortDirection",
    # Responses
    "FilingResponse",
    "AnalysisResponse",
    "TaskResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMetadata",
    "TaskStatus",
    "ErrorType",
]
