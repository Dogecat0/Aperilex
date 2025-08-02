"""Handler for SearchFilingsQuery - searches SEC filings through Edgar service."""

import logging
from uuid import uuid4

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.search_filings import SearchFilingsQuery
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.infrastructure.edgar.service import EdgarService

logger = logging.getLogger(__name__)


class SearchFilingsHandler(
    QueryHandler[SearchFilingsQuery, PaginatedResponse[FilingSearchResult]]
):
    """Handler for searching SEC filings through Edgar service.

    This handler processes SearchFilingsQuery by:
    - Using EdgarService to query SEC filings directly
    - Applying date and form type filters
    - Converting Edgar results to search result DTOs
    - Implementing pagination and sorting
    - Providing search summary for client consumption

    The handler focuses on discovery of filings rather than database lookups,
    making it suitable for exploring available SEC data.
    """

    def __init__(self, edgar_service: EdgarService) -> None:
        """Initialize the handler with required dependencies.

        Args:
            edgar_service: Service for Edgar/SEC data access
        """
        self.edgar_service = edgar_service

    async def handle(
        self, query: SearchFilingsQuery
    ) -> PaginatedResponse[FilingSearchResult]:
        """Process the search filings query.

        Args:
            query: The query containing search and pagination parameters

        Returns:
            PaginatedResponse[FilingSearchResult]: Paginated search results

        Raises:
            ValueError: If query parameters are invalid or search fails
        """
        logger.info(
            "Processing search filings query",
            extra={
                "user_id": query.user_id,
                "ticker": query.ticker,
                "form_type": query.form_type.value if query.form_type else None,
                "date_from": query.date_from.isoformat() if query.date_from else None,
                "date_to": query.date_to.isoformat() if query.date_to else None,
                "sort_by": query.sort_by.value,
                "sort_direction": query.sort_direction.value,
                "page": query.page,
                "page_size": query.page_size,
                "limit": query.limit,
            },
        )

        try:
            # Build search parameters for Edgar service
            search_params = self._build_edgar_search_params(query)

            # Get filings from Edgar service
            if query.has_form_type_filter and query.form_type:
                # Use specific filing type search
                filing_date = search_params.get("filing_date")
                limit = search_params.get("limit")
                amendments = search_params.get("amendments", True)

                edgar_filings = self.edgar_service.get_filings(
                    ticker=query.ticker_value_object,
                    filing_type=query.form_type,
                    filing_date=filing_date if isinstance(filing_date, str) else None,
                    limit=limit if isinstance(limit, int) else None,
                    amendments=bool(amendments),
                )
            else:
                # Use general search across all filing types
                filing_date = search_params.get("filing_date")
                limit = search_params.get("limit")
                amendments = search_params.get("amendments", True)

                edgar_filings = self.edgar_service.search_all_filings(
                    ticker=query.ticker_value_object,
                    filing_date=filing_date if isinstance(filing_date, str) else None,
                    limit=limit if isinstance(limit, int) else None,
                    amendments=bool(amendments),
                )

            # Convert Edgar results to search results
            search_results = [
                FilingSearchResult.from_edgar_data(filing_data)
                for filing_data in edgar_filings
            ]

            # Apply additional filtering if needed
            filtered_results = self._apply_additional_filters(search_results, query)

            # Apply sorting
            sorted_results = self._apply_sorting(filtered_results, query)

            # Apply pagination
            paginated_results = self._apply_pagination(sorted_results, query)

            # Calculate total count for pagination info
            total_count = len(filtered_results)

            # Create paginated response
            response = PaginatedResponse.create(
                items=paginated_results,
                page=query.page,
                page_size=query.page_size,
                total_items=total_count,
                query_id=uuid4(),
                filters_applied=query.search_summary,
            )

            logger.info(
                "Successfully searched filings",
                extra={
                    "ticker": query.ticker,
                    "total_found": len(edgar_filings),
                    "total_after_filters": total_count,
                    "page": query.page,
                    "page_size": query.page_size,
                    "returned_count": len(paginated_results),
                    "search_summary": query.search_summary,
                },
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to search filings",
                extra={
                    "error": str(e),
                    "user_id": query.user_id,
                    "ticker": query.ticker,
                    "form_type": query.form_type.value if query.form_type else None,
                },
                exc_info=True,
            )
            raise

    def _build_edgar_search_params(
        self, query: SearchFilingsQuery
    ) -> dict[str, str | int | bool]:
        """Build parameters for Edgar service based on query.

        Args:
            query: Search query with filters

        Returns:
            Dictionary of parameters for Edgar service
        """
        params: dict[str, str | int | bool] = {
            "amendments": True,  # Include amendments by default
            "limit": (
                query.effective_limit if query.limit else 50
            ),  # Default reasonable limit
        }

        # Add date filtering if specified
        if query.has_date_range_filter:
            if query.date_from and query.date_to:
                # Format as date range for Edgar service
                params["filing_date"] = f"{query.date_from}:{query.date_to}"
            elif query.date_from:
                params["filing_date"] = f"{query.date_from}:"
            elif query.date_to:
                params["filing_date"] = f":{query.date_to}"

        return params

    def _apply_additional_filters(
        self, results: list[FilingSearchResult], query: SearchFilingsQuery
    ) -> list[FilingSearchResult]:
        """Apply additional client-side filters that Edgar service doesn't support.

        Args:
            results: List of search results
            query: Search query with filters

        Returns:
            Filtered list of search results
        """
        filtered = results

        # Additional filtering could be added here if needed
        # For now, Edgar service handles the main filtering

        return filtered

    def _apply_sorting(
        self, results: list[FilingSearchResult], query: SearchFilingsQuery
    ) -> list[FilingSearchResult]:
        """Apply sorting to search results.

        Args:
            results: List of search results to sort
            query: Search query with sort criteria

        Returns:
            Sorted list of search results
        """
        reverse = query.sort_direction.value == "desc"

        if query.sort_by.value == "filing_date":
            return sorted(results, key=lambda x: x.filing_date, reverse=reverse)
        elif query.sort_by.value == "filing_type":
            return sorted(results, key=lambda x: x.filing_type, reverse=reverse)
        elif query.sort_by.value == "company_name":
            return sorted(results, key=lambda x: x.company_name, reverse=reverse)
        else:
            # Default to filing date
            return sorted(results, key=lambda x: x.filing_date, reverse=reverse)

    def _apply_pagination(
        self, results: list[FilingSearchResult], query: SearchFilingsQuery
    ) -> list[FilingSearchResult]:
        """Apply pagination to search results.

        Args:
            results: List of search results to paginate
            query: Search query with pagination info

        Returns:
            Paginated slice of search results
        """
        start_index = (query.page - 1) * query.page_size
        end_index = start_index + query.page_size
        return results[start_index:end_index]

    @classmethod
    def query_type(cls) -> type[SearchFilingsQuery]:
        """Return the query type this handler processes."""
        return SearchFilingsQuery
