"""Handler for GetFilingQuery - retrieves specific filing details."""

import logging

from src.application.base.exceptions import ResourceNotFoundError
from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.responses.filing_response import FilingResponse
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class GetFilingQueryHandler(QueryHandler[GetFilingQuery, FilingResponse]):
    """Handler for retrieving specific filing by ID.

    This handler processes GetFilingQuery by:
    - Retrieving filing entity from repository
    - Optionally including analysis count and latest analysis date
    - Converting to response DTO with requested detail level

    The handler focuses on data retrieval without presentation concerns.
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

    async def handle(self, query: GetFilingQuery) -> FilingResponse:
        """Process the get filing query.

        Args:
            query: The query containing filing retrieval parameters

        Returns:
            FilingResponse: Detailed filing information

        Raises:
            ValueError: If filing_id is invalid or filing not found
        """
        logger.info(
            f"Processing get filing query for ID {query.filing_id}",
            extra={
                "filing_id": str(query.filing_id),
                "include_analyses": query.include_analyses,
                "include_content_metadata": query.include_content_metadata,
                "user_id": query.user_id,
            },
        )

        try:
            # Validate required parameters
            if query.filing_id is None:
                raise ValueError("Filing ID is required")

            # Retrieve filing entity from repository
            filing = await self.filing_repository.get_by_id(query.filing_id)

            if not filing:
                raise ResourceNotFoundError("Filing", str(query.filing_id))

            # Optionally get analysis information
            analyses_count = None
            latest_analysis_date = None

            if query.include_analyses:
                # Get count of analyses for this filing
                analyses = await self.analysis_repository.find_by_filing_id(
                    query.filing_id  # Already validated as not None above
                )
                analyses_count = len(analyses) if analyses else 0

                # Get latest analysis date
                if analyses:
                    latest_analysis = max(analyses, key=lambda a: a.created_at)
                    latest_analysis_date = latest_analysis.created_at.date()

            # Convert to response DTO
            response = FilingResponse.from_domain(
                filing,
                analyses_count=analyses_count,
                latest_analysis_date=latest_analysis_date,
            )

            logger.info(
                f"Successfully retrieved filing {query.filing_id}",
                extra={
                    "filing_id": str(query.filing_id),
                    "accession_number": response.accession_number,
                    "filing_type": response.filing_type,
                    "processing_status": response.processing_status,
                    "analyses_count": analyses_count,
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to retrieve filing {query.filing_id}",
                extra={
                    "filing_id": str(query.filing_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[GetFilingQuery]:
        """Return the query type this handler processes."""
        return GetFilingQuery
