"""Handler for SearchFilingsQuery - searches SEC filings from database."""

import logging
from typing import Any
from uuid import uuid4

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.search_filings import SearchFilingsQuery
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.filing import Filing
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class SearchFilingsHandler(
    QueryHandler[SearchFilingsQuery, PaginatedResponse[FilingSearchResult]]
):
    """Handler for searching SEC filings from database.

    This handler processes SearchFilingsQuery by:
    - Querying filings from the database repository
    - Applying date and form type filters
    - Converting database results to search result DTOs
    - Implementing pagination and sorting
    - Providing search summary for client consumption

    The handler queries locally stored filings for improved performance
    and reduced external API dependencies.
    """

    def __init__(self, filing_repository: FilingRepository) -> None:
        """Initialize the handler with required dependencies.

        Args:
            filing_repository: Repository for database filing access
        """
        self.filing_repository = filing_repository

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
            # Create ticker value object (ticker is required and validated by query)
            if not query.ticker:
                raise ValueError("Ticker is required")
            ticker_vo = Ticker(query.ticker)

            # Get total count for pagination
            total_count = await self.filing_repository.count_by_ticker_with_filters(
                ticker=ticker_vo,
                filing_type=query.form_type,
                start_date=query.date_from,
                end_date=query.date_to,
            )

            # Get filings from database with pagination and company info
            filings_with_company = (
                await self.filing_repository.get_by_ticker_with_filters_and_company(
                    ticker=ticker_vo,
                    filing_type=query.form_type,
                    start_date=query.date_from,
                    end_date=query.date_to,
                    sort_field=query.sort_by.value,
                    sort_direction=query.sort_direction.value,
                    page=query.page,
                    page_size=query.page_size,
                )
            )

            # Convert to search results
            search_results = self._convert_to_search_results(filings_with_company)

            # Create paginated response
            response = PaginatedResponse.create(
                items=search_results,
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
                    "total_found": total_count,
                    "page": query.page,
                    "page_size": query.page_size,
                    "returned_count": len(search_results),
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

    def _convert_to_search_results(
        self, filings_with_company: list[tuple[Filing, dict[str, Any]]]
    ) -> list[FilingSearchResult]:
        """Convert database filings with company info to search result DTOs.

        Args:
            filings_with_company: List of tuples (Filing entity, company_info dict)

        Returns:
            List of FilingSearchResult DTOs
        """
        results = []

        for filing, company_info in filings_with_company:
            # Create search result using filing and company info
            result = FilingSearchResult(
                accession_number=str(filing.accession_number),
                filing_type=filing.filing_type.value,
                filing_date=filing.filing_date,
                company_name=company_info["name"],
                cik=company_info["cik"],
                ticker=company_info["ticker"],
                has_content=filing.processing_status.value == "COMPLETED",
                sections_count=0,  # Can be enhanced later to count actual sections
            )
            results.append(result)

        return results

    @classmethod
    def query_type(cls) -> type[SearchFilingsQuery]:
        """Return the query type this handler processes."""
        return SearchFilingsQuery
