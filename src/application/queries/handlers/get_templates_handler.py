"""Handler for template queries - retrieves analysis template information."""

import logging

from src.application.base.handlers import QueryHandler
from src.application.schemas.queries.get_templates import GetTemplatesQuery
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.application.services.analysis_template_service import AnalysisTemplateService

logger = logging.getLogger(__name__)


class GetTemplatesQueryHandler(QueryHandler[GetTemplatesQuery, TemplatesResponse]):
    """Handler for retrieving analysis template information.

    This handler processes GetTemplatesQuery by:
    - Using AnalysisTemplateService to get all templates
    - Returning template metadata including descriptions and schema counts
    - Providing information needed for template selection in APIs

    The handler focuses on template metadata without presentation concerns.
    """

    def __init__(self, template_service: AnalysisTemplateService) -> None:
        """Initialize the handler with required dependencies.

        Args:
            template_service: Service for template information
        """
        self.template_service = template_service

    async def handle(self, query: GetTemplatesQuery) -> TemplatesResponse:
        """Process the get templates query.

        Args:
            query: The query for template information

        Returns:
            TemplatesResponse with template metadata and descriptions

        """
        logger.info(
            "Processing get templates query",
            extra={
                "user_id": query.user_id,
            },
        )

        try:
            # Get all templates with metadata from service
            response = TemplatesResponse.from_template_service(self.template_service)

            logger.info(
                f"Successfully retrieved {response.total_count} templates",
                extra={
                    "template_count": response.total_count,
                    "template_names": list(response.templates.keys()),
                },
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to retrieve templates",
                extra={
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[GetTemplatesQuery]:
        """Return the query type this handler processes."""
        return GetTemplatesQuery
