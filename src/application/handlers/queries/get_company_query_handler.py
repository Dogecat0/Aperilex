"""Handler for GetCompanyQuery."""

import logging

from src.application.base.handlers import QueryHandler
from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.responses.company_response import (
    AnalysisSummary,
    CompanyResponse,
)
from src.application.interfaces.authentication import AuthenticationError
from src.application.interfaces.datasource import IDataSourceProvider
from src.application.interfaces.query_services import IAnalysisQueryService
from src.application.interfaces.repositories import (
    CompanyData,
    ICompanyRepository,
)
from src.domain.entities.company import Company
from src.shared.types import CIK, CompanyId, Ticker

logger = logging.getLogger(__name__)


class GetCompanyQueryHandler(QueryHandler[GetCompanyQuery, CompanyResponse]):
    """Handler for retrieving comprehensive company information."""

    def __init__(
        self,
        company_repository: ICompanyRepository,
        data_source_provider: IDataSourceProvider,
        analysis_query_service: IAnalysisQueryService,
    ) -> None:
        """Initialize GetCompanyQueryHandler.

        Args:
            company_repository: Repository for company database operations
            data_source_provider: Provider for accessing external data sources
            analysis_query_service: Query service for complex analysis queries
        """
        self.company_repository = company_repository
        self.data_source_provider = data_source_provider
        self.analysis_query_service = analysis_query_service

    async def handle(self, query: GetCompanyQuery) -> CompanyResponse:
        """Handle GetCompanyQuery by retrieving company information.

        Retrieval strategy:
        1. Look up company in database first
        2. Fetch enriched data from EdgarService
        3. Optionally include requested enrichments
        4. Return comprehensive company response

        Args:
            query: GetCompanyQuery with lookup criteria and options

        Returns:
            CompanyResponse with company information and optional enrichments

        Raises:
            ValueError: If company cannot be found in database or EDGAR
            RuntimeError: If EdgarService is unavailable
        """
        lookup_type, lookup_value = query.get_lookup_key()

        if not query.user_id:
            raise AuthenticationError(
                "Authenticated user context required for company retrieval"
            )

        logger.info(
            "Processing GetCompanyQuery",
            extra={
                "lookup_type": lookup_type,
                "lookup_value": str(lookup_value),
                "include_recent_analyses": query.include_recent_analyses,
            },
        )

        try:
            # Step 1: Try to find company in database
            company_record: CompanyData | None = None
            datasource_cik: CIK | None = None
            datasource_ticker: Ticker | None = None

            if lookup_type == "cik":
                cik_value = CIK(value=lookup_value)
                company_record = await self.company_repository.get_by_cik(cik_value)
                datasource_cik = cik_value
            elif lookup_type == "ticker":
                ticker_value = Ticker(value=lookup_value)
                company_record = await self.company_repository.get_by_ticker(
                    ticker_value
                )
                datasource_ticker = ticker_value
            elif lookup_type == "company_id":
                company_id = CompanyId(lookup_value)
                company_record = await self.company_repository.get_by_id(company_id)
                if company_record is None:
                    raise ValueError(
                        f"Company with ID {lookup_value} not found in database"
                    )
                datasource_cik = company_record.cik
            else:
                raise ValueError(f"Unsupported lookup type: {lookup_type}")

            company_domain = (
                Company(
                    id=company_record.id,
                    cik=company_record.cik,
                    name=company_record.name,
                    metadata=company_record.metadata,
                )
                if company_record is not None
                else None
            )

            # Step 2: Get enriched data from DataSourceProvider
            try:
                if datasource_cik is not None:
                    company_info = await self.data_source_provider.get_company_info(
                        cik=datasource_cik
                    )
                elif datasource_ticker is not None:
                    company_info = await self.data_source_provider.get_company_info(
                        ticker=datasource_ticker
                    )
                else:  # pragma: no cover - defensive guard
                    raise ValueError(
                        f"Unable to determine data source lookup for {lookup_type}"
                    )
            except Exception as e:
                logger.error(
                    "Failed to retrieve company data from data source",
                    extra={
                        "lookup_type": lookup_type,
                        "lookup_value": str(lookup_value),
                    },
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Unable to retrieve company information from data source: {str(e)}"
                ) from e

            # Step 3: Collect optional enrichments
            recent_analyses = await self._collect_recent_analyses(
                query=query,
                company_id=company_record.id if company_record else None,
            )

            # Step 4: Create response
            if company_domain:
                logger.info(
                    "Company found in database, creating enhanced response",
                    extra={"company_id": str(company_domain.id)},
                )
                return CompanyResponse.from_domain_and_datasource(
                    company=company_domain,
                    company_info=company_info,
                    recent_analyses=recent_analyses,
                )
            else:
                logger.info(
                    "Company not in database, creating data-source-only response",
                    extra={"cik": str(company_info.cik)},
                )
                return CompanyResponse.from_datasource_only(
                    company_info=company_info,
                    recent_analyses=recent_analyses,
                )

        except Exception:
            logger.error(
                "Failed to process GetCompanyQuery",
                extra={
                    "lookup_type": lookup_type,
                    "lookup_value": str(lookup_value),
                },
                exc_info=True,
            )
            raise

    async def _collect_recent_analyses(
        self,
        query: GetCompanyQuery,
        company_id: CompanyId | None,
    ) -> list[AnalysisSummary] | None:
        """Collect recent analyses enrichment when requested."""
        if not query.include_recent_analyses or company_id is None:
            return None

        try:
            recent_analyses = await self._get_recent_analyses(company_id)
            logger.debug("Added %d recent analyses", len(recent_analyses))
            return recent_analyses
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to get recent analyses for company %s: %s",
                company_id,
                exc,
            )
            return []

    async def _get_recent_analyses(
        self, company_id: CompanyId
    ) -> list[AnalysisSummary]:
        """Get recent analyses for the company.

        Args:
            company_id: Company ID

        Returns:
            List of recent analysis summaries
        """
        try:
            # Get recent completed analyses for the company
            analyses = await self.analysis_query_service.find_recent_completed(
                company_id=company_id, limit=5
            )

            return [
                {
                    "analysis_id": str(analysis.analysis_id),
                    "analysis_type": analysis.analysis_type,
                    "created_at": analysis.created_at.isoformat(),
                    "status": analysis.status.value,
                }
                for analysis in analyses
            ]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to fetch recent analyses for company %s: %s",
                company_id,
                exc,
            )
            return []

    @classmethod
    def query_type(cls) -> type[GetCompanyQuery]:
        """Return the query type this handler processes.

        Returns:
            GetCompanyQuery class
        """
        return GetCompanyQuery
