"""Handler for GetAnalysisQuery - retrieves specific analysis details."""

import logging

from src.application.base.exceptions import ResourceNotFoundError
from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.infrastructure.repositories.analysis_repository import AnalysisRepository

logger = logging.getLogger(__name__)


class GetAnalysisQueryHandler(QueryHandler[GetAnalysisQuery, AnalysisResponse]):
    """Handler for retrieving specific analysis by ID.

    This handler processes GetAnalysisQuery by:
    - Retrieving analysis entity from repository
    - Converting to response DTO with requested detail level
    - Handling not found cases appropriately

    The handler focuses on data retrieval without presentation concerns.
    """

    def __init__(self, analysis_repository: AnalysisRepository) -> None:
        """Initialize the handler with required dependencies.

        Args:
            analysis_repository: Repository for analysis data access
        """
        self.analysis_repository = analysis_repository

    async def handle(self, query: GetAnalysisQuery) -> AnalysisResponse:
        """Process the get analysis query.

        Args:
            query: The query containing analysis retrieval parameters

        Returns:
            AnalysisResponse: Detailed analysis information

        Raises:
            ValueError: If analysis_id is invalid or analysis not found
        """
        logger.info(
            f"Processing get analysis query for ID {query.analysis_id}",
            extra={
                "analysis_id": str(query.analysis_id),
                "include_full_results": query.include_full_results,
                "include_section_details": query.include_section_details,
                "include_processing_metadata": query.include_processing_metadata,
                "user_id": query.user_id,
            },
        )

        try:
            # Validate required parameters
            if query.analysis_id is None:
                raise ValueError("Analysis ID is required")

            # Retrieve analysis entity from repository
            analysis = await self.analysis_repository.get_by_id(query.analysis_id)

            if not analysis:
                raise ResourceNotFoundError("Analysis", str(query.analysis_id))

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
                f"Successfully retrieved analysis {query.analysis_id}",
                extra={
                    "analysis_id": str(query.analysis_id),
                    "analysis_type": response.analysis_type,
                    "confidence_score": response.confidence_score,
                    "sections_analyzed": response.sections_analyzed,
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to retrieve analysis {query.analysis_id}",
                extra={
                    "analysis_id": str(query.analysis_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[GetAnalysisQuery]:
        """Return the query type this handler processes."""
        return GetAnalysisQuery
