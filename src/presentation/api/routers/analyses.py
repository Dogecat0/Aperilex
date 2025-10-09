"""API router for analysis-related endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

from src.application.handlers.schemas.queries import (
    GetAnalysisQuery,
    GetTemplatesQuery,
    ListAnalysesQuery,
)
from src.application.handlers.schemas.queries.list_analyses import (
    AnalysisSegment,
    AnalysisSortField,
    SortDirection,
)
from src.application.handlers.schemas.responses import (
    AnalysesListResponse,
    AnalysisResponse,
    TemplatesResponse,
)
from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.application_service import ApplicationService
from src.presentation.api.dependencies import get_application_service
from src.presentation.api.security import get_current_user, user_id_str
from src.shared.enums import AnalysisStatus
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
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]
if TYPE_CHECKING:
    ApplicationServiceDep = ApplicationService
else:
    ApplicationServiceDep = Annotated[Any, Depends(get_application_service)]


class AnalysesListParams(BaseModel):
    """Normalized query parameters for the analyses list endpoint."""

    search: str | None = Field(
        default=None,
        description="Full-text search input",
    )
    segment: AnalysisSegment = Field(
        default=AnalysisSegment.ALL,
        description="Dashboard segment filter",
    )
    statuses: list[AnalysisStatus] | None = Field(
        default=None,
        description="Comma-separated analysis statuses",
    )
    created_after: datetime | None = Field(
        default=None,
        description="Filter analyses created after this timestamp",
    )
    created_before: datetime | None = Field(
        default=None,
        description="Filter analyses created before this timestamp",
    )
    created_by: str | None = Field(
        default=None,
        description="Restrict analyses to those created by the supplied identifier",
    )
    sort: AnalysisSortField = Field(
        default=AnalysisSortField.CREATED_AT,
        description="Field used for sorting",
    )
    direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sorting direction",
    )
    page: int = Field(default=1, ge=1, description="Requested page number")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of analyses per page (max 100)",
    )

    @field_validator("search", mode="before")
    @classmethod
    def _normalize_search(cls, raw: str | None) -> str | None:
        if raw is None:
            return None
        normalized = raw.strip()
        if not normalized:
            return None
        return normalized[:128]

    @field_validator("created_by", mode="before")
    @classmethod
    def _normalize_created_by(cls, raw: str | None) -> str | None:
        if raw is None:
            return None
        normalized = raw.strip()
        return normalized or None

    @field_validator("statuses", mode="before")
    @classmethod
    def _split_statuses(cls, raw: list[str] | str | None) -> list[str] | None:
        if raw is None:
            return None
        if isinstance(raw, list):
            return raw or None
        tokens = [token.strip() for token in raw.split(",")]
        values = [token for token in tokens if token]
        return values or None

    @field_validator("statuses")
    @classmethod
    def _dedupe_statuses(
        cls, statuses: list[AnalysisStatus] | None
    ) -> list[AnalysisStatus] | None:
        if statuses is None:
            return None
        unique: list[AnalysisStatus] = []
        seen: set[AnalysisStatus] = set()
        for analysis_status in statuses:
            if analysis_status not in seen:
                unique.append(analysis_status)
                seen.add(analysis_status)
        return unique or None

    @model_validator(mode="after")
    def _validate_chronology(self) -> AnalysesListParams:
        if (
            self.created_after
            and self.created_before
            and self.created_after > self.created_before
        ):
            raise ValueError("created_after cannot be later than created_before")
        return self

    @classmethod
    def as_dependency(
        cls,
        search: Annotated[
            str | None, Query(description="Full-text search term")
        ] = None,
        segment: Annotated[
            AnalysisSegment,
            Query(description="Segment filter", alias="segment"),
        ] = AnalysisSegment.ALL,
        status: Annotated[
            list[str] | str | None,
            Query(
                description="Comma-separated list of analysis statuses",
                alias="status",
            ),
        ] = None,
        created_after: Annotated[
            datetime | None, Query(description="Created after timestamp")
        ] = None,
        created_before: Annotated[
            datetime | None, Query(description="Created before timestamp")
        ] = None,
        created_by: Annotated[
            str | None, Query(description="Filter by analysis creator")
        ] = None,
        sort: Annotated[
            AnalysisSortField,
            Query(description="Sort field", alias="sort"),
        ] = AnalysisSortField.CREATED_AT,
        direction: Annotated[
            SortDirection,
            Query(description="Sort direction", alias="direction"),
        ] = SortDirection.DESC,
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int,
            Query(ge=1, le=100, description="Number of results per page (max 100)"),
        ] = 20,
    ) -> AnalysesListParams:
        payload: dict[str, Any] = {
            "search": search,
            "segment": segment,
            "statuses": status,
            "created_after": created_after,
            "created_before": created_before,
            "created_by": created_by,
            "sort": sort,
            "direction": direction,
            "page": page,
            "page_size": page_size,
        }
        return cls.model_validate(payload)

    def to_query(
        self,
        *,
        user_id: str | None,
        company_cik: CIK | None = None,
    ) -> ListAnalysesQuery:
        return ListAnalysesQuery(
            user_id=user_id,
            company_cik=company_cik,
            search=self.search,
            segment=self.segment,
            statuses=self.statuses,
            created_after=self.created_after,
            created_before=self.created_before,
            created_by=self.created_by,
            sort_by=self.sort,
            sort_direction=self.direction,
            page=self.page,
            page_size=self.page_size,
        )


ListParamsDep = Annotated[AnalysesListParams, Depends(AnalysesListParams.as_dependency)]


@router.get(
    "",
    response_model=AnalysesListResponse,
    summary="List analyses",
    description="""
    List analyses with rich filtering, pagination, and sorting.

    Supports full-text search, dashboard segments, lifecycle status filters,
    creator scoping, and server-side sorting by key metrics.
    """,
)
async def list_analyses(
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    params: ListParamsDep,
) -> AnalysesListResponse:
    """List analyses with filtering and pagination."""
    logger.info(
        "Listing analyses",
        extra={
            "search": params.search,
            "segment": params.segment.value,
            "statuses": (
                [status.value for status in params.statuses]
                if params.statuses
                else None
            ),
            "created_after": (
                params.created_after.isoformat() if params.created_after else None
            ),
            "created_before": (
                params.created_before.isoformat() if params.created_before else None
            ),
            "created_by": params.created_by,
            "sort": params.sort.value,
            "direction": params.direction.value,
            "page": params.page,
            "page_size": params.page_size,
        },
    )

    try:
        if not current_user.authenticated or current_user.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated user context required to list analyses",
            )

        query = params.to_query(user_id=user_id_str(current_user))

        results_obj = await application_service.execute_query(query)
        if not isinstance(results_obj, AnalysesListResponse):
            logger.error(
                "Unexpected response type when listing analyses",
                extra={
                    "returned_type": type(results_obj).__name__,
                    "expected_type": "AnalysesListResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        results = results_obj

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
        raise
    except Exception:
        logger.error(
            "Failed to list analyses",
            extra={
                "search": params.search,
                "segment": params.segment.value,
                "statuses": (
                    [status.value for status in params.statuses]
                    if params.statuses
                    else None
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
        result_obj = await application_service.execute_query(query)
        if not isinstance(result_obj, TemplatesResponse):
            logger.error(
                "Unexpected response type when retrieving templates",
                extra={
                    "returned_type": type(result_obj).__name__,
                    "expected_type": "TemplatesResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        result = result_obj

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
        result_obj = await application_service.execute_query(query)
        if not isinstance(result_obj, AnalysisResponse):
            logger.error(
                "Unexpected response type when retrieving analysis",
                extra={
                    "analysis_id": str(analysis_id),
                    "returned_type": type(result_obj).__name__,
                    "expected_type": "AnalysisResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        result = result_obj

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
