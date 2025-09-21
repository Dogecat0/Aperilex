"""API router for analysis-related endpoints."""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.handlers.schemas.queries import (
    GetAnalysisQuery,
    GetTemplatesQuery,
    ListAnalysesQuery,
)
from src.application.handlers.schemas.responses import (
    AnalysisResponse,
    PaginatedResponse,
    TemplatesResponse,
)
from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.application_service import ApplicationService
from src.domain.entities.analysis import AnalysisType
from src.presentation.api.dependencies import get_application_service
from src.presentation.api.security import get_current_user, user_id_str
from src.shared.types import CIK

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
AnalysisIdPath = Annotated[UUID, Path(description="Analysis ID")]
ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]


@router.get(
    "",
    response_model=PaginatedResponse[AnalysisResponse],
    summary="List analyses",
    description="""
    List analyses with optional filtering and pagination.

    Supports filtering by company CIK, analysis type, analysis template, date range, and confidence score.
    Results are ordered by creation date (newest first) and support pagination.

    Note: analysis_template and analysis_type filters can be used independently or together.
    """,
)
async def list_analyses(
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    # Filtering parameters
    company_cik: Annotated[
        str | None, Query(description="Filter by company CIK (e.g., '0000320193')")
    ] = None,
    analysis_type: Annotated[
        AnalysisType | None, Query(description="Filter by analysis type")
    ] = None,
    analysis_template: Annotated[
        AnalysisTemplate | None,
        Query(
            description="Filter by analysis template (comprehensive, financial_focused, risk_focused, business_focused)"
        ),
    ] = None,
    min_confidence_score: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Minimum confidence score (0.0-1.0)"),
    ] = None,
    created_from: Annotated[
        datetime | None, Query(description="Filter analyses created from this date")
    ] = None,
    created_to: Annotated[
        datetime | None, Query(description="Filter analyses created to this date")
    ] = None,
    # Pagination parameters
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of analyses per page (max 100)")
    ] = 20,
) -> PaginatedResponse[AnalysisResponse]:
    """List analyses with filtering and pagination.

    Args:
        company_cik: Optional CIK to filter by specific company
        analysis_type: Optional analysis type filter
        analysis_template: Optional analysis template filter
        min_confidence_score: Optional minimum confidence score filter
        created_from: Optional start date filter
        created_to: Optional end date filter
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
            "analysis_template": analysis_template.value if analysis_template else None,
            "min_confidence_score": min_confidence_score,
            "page": page,
            "page_size": page_size,
        },
    )

    try:
        # Validate and convert CIK if provided
        cik_obj = None
        if company_cik:
            try:
                cik_obj = CIK(value=company_cik)
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

        # Remove the hardcoded template mapping logic - let the query schema handle this

        query = ListAnalysesQuery(
            user_id=user_id_str(current_user),
            company_cik=cik_obj,
            analysis_types=analysis_types,
            analysis_template=analysis_template,
            created_from=created_from,
            created_to=created_to,
            min_confidence_score=min_confidence_score,
            page=page,
            page_size=page_size,
        )

        # Execute query through application service
        results: PaginatedResponse[
            AnalysisResponse
        ] = await application_service.execute_query(query)

        logger.info(
            "Listed analyses successfully",
            extra={
                "results_count": len(results.items),
                "page": results.pagination.page,
                "page_size": results.pagination.page_size,
                "total_items": results.pagination.total_items,
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
                "analysis_template": (
                    analysis_template.value if analysis_template else None
                ),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list analyses",
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
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    # Optional template filtering
    template_type: Annotated[
        str | None,
        Query(description="Filter by template type (e.g., 'financial', 'risk')"),
    ] = None,
) -> TemplatesResponse:
    """Get available analysis templates and configurations.

    Args:
        template_type: Optional filter for specific template types

    Returns:
        TemplatesResponse with available templates and configurations

    Raises:
        HTTPException: 500 if template retrieval fails
    """
    logger.info("Retrieving analysis templates", extra={"template_type": template_type})

    try:
        # Create query
        query = GetTemplatesQuery(
            template_type=template_type,
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result: TemplatesResponse = await application_service.execute_query(query)

        logger.info(
            "Analysis templates retrieved successfully",
            extra={
                "template_count": (
                    len(result.templates) if hasattr(result, "templates") else 0
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
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
) -> AnalysisResponse:
    """Get a specific analysis by ID.

    Args:
        analysis_id: Unique analysis identifier

    Returns:
        AnalysisResponse with complete analysis information

    Raises:
        HTTPException: 404 if analysis not found
        HTTPException: 500 if retrieval fails
    """
    logger.info("Retrieving analysis by ID", extra={"analysis_id": str(analysis_id)})

    try:
        # Create query
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result: AnalysisResponse = await application_service.execute_query(query)

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
