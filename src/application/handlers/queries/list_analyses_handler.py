"""Handler for ListAnalysesQuery - retrieves analyses with filtering and pagination."""

import logging

from src.application.base.handlers import QueryHandler
from src.application.handlers.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysesListResponse,
    AnalysisResponse,
)
from src.application.handlers.schemas.responses.paginated_response import (
    PaginationMetadata,
)
from src.application.interfaces.repositories import IAnalysisRepository

logger = logging.getLogger(__name__)


class ListAnalysesQueryHandler(QueryHandler[ListAnalysesQuery, AnalysesListResponse]):
    """Handler for listing analyses with filtering and pagination.

    This handler processes ListAnalysesQuery by:
    - Applying filters for company scope, search, segment, status, and date ranges
    - Implementing pagination with richer sorting options
    - Hydrating summary DTOs directly from denormalized database payloads

    The handler focuses on data retrieval and pagination without presentation concerns.
    """

    def __init__(self, analysis_repository: IAnalysisRepository) -> None:
        """Initialize the handler with required dependencies.

        Args:
            analysis_repository: Repository for analysis data access
        """
        self.analysis_repository = analysis_repository

    async def handle(self, query: ListAnalysesQuery) -> AnalysesListResponse:
        """Process the list analyses query.

        Args:
            query: The query containing filtering and pagination parameters

        Returns:
            AnalysesListResponse: Paginated list of analyses

        Raises:
            ValueError: If query parameters are invalid
        """
        logger.info(
            "Processing list analyses query",
            extra={
                "user_id": query.user_id,
                "company_cik": str(query.company_cik) if query.company_cik else None,
                "search": query.search,
                "segment": query.segment.value,
                "statuses": (
                    [status.value for status in query.statuses]
                    if query.statuses
                    else None
                ),
                "created_after": (
                    query.created_after.isoformat() if query.created_after else None
                ),
                "created_before": (
                    query.created_before.isoformat() if query.created_before else None
                ),
                "created_by": query.created_by,
                "sort_by": query.sort_by.value,
                "sort_direction": query.sort_direction.value,
                "page": query.page,
                "page_size": query.page_size,
            },
        )

        try:
            company_cik_value = str(query.company_cik) if query.company_cik else None
            status_filters = (
                [status.value for status in query.statuses] if query.statuses else None
            )

            total_count = await self.analysis_repository.count_with_filters(
                company_cik=company_cik_value,
                search=query.search,
                segment=query.segment.value,
                statuses=status_filters,
                created_after=query.created_after,
                created_before=query.created_before,
                created_by=query.created_by,
            )

            if total_count == 0:
                pagination = PaginationMetadata.create(
                    query.page, query.page_size, total_items=0
                )
                return AnalysesListResponse(items=[], pagination=pagination)

            analyses = await self.analysis_repository.find_with_filters(
                company_cik=company_cik_value,
                search=query.search,
                segment=query.segment.value,
                statuses=status_filters,
                created_after=query.created_after,
                created_before=query.created_before,
                created_by=query.created_by,
                sort_by=query.sort_by.value,
                sort_direction=query.sort_direction.value,
                page=query.page,
                page_size=query.page_size,
            )

            analysis_responses = [
                AnalysisResponse.from_data(analysis) for analysis in analyses
            ]

            pagination = PaginationMetadata.create(
                query.page, query.page_size, total_items=total_count
            )

            response = AnalysesListResponse(
                items=analysis_responses,
                pagination=pagination,
            )

            logger.info(
                "Successfully listed analyses",
                extra={
                    "total_count": total_count,
                    "page": query.page,
                    "page_size": query.page_size,
                    "returned_count": len(analysis_responses),
                },
            )

            return response

        except Exception as exc:
            logger.error(
                "Failed to list analyses",
                extra={
                    "error": str(exc),
                    "user_id": query.user_id,
                    "page": query.page,
                    "page_size": query.page_size,
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[ListAnalysesQuery]:
        """Return the query type this handler processes."""
        return ListAnalysesQuery
