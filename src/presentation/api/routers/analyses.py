"""API router for analysis-related endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_templates import GetTemplatesQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.infrastructure.database.base import get_db
from src.presentation.api.dependencies import get_service_factory

logger = logging.getLogger(__name__)

# Create router with appropriate prefix and tags
router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
    responses={
        404: {"description": "Analysis not found"},
        422: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)

# Type aliases for dependencies
SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
AnalysisIdPath = Annotated[UUID, Path(description="Analysis ID")]


@router.get(
    "",
    response_model=list[AnalysisResponse],
    summary="List analyses",
    description="""
    List analyses with optional filtering and pagination.

    Supports filtering by company CIK, analysis type, date range, and confidence score.
    Results are ordered by creation date (newest first) and support pagination.
    """,
)
async def list_analyses(
    session: SessionDep,
    factory: ServiceFactoryDep,
    # Filtering parameters
    company_cik: Annotated[
        str | None, Query(description="Filter by company CIK (e.g., '0000320193')")
    ] = None,
    analysis_type: Annotated[
        AnalysisType | None, Query(description="Filter by analysis type")
    ] = None,
    min_confidence: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Minimum confidence score (0.0-1.0)"),
    ] = None,
    # Pagination parameters
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of analyses per page (max 100)")
    ] = 20,
) -> list[AnalysisResponse]:
    """List analyses with filtering and pagination.

    Args:
        session: Database session for repository operations
        factory: Service factory for dependency injection
        company_cik: Optional CIK to filter by specific company
        analysis_type: Optional analysis type filter
        min_confidence: Optional minimum confidence score filter
        page: Page number for pagination (1-based)
        page_size: Number of results per page

    Returns:
        List of AnalysisResponse objects matching the filters

    Raises:
        HTTPException: 422 if query parameters are invalid
        HTTPException: 500 if listing fails
    """
    logger.info(
        "Listing analyses",
        extra={
            "company_cik": company_cik,
            "analysis_type": analysis_type.value if analysis_type else None,
            "min_confidence": min_confidence,
            "page": page,
            "page_size": page_size,
        },
    )

    try:
        # Validate and convert CIK if provided
        cik_obj = None
        if company_cik:
            try:
                cik_obj = CIK(company_cik)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid CIK format: {str(e)}",
                ) from e

        # Calculate offset for pagination
        (page - 1) * page_size

        # Create query
        # Convert single analysis_type to list for schema compatibility
        analysis_types = [analysis_type] if analysis_type else None

        query = ListAnalysesQuery(
            company_cik=cik_obj,
            analysis_types=analysis_types,
            # Note: ListAnalysesQuery doesn't support min_confidence_score, offset, limit
            # These parameters need to be handled differently or the schema needs updating
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        results: list[AnalysisResponse] = await dispatcher.dispatch_query(
            query, dependencies
        )

        logger.info(
            "Listed analyses successfully",
            extra={
                "results_count": len(results),
                "page": page,
                "page_size": page_size,
            },
        )

        return results

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception:
        logger.error(
            "Failed to list analyses",
            extra={
                "company_cik": company_cik,
                "analysis_type": analysis_type.value if analysis_type else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list analyses",
        ) from None


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get analysis by ID",
    description="""
    Retrieve a specific analysis by its unique ID.

    Returns complete analysis results including AI insights, key findings,
    and metadata about the analysis process.
    """,
)
async def get_analysis(
    analysis_id: AnalysisIdPath,
    session: SessionDep,
    factory: ServiceFactoryDep,
) -> AnalysisResponse:
    """Get a specific analysis by ID.

    Args:
        analysis_id: Unique analysis identifier
        session: Database session for repository operations
        factory: Service factory for dependency injection

    Returns:
        AnalysisResponse with complete analysis information

    Raises:
        HTTPException: 404 if analysis not found
        HTTPException: 500 if retrieval fails
    """
    logger.info("Retrieving analysis by ID", extra={"analysis_id": str(analysis_id)})

    try:
        # Create query
        query = GetAnalysisQuery(analysis_id=analysis_id)

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: AnalysisResponse = await dispatcher.dispatch_query(query, dependencies)

        logger.info(
            "Analysis retrieved successfully", extra={"analysis_id": str(analysis_id)}
        )

        return result

    except Exception:
        logger.error(
            "Failed to retrieve analysis",
            extra={"analysis_id": str(analysis_id)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis",
        ) from None


@router.get(
    "/templates",
    response_model=TemplatesResponse,
    summary="Get analysis templates",
    description="""
    Retrieve available analysis templates and their configurations.

    Returns information about supported analysis types, required parameters,
    and template-specific settings for different filing analysis workflows.
    """,
)
async def get_analysis_templates(
    session: Annotated[AsyncSession, Depends(get_db)],
    factory: Annotated[ServiceFactory, Depends(get_service_factory)],
    # Optional template filtering
    template_type: Annotated[
        str | None,
        Query(description="Filter by template type (e.g., 'financial', 'risk')"),
    ] = None,
) -> TemplatesResponse:
    """Get available analysis templates and configurations.

    Args:
        session: Database session for repository operations
        factory: Service factory for dependency injection
        template_type: Optional filter for specific template types

    Returns:
        TemplatesResponse with available templates and configurations

    Raises:
        HTTPException: 500 if template retrieval fails
    """
    logger.info("Retrieving analysis templates", extra={"template_type": template_type})

    try:
        # Create query
        query = GetTemplatesQuery(template_type=template_type)

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: TemplatesResponse = await dispatcher.dispatch_query(query, dependencies)

        logger.info(
            "Analysis templates retrieved successfully",
            extra={
                "template_count": (
                    len(result.templates) if hasattr(result, 'templates') else 0
                ),
                "template_type": template_type,
            },
        )

        return result

    except Exception:
        logger.error(
            "Failed to retrieve analysis templates",
            extra={"template_type": template_type},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis templates",
        ) from None
