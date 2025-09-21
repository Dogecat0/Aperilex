"""Handler for SearchFilingsQuery - searches SEC filings from database."""

import logging
from uuid import uuid4

from src.application.base.handlers import QueryHandler
from src.application.handlers.schemas.queries.search_filings import (
    SearchFilingsQuery,
)
from src.application.handlers.schemas.responses.filing_search_response import (
    FilingSearchResult,
)
from src.application.handlers.schemas.responses.paginated_response import (
    PaginatedResponse,
)
from src.application.interfaces.query_services import IFilingQueryService
from src.application.interfaces.repositories import ICompanyRepository
from src.domain.value_objects.processing_status import ProcessingStatus
from src.shared.types import Ticker

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

    def __init__(
        self,
        company_repository: ICompanyRepository,
        filing_query_service: IFilingQueryService,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            company_repository: Repository for company identifier lookups
            filing_query_service: Query service for filing access
        """
        self.company_repository = company_repository
        self.filing_query_service = filing_query_service

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
            if not query.ticker:
                raise ValueError("Ticker is required")
            ticker_vo = Ticker(value=query.ticker)

            company = await self.company_repository.get_by_ticker(ticker_vo)

            if company is None:
                logger.info(
                    "No company found for ticker",
                    extra={"ticker": query.ticker},
                )
                return PaginatedResponse.empty(
                    page=query.page,
                    page_size=query.page_size,
                    query_id=uuid4(),
                    filters_applied=query.search_summary,
                )

            page_size = query.limit if query.limit is not None else query.page_size

            page_result = (
                await self.filing_query_service.list_company_filings_paginated(
                    company_id=company.id,
                    filing_type=query.form_type,
                    start_date=query.date_from,
                    end_date=query.date_to,
                    sort_field=query.sort_by.value,
                    sort_direction=query.sort_direction.value,
                    page=query.page,
                    page_size=page_size,
                )
            )

            if page_result.total_count == 0:
                return PaginatedResponse.empty(
                    page=query.page,
                    page_size=page_size,
                    query_id=uuid4(),
                    filters_applied=query.search_summary,
                )

            search_results: list[FilingSearchResult] = []
            company_ticker = str(company.ticker) if company.ticker else query.ticker
            company_name = company.name
            company_cik = str(company.cik)

            for filing in page_result.items:
                processing_status = ProcessingStatus(filing.processing_status)
                search_results.append(
                    FilingSearchResult(
                        accession_number=filing.accession_number,
                        filing_type=filing.filing_type.value,
                        filing_date=filing.filing_date.date(),
                        company_name=company_name,
                        cik=company_cik,
                        ticker=company_ticker,
                        has_content=processing_status.is_successful(),
                        sections_count=0,
                    )
                )

            # Create paginated response
            response = PaginatedResponse.create(
                items=search_results,
                page=query.page,
                page_size=page_size,
                total_items=page_result.total_count,
                query_id=uuid4(),
                filters_applied=query.search_summary,
            )

            logger.info(
                "Successfully searched filings",
                extra={
                    "ticker": query.ticker,
                    "total_found": page_result.total_count,
                    "page": query.page,
                    "page_size": page_size,
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

    @classmethod
    def query_type(cls) -> type[SearchFilingsQuery]:
        """Return the query type this handler processes."""
        return SearchFilingsQuery
