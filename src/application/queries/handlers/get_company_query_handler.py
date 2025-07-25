"""Handler for GetCompanyQuery."""

import logging
from typing import Any

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.get_company import GetCompanyQuery
from src.application.schemas.responses.company_response import CompanyResponse
from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository

logger = logging.getLogger(__name__)


class GetCompanyQueryHandler(QueryHandler[GetCompanyQuery, CompanyResponse]):
    """Handler for retrieving comprehensive company information."""

    def __init__(
        self,
        company_repository: CompanyRepository,
        edgar_service: EdgarService,
        analysis_repository: AnalysisRepository,
    ) -> None:
        """Initialize GetCompanyQueryHandler.

        Args:
            company_repository: Repository for company database operations
            edgar_service: Service for accessing SEC EDGAR data
            analysis_repository: Repository for analysis data (for recent analyses)
        """
        self.company_repository = company_repository
        self.edgar_service = edgar_service
        self.analysis_repository = analysis_repository

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
            company_entity = None
            if lookup_type == "cik":
                company_entity = await self.company_repository.get_by_cik(lookup_value)
            elif lookup_type == "ticker":
                company_entity = await self.company_repository.get_by_ticker(
                    Ticker(lookup_value)
                )

            # Step 2: Get enriched data from EdgarService
            try:
                if lookup_type == "cik":
                    edgar_data = self.edgar_service.get_company_by_cik(
                        CIK(lookup_value)
                    )
                elif lookup_type == "ticker":
                    edgar_data = self.edgar_service.get_company_by_ticker(
                        Ticker(lookup_value)
                    )
                else:
                    raise ValueError(f"Unsupported lookup type: {lookup_type}")
            except Exception as e:
                logger.error(
                    "Failed to retrieve company data from EDGAR",
                    extra={
                        "lookup_type": lookup_type,
                        "lookup_value": str(lookup_value),
                    },
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Unable to retrieve company information from SEC EDGAR: {str(e)}"
                ) from e

            # Step 3: Collect optional enrichments
            enrichments = await self._collect_enrichments(
                query, edgar_data, company_entity
            )

            # Step 4: Create response
            if company_entity:
                logger.info(
                    "Company found in database, creating enhanced response",
                    extra={"company_id": str(company_entity.id)},
                )
                return CompanyResponse.from_domain_and_edgar(
                    company=company_entity, edgar_data=edgar_data, **enrichments
                )
            else:
                logger.info(
                    "Company not in database, creating EDGAR-only response",
                    extra={"cik": edgar_data.cik},
                )
                return CompanyResponse.from_edgar_only(
                    edgar_data=edgar_data, **enrichments
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

    async def _collect_enrichments(
        self,
        query: GetCompanyQuery,
        edgar_data: Any,
        company_entity: Company | None,
    ) -> dict[str, Any]:
        """Collect optional enrichment data based on query flags.

        Args:
            query: Original query with enrichment flags
            edgar_data: Company data from EdgarService
            company_entity: Company entity from database (may be None)

        Returns:
            Dictionary with enrichment data for response creation
        """
        enrichments: dict[str, Any] = {}

        # Recent analyses enrichment
        if query.include_recent_analyses and company_entity:
            try:
                recent_analyses = await self._get_recent_analyses(company_entity.cik)
                enrichments["recent_analyses"] = recent_analyses
                logger.debug(f"Added {len(recent_analyses)} recent analyses")
            except Exception as e:
                logger.warning(f"Failed to get recent analyses: {str(e)}")
                enrichments["recent_analyses"] = []

        return enrichments

    async def _get_recent_analyses(self, cik: CIK) -> list[dict[str, Any]]:
        """Get recent analyses for the company.

        Args:
            cik: Company CIK

        Returns:
            List of recent analysis summaries
        """
        try:
            # Get recent analyses from database
            # Get the 5 most recent analyses with pagination
            all_analyses = await self.analysis_repository.find_with_filters(
                company_cik=cik, page=1, page_size=5
            )
            analyses = all_analyses

            return [
                {
                    "analysis_id": str(analysis.id),
                    "analysis_type": analysis.analysis_type.value,
                    "created_at": analysis.created_at.isoformat(),
                    "confidence_score": analysis.confidence_score,
                    "summary": analysis.results.get("summary", "No summary available"),
                }
                for analysis in analyses
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch recent analyses for CIK {cik}: {str(e)}")
            return []

    @classmethod
    def query_type(cls) -> type[GetCompanyQuery]:
        """Return the query type this handler processes.

        Returns:
            GetCompanyQuery class
        """
        return GetCompanyQuery
