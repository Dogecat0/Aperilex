"""Handler for template queries - retrieves analysis template information."""

import logging
from typing import Any

from src.application.base.handlers import QueryHandler
from src.application.base.query import BaseQuery
from src.application.services.analysis_template_service import AnalysisTemplateService

logger = logging.getLogger(__name__)


class GetTemplatesQuery(BaseQuery):
    """Query to retrieve all available analysis templates.

    This query has no parameters beyond the base query fields.
    """

    pass


class GetTemplatesQueryHandler(
    QueryHandler[GetTemplatesQuery, dict[str, dict[str, Any]]]
):
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

    async def handle(self, query: GetTemplatesQuery) -> dict[str, dict[str, Any]]:
        """Process the get templates query.

        Args:
            query: The query for template information

        Returns:
            Dictionary with template metadata and descriptions

        """
        logger.info(
            "Processing get templates query",
            extra={
                "user_id": query.user_id,
            },
        )

        try:
            # Get all templates with metadata from service
            templates = self.template_service.get_all_templates()

            logger.info(
                f"Successfully retrieved {len(templates)} templates",
                extra={
                    "template_count": len(templates),
                    "template_names": list(templates.keys()),
                },
            )

            return templates

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
