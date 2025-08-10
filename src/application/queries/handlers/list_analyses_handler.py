"""Handler for ListAnalysesQuery - retrieves analyses with filtering and pagination."""

import logging
from uuid import uuid4

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.infrastructure.repositories.analysis_repository import AnalysisRepository

logger = logging.getLogger(__name__)


class ListAnalysesQueryHandler(
    QueryHandler[ListAnalysesQuery, PaginatedResponse[AnalysisResponse]]
):
    """Handler for listing analyses with filtering and pagination.

    This handler processes ListAnalysesQuery by:
    - Applying filters for company, date range, and analysis types
    - Implementing pagination with sorting
    - Converting results to response DTOs
    - Providing filter summary for client consumption

    The handler focuses on data retrieval and pagination without presentation concerns.
    """

    def __init__(self, analysis_repository: AnalysisRepository) -> None:
        """Initialize the handler with required dependencies.

        Args:
            analysis_repository: Repository for analysis data access
        """
        self.analysis_repository = analysis_repository

    async def handle(
        self, query: ListAnalysesQuery
    ) -> PaginatedResponse[AnalysisResponse]:
        """Process the list analyses query.

        Args:
            query: The query containing filtering and pagination parameters

        Returns:
            PaginatedResponse[AnalysisResponse]: Paginated list of analyses

        Raises:
            ValueError: If query parameters are invalid
        """
        logger.info(
            "Processing list analyses query",
            extra={
                "user_id": query.user_id,
                "company_cik": str(query.company_cik) if query.company_cik else None,
                "analysis_types": (
                    [t.value for t in query.analysis_types]
                    if query.analysis_types
                    else None
                ),
                "analysis_template": (
                    query.analysis_template.value if query.analysis_template else None
                ),
                "created_from": (
                    query.created_from.isoformat() if query.created_from else None
                ),
                "created_to": (
                    query.created_to.isoformat() if query.created_to else None
                ),
                "min_confidence_score": query.min_confidence_score,
                "sort_by": query.sort_by.value,
                "sort_direction": query.sort_direction.value,
                "page": query.page,
                "page_size": query.page_size,
            },
        )

        try:
            # Determine which analysis types to filter by
            # Priority: explicit analysis_types > template mapping > no filter
            filter_analysis_types = query.analysis_types

            # If no explicit analysis_types but template is provided, use template mapping
            if not filter_analysis_types and query.has_template_filter:
                filter_analysis_types = query.get_analysis_types_for_template()

            # Build filter summary for response
            filter_parts = []

            if query.has_company_filter:
                filter_parts.append(f"company: {query.company_cik}")

            if query.has_type_filter and query.analysis_types:
                types_str = ", ".join([t.value for t in query.analysis_types])
                filter_parts.append(f"types: {types_str}")

            if query.has_template_filter and query.analysis_template:
                filter_parts.append(f"template: {query.analysis_template.value}")
                # If template is used for filtering (no explicit types), show mapped types
                if not query.has_type_filter and filter_analysis_types:
                    mapped_types_str = ", ".join(
                        [t.value for t in filter_analysis_types]
                    )
                    filter_parts.append(f"mapped_to_types: {mapped_types_str}")

            if query.has_date_range_filter:
                if query.created_from and query.created_to:
                    filter_parts.append(
                        f"date: {query.created_from.date()} to {query.created_to.date()}"
                    )
                elif query.created_from:
                    filter_parts.append(f"date: from {query.created_from.date()}")
                elif query.created_to:
                    filter_parts.append(f"date: until {query.created_to.date()}")

            if query.min_confidence_score is not None:
                filter_parts.append(f"min_confidence: {query.min_confidence_score}")

            filters_applied = ", ".join(filter_parts) if filter_parts else "none"

            # Get total count for pagination using determined analysis types
            total_count = await self.analysis_repository.count_with_filters(
                company_cik=query.company_cik,
                analysis_types=filter_analysis_types,
                created_from=query.created_from,
                created_to=query.created_to,
                min_confidence_score=query.min_confidence_score,
            )

            # If no results, return empty response
            if total_count == 0:
                return PaginatedResponse.empty(
                    page=query.page,
                    page_size=query.page_size,
                    query_id=uuid4(),
                    filters_applied=filters_applied,
                )

            # Get paginated results using determined analysis types
            analyses = await self.analysis_repository.find_with_filters(
                company_cik=query.company_cik,
                analysis_types=filter_analysis_types,
                created_from=query.created_from,
                created_to=query.created_to,
                min_confidence_score=query.min_confidence_score,
                sort_by=query.sort_by,
                sort_direction=query.sort_direction,
                page=query.page,
                page_size=query.page_size,
            )

            # Convert to response DTOs (summary version for list view)
            analysis_responses = [
                AnalysisResponse.summary_from_domain(analysis) for analysis in analyses
            ]

            # Create paginated response
            response = PaginatedResponse.create(
                items=analysis_responses,
                page=query.page,
                page_size=query.page_size,
                total_items=total_count,
                query_id=uuid4(),
                filters_applied=filters_applied,
            )

            logger.info(
                "Successfully listed analyses",
                extra={
                    "total_count": total_count,
                    "page": query.page,
                    "page_size": query.page_size,
                    "returned_count": len(analysis_responses),
                    "filters_applied": filters_applied,
                },
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to list analyses",
                extra={
                    "error": str(e),
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
