"""Handler for ListCompanyFilingsQuery - retrieves filings for a company with filtering and pagination."""

import logging
from uuid import uuid4

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.list_company_filings import ListCompanyFilingsQuery
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class ListCompanyFilingsQueryHandler(
    QueryHandler[ListCompanyFilingsQuery, PaginatedResponse[FilingResponse]]
):
    """Handler for listing company filings with filtering and pagination.

    This handler processes ListCompanyFilingsQuery by:
    - Applying filters for filing type and date range
    - Implementing pagination with sorting
    - Converting results to response DTOs
    - Providing filter summary for client consumption

    The handler focuses on data retrieval and pagination without presentation concerns.
    """

    def __init__(self, filing_repository: FilingRepository) -> None:
        """Initialize the handler with required dependencies.

        Args:
            filing_repository: Repository for filing data access
        """
        self.filing_repository = filing_repository

    async def handle(
        self, query: ListCompanyFilingsQuery
    ) -> PaginatedResponse[FilingResponse]:
        """Process the list company filings query.

        Args:
            query: The query containing filtering and pagination parameters

        Returns:
            PaginatedResponse[FilingResponse]: Paginated list of filings

        Raises:
            ValueError: If query parameters are invalid
        """
        logger.info(
            "Processing list company filings query",
            extra={
                "user_id": query.user_id,
                "ticker": query.ticker,
                "filing_type": query.filing_type.value if query.filing_type else None,
                "start_date": query.start_date.isoformat() if query.start_date else None,
                "end_date": query.end_date.isoformat() if query.end_date else None,
                "sort_by": query.sort_by.value,
                "sort_direction": query.sort_direction.value,
                "page": query.page,
                "page_size": query.page_size,
            },
        )

        try:
            # Build filter summary for response
            filter_parts = []

            filter_parts.append(f"ticker: {query.ticker}")

            if query.has_filing_type_filter and query.filing_type:
                filter_parts.append(f"filing_type: {query.filing_type.value}")

            if query.has_date_range_filter:
                if query.start_date and query.end_date:
                    filter_parts.append(
                        f"date: {query.start_date} to {query.end_date}"
                    )
                elif query.start_date:
                    filter_parts.append(f"date: from {query.start_date}")
                elif query.end_date:
                    filter_parts.append(f"date: until {query.end_date}")

            filters_applied = ", ".join(filter_parts)

            # Get total count for pagination
            total_count = await self.filing_repository.count_by_ticker_with_filters(
                ticker=query.ticker_value_object,
                filing_type=query.filing_type,
                start_date=query.start_date,
                end_date=query.end_date,
            )

            # If no results, return empty response
            if total_count == 0:
                return PaginatedResponse.empty(
                    page=query.page,
                    page_size=query.page_size,
                    query_id=uuid4(),
                    filters_applied=filters_applied,
                )

            # Get paginated results
            filings = await self.filing_repository.get_by_ticker_with_filters(
                ticker=query.ticker_value_object,
                filing_type=query.filing_type,
                start_date=query.start_date,
                end_date=query.end_date,
                sort_field=query.sort_by.value,
                sort_direction=query.sort_direction.value,
                page=query.page,
                page_size=query.page_size,
            )

            # Convert to response DTOs
            filing_responses = [
                FilingResponse.from_domain(filing) for filing in filings
            ]

            # Create paginated response
            response = PaginatedResponse.create(
                items=filing_responses,
                page=query.page,
                page_size=query.page_size,
                total_items=total_count,
                query_id=uuid4(),
                filters_applied=filters_applied,
            )

            logger.info(
                "Successfully listed company filings",
                extra={
                    "ticker": query.ticker,
                    "total_count": total_count,
                    "page": query.page,
                    "page_size": query.page_size,
                    "returned_count": len(filing_responses),
                    "filters_applied": filters_applied,
                },
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to list company filings",
                extra={
                    "error": str(e),
                    "user_id": query.user_id,
                    "ticker": query.ticker,
                    "page": query.page,
                    "page_size": query.page_size,
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[ListCompanyFilingsQuery]:
        """Return the query type this handler processes."""
        return ListCompanyFilingsQuery