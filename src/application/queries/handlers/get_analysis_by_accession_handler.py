"""Handler for GetAnalysisByAccessionQuery - retrieves analysis by filing accession number."""

import logging

from src.application.base.exceptions import ResourceNotFoundError
from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.get_analysis_by_accession import (
    GetAnalysisByAccessionQuery,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class GetAnalysisByAccessionQueryHandler(
    QueryHandler[GetAnalysisByAccessionQuery, AnalysisResponse]
):
    """Handler for retrieving the latest analysis for a filing by accession number.

    This handler processes GetAnalysisByAccessionQuery by:
    - Finding the filing by accession number
    - Retrieving the latest analysis for that filing
    - Converting to response DTO with requested detail level

    The handler uses a two-step lookup to bridge accession numbers to analyses.
    """

    def __init__(
        self,
        filing_repository: FilingRepository,
        analysis_repository: AnalysisRepository,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            filing_repository: Repository for filing data access
            analysis_repository: Repository for analysis data access
        """
        self.filing_repository = filing_repository
        self.analysis_repository = analysis_repository

    async def handle(self, query: GetAnalysisByAccessionQuery) -> AnalysisResponse:
        """Process the get analysis by accession number query.

        Args:
            query: The query containing analysis retrieval parameters

        Returns:
            AnalysisResponse: Detailed analysis information

        Raises:
            ValueError: If accession_number is invalid, filing not found, or no analysis found
        """
        logger.info(
            f"Processing get analysis query for accession {query.accession_number}",
            extra={
                "accession_number": str(query.accession_number),
                "include_full_results": query.include_full_results,
                "include_section_details": query.include_section_details,
                "include_processing_metadata": query.include_processing_metadata,
                "user_id": query.user_id,
            },
        )

        try:
            # Step 1: Find filing by accession number
            if query.accession_number is None:
                raise ValueError("accession_number is required")
            filing = await self.filing_repository.get_by_accession_number(
                query.accession_number
            )

            if not filing:
                raise ValueError(
                    f"Filing with accession number {query.accession_number} not found"
                )

            # Step 2: Get latest analysis for the filing
            analysis = await self.analysis_repository.get_latest_analysis_for_filing(
                filing.id
            )

            if not analysis:
                raise ResourceNotFoundError("Analysis", query.accession_number)

            # Convert to response DTO based on requested detail level
            if query.include_full_results:
                response = AnalysisResponse.from_domain(
                    analysis, include_full_results=True
                )
            else:
                response = AnalysisResponse.from_domain(
                    analysis, include_full_results=False
                )

            logger.info(
                f"Successfully retrieved analysis for filing {query.accession_number}",
                extra={
                    "accession_number": str(query.accession_number),
                    "filing_id": str(filing.id),
                    "analysis_id": str(analysis.id),
                    "analysis_type": response.analysis_type,
                    "confidence_score": response.confidence_score,
                    "sections_analyzed": response.sections_analyzed,
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to retrieve analysis for filing {query.accession_number}",
                extra={
                    "accession_number": str(query.accession_number),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[GetAnalysisByAccessionQuery]:
        """Return the query type this handler processes."""
        return GetAnalysisByAccessionQuery
