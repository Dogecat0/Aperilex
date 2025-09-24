"""API router for filing-related endpoints."""

import logging
from datetime import date
from typing import TYPE_CHECKING, Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.application.base.exceptions import ResourceNotFoundError
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.queries.get_filing import GetFilingQuery
from src.application.handlers.schemas.queries.list_company_filings import (
    FilingSortField as ListCompanyFilingSortField,
)
from src.application.handlers.schemas.queries.search_filings import (
    FilingSortField as SearchFilingSortField,
)
from src.application.handlers.schemas.queries.search_filings import (
    SearchFilingsQuery,
)
from src.application.handlers.schemas.queries.search_filings import (
    SortDirection as SearchSortDirection,
)
from src.application.handlers.schemas.responses import (
    AnalysisResponse,
    FilingResponse,
    FilingSearchResult,
    PaginatedResponse,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.application_service import ApplicationService
from src.presentation.api.dependencies import get_application_service
from src.presentation.api.security import get_current_user, user_id_str
from src.shared.enums import FilingType
from src.shared.types import CIK, AccessionNumber

logger = logging.getLogger(__name__)

# Create router with appropriate prefix and tags
router = APIRouter(
    prefix="/filings",
    tags=["filings"],
    responses={
        404: {"description": "Filing not found"},
        422: {"description": "Invalid accession number or filing ID format"},
        500: {"description": "Internal server error"},
    },
)


LIST_TO_SEARCH_SORT_FIELD_MAP: dict[
    ListCompanyFilingSortField, SearchFilingSortField
] = {
    ListCompanyFilingSortField.FILING_DATE: SearchFilingSortField.FILING_DATE,
    ListCompanyFilingSortField.FILING_TYPE: SearchFilingSortField.FILING_TYPE,
    ListCompanyFilingSortField.PROCESSING_STATUS: SearchFilingSortField.FILING_DATE,
    ListCompanyFilingSortField.CREATED_AT: SearchFilingSortField.FILING_DATE,
}

# Type aliases for dependencies
if TYPE_CHECKING:
    ApplicationServiceDep = ApplicationService
else:
    ApplicationServiceDep = Annotated[Any, Depends(get_application_service)]
AccessionNumberPath = Annotated[str, Path(description="SEC filing accession number")]
FilingIdPath = Annotated[UUID, Path(description="Filing UUID identifier")]
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]


@router.get(
    "/search",
    response_model=PaginatedResponse[FilingSearchResult],
    summary="Search SEC filings from database",
    description="""
    Search for SEC filings from the local database.

    This endpoint queries locally stored SEC filings that have been
    previously imported. It provides fast, reliable access to filing
    metadata without external API dependencies.

    Required parameter:
    - ticker: Company ticker symbol (e.g., "AAPL", "MSFT")

    Optional filters:
    - form_type: Specific filing type (e.g., "10-K", "10-Q", "8-K")
    - date_from: Start date for filing date range (YYYY-MM-DD)
    - date_to: End date for filing date range (YYYY-MM-DD)

    Pagination and sorting:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - sort_by: Sort field (filing_date, filing_type, company_name)
    - sort_direction: Sort direction (asc, desc)
    """,
)
async def search_filings(
    ticker: Annotated[str, Query(description="Company ticker symbol (required)")],
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    form_type: Annotated[
        str | None, Query(description="Filing type filter (e.g., 10-K, 10-Q)")
    ] = None,
    date_from: Annotated[
        date | None, Query(description="Start date for filing range (YYYY-MM-DD)")
    ] = None,
    date_to: Annotated[
        date | None, Query(description="End date for filing range (YYYY-MM-DD)")
    ] = None,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=100)] = 20,
    sort_by: Annotated[str, Query(description="Sort field")] = "filing_date",
    sort_direction: Annotated[str, Query(description="Sort direction")] = "desc",
) -> PaginatedResponse[FilingSearchResult]:
    """Search for SEC filings using various criteria.

    Args:
        ticker: Company ticker symbol (required)
        form_type: Optional filing type filter
        date_from: Optional start date for filing range
        date_to: Optional end date for filing range
        page: Page number for pagination
        page_size: Number of items per page
        sort_by: Field to sort results by
        sort_direction: Sort direction (asc/desc)

    Returns:
        PaginatedResponse[FilingSearchResult]: Paginated search results

    Raises:
        HTTPException: 422 if parameters are invalid
        HTTPException: 500 if search fails
    """
    logger.info(
        "Processing filing search request",
        extra={
            "ticker": ticker,
            "form_type": form_type,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "page": page,
            "page_size": page_size,
        },
    )

    try:
        # Parse form_type if provided
        filing_type_enum = None
        if form_type:
            try:
                filing_type_enum = FilingType(form_type.upper())
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid form_type: {form_type}. Must be one of: {', '.join([ft.value for ft in FilingType])}",
                ) from e

        # Parse sort parameters
        try:
            sort_by_enum = SearchFilingSortField(sort_by)
        except ValueError:
            try:
                list_sort_field = ListCompanyFilingSortField(sort_by)
            except ValueError as e:
                available_fields = sorted(
                    {
                        field.value
                        for field in (
                            list(ListCompanyFilingSortField)
                            + list(SearchFilingSortField)
                        )
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Invalid sort_by: "
                        f"{sort_by}. Must be one of: {', '.join(available_fields)}"
                    ),
                ) from e

            mapped_sort = LIST_TO_SEARCH_SORT_FIELD_MAP.get(list_sort_field)
            if mapped_sort is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(f"Unsupported sort_by for filing search: {sort_by}."),
                ) from None
            sort_by_enum = mapped_sort

        try:
            sort_direction_enum = SearchSortDirection(sort_direction)
        except ValueError as e:
            valid_directions = ", ".join(
                direction.value for direction in SearchSortDirection
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid sort_direction: {sort_direction}. "
                    f"Must be one of: {valid_directions}"
                ),
            ) from e

        # Create search query
        query = SearchFilingsQuery(
            ticker=ticker,
            form_type=filing_type_enum,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            sort_by=sort_by_enum,
            sort_direction=sort_direction_enum,
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result = cast(
            PaginatedResponse[FilingSearchResult],
            await application_service.execute_query(query),
        )

        logger.info(
            "Filing search completed successfully",
            extra={
                "ticker": ticker,
                "total_items": result.pagination.total_items,
                "page": result.pagination.page,
                "returned_items": len(result.items),
                "search_summary": query.search_summary,
            },
        )

        return result

    except HTTPException:
        # Let HTTPException pass through to FastAPI
        raise
    except ValueError as e:
        logger.warning(
            "Invalid search parameters",
            extra={"ticker": ticker, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid search parameters: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to search filings",
            extra={"ticker": ticker, "form_type": form_type},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search filings",
        ) from None


@router.post(
    "/by-id/{filing_id}/analyze",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start analysis of a filing by UUID",
    description="""
    Initiate background analysis of a specific SEC filing using its UUID.

    The analysis process runs asynchronously and returns a task ID for tracking progress.
    Use the task ID to check status and retrieve results when complete.
    """,
)
async def analyze_filing_by_id(
    filing_id: FilingIdPath,
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
) -> TaskResponse:
    """Analyze a specific SEC filing identified by UUID."""
    logger.info(
        "Starting filing analysis by ID", extra={"filing_id": str(filing_id)}
    )

    try:
        query = GetFilingQuery(
            filing_id=filing_id,
            include_analyses=False,
            include_content_metadata=False,
            user_id=user_id_str(current_user),
        )

        filing = cast(
            FilingResponse,
            await application_service.execute_query(query),
        )

        accession_number = AccessionNumber(value=filing.accession_number)
        company_cik = CIK(value=accession_number.get_cik())

        from src.shared.config.settings import Settings

        settings = Settings()
        if not settings.analysis_enabled:
            logger.info(
                "Analysis disabled in demo mode",
                extra={"filing_id": str(filing_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Analysis is disabled for demonstration purposes. "
                    "Try to view one of the complete analysis reports."
                ),
            )

        command = AnalyzeFilingCommand(
            accession_number=accession_number,
            company_cik=company_cik,
            user_id=user_id_str(current_user),
        )

        result = cast(
            TaskResponse,
            await application_service.execute_command(command),
        )

        logger.info(
            "Filing analysis initiated successfully by ID",
            extra={
                "filing_id": str(filing_id),
                "accession_number": filing.accession_number,
                "task_id": result.task_id,
            },
        )

        return result

    except ResourceNotFoundError as e:
        logger.info(
            "Filing not found for analysis",
            extra={"filing_id": str(filing_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filing with ID {filing_id} not found",
        ) from e
    except ValueError as e:
        logger.warning(
            "Invalid filing data for analysis",
            extra={"filing_id": str(filing_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception:
        logger.error(
            "Failed to analyze filing by ID",
            extra={"filing_id": str(filing_id)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate filing analysis",
        ) from None


@router.get(
    "/by-id/{filing_id}",
    response_model=FilingResponse,
    summary="Get filing by UUID",
    description="""
    Retrieve detailed information about a specific SEC filing using its unique identifier.

    This endpoint retrieves filing information using the internal filing UUID,
    providing an alternative to accession-based lookup for maintaining domain separation.
    Returns filing metadata, processing status, and links to source documents.
    """,
)
async def get_filing_by_id(
    filing_id: FilingIdPath,
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
) -> FilingResponse:
    """Get information about a specific SEC filing by UUID.

    Args:
        filing_id: Filing UUID identifier

    Returns:
        FilingResponse with complete filing information

    Raises:
        HTTPException: 422 if filing_id format is invalid
        HTTPException: 404 if filing not found
        HTTPException: 500 if filing retrieval fails
    """
    logger.info(
        "Retrieving filing information by ID", extra={"filing_id": str(filing_id)}
    )

    try:
        # Create query using GetFilingQuery
        query = GetFilingQuery(
            filing_id=filing_id,
            include_analyses=True,  # Include analysis count for enriched response
            include_content_metadata=True,
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result = cast(
            FilingResponse,
            await application_service.execute_query(query),
        )

        logger.info(
            "Filing retrieved successfully by ID",
            extra={
                "filing_id": str(filing_id),
                "accession_number": result.accession_number,
                "filing_type": result.filing_type,
                "processing_status": result.processing_status,
            },
        )

        return result

    except ResourceNotFoundError as e:
        logger.info(
            "Filing not found",
            extra={"filing_id": str(filing_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filing with ID {filing_id} not found",
        ) from e
    except ValueError as e:
        logger.info(
            "Filing not found",
            extra={"filing_id": str(filing_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception:
        logger.error(
            "Failed to retrieve filing information by ID",
            extra={"filing_id": str(filing_id)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve filing information",
        ) from None


@router.get(
    "/{accession_number}",
    response_model=FilingResponse,
    summary="Get filing information",
    description="""
    Retrieve detailed information about a specific SEC filing.

    Returns filing metadata, processing status, and links to source documents.
    """,
)
async def get_filing(
    accession_number: AccessionNumberPath,
    application_service: ApplicationServiceDep,  # noqa: ARG001 - for DI parity
    current_user: AuthenticatedUserDep,  # noqa: ARG001 - for DI parity
) -> FilingResponse:
    """Deprecated accession-based filing lookup."""
    logger.info(
        "Deprecated accession-based filing lookup attempted",
        extra={"accession_number": accession_number},
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "Retrieving filings by accession number is no longer supported. "
            "Use /filings/by-id/{filing_id} instead."
        ),
    )


@router.get(
    "/{accession_number}/analysis",
    response_model=AnalysisResponse,
    summary="Get filing analysis results",
    description="""
    Retrieve analysis results for a specific SEC filing.

    Returns the most recent completed analysis for the filing, including
    AI-generated insights, key findings, and confidence scores.
    """,
)
async def get_filing_analysis(
    accession_number: AccessionNumberPath,
    application_service: ApplicationServiceDep,  # noqa: ARG001 - for DI parity
    current_user: AuthenticatedUserDep,  # noqa: ARG001 - for DI parity
) -> AnalysisResponse:
    """Deprecated accession-based analysis lookup."""
    logger.info(
        "Deprecated accession-based analysis lookup attempted",
        extra={"accession_number": accession_number},
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "Retrieving analyses by accession number is no longer supported. "
            "Use /analyses/{analysis_id} or /filings/by-id/{filing_id}/analysis instead."
        ),
    )
