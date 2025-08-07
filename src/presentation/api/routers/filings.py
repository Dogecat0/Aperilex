"""API router for filing-related endpoints."""

import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.queries.get_analysis_by_accession import (
    GetAnalysisByAccessionQuery,
)
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.get_filing_by_accession import (
    GetFilingByAccessionQuery,
)
from src.application.schemas.queries.search_filings import (
    FilingSortField,
    SearchFilingsQuery,
    SortDirection,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.application.schemas.responses.task_response import TaskResponse
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.infrastructure.database.base import get_db
from src.presentation.api.dependencies import get_service_factory

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

# Type aliases for dependencies
SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
AccessionNumberPath = Annotated[str, Path(description="SEC filing accession number")]
FilingIdPath = Annotated[UUID, Path(description="Filing UUID identifier")]


@router.get(
    "/search",
    response_model=PaginatedResponse[FilingSearchResult],
    summary="Search SEC filings",
    description="""
    Search for SEC filings using various criteria.

    This endpoint queries the SEC Edgar database directly to find filings
    matching the specified criteria. Results include filing metadata
    suitable for display in search interfaces.

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
    session: SessionDep,
    factory: ServiceFactoryDep,
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
        session: Database session for repository operations
        factory: Service factory for dependency injection
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
            sort_by_enum = FilingSortField(sort_by)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort_by: {sort_by}. Must be one of: {', '.join([sf.value for sf in FilingSortField])}",
            ) from e

        try:
            sort_direction_enum = SortDirection(sort_direction)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort_direction: {sort_direction}. Must be one of: {', '.join([sd.value for sd in SortDirection])}",
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
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: PaginatedResponse[FilingSearchResult] = await dispatcher.dispatch_query(
            query, dependencies
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
    "/{accession_number}/analyze",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start analysis of a filing",
    description="""
    Initiate background analysis of a specific SEC filing.

    The analysis process runs asynchronously and returns a task ID for tracking progress.
    Use the task ID to check status and retrieve results when complete.
    """,
)
async def analyze_filing(
    accession_number: AccessionNumberPath,
    session: SessionDep,
    factory: ServiceFactoryDep,
) -> TaskResponse:
    """Analyze a specific SEC filing.

    Args:
        accession_number: SEC filing accession number (e.g., "0000320193-23-000077")
        session: Database session for repository operations
        factory: Service factory for dependency injection

    Returns:
        TaskResponse with task_id for tracking analysis progress

    Raises:
        HTTPException: 422 if accession number format is invalid
        HTTPException: 404 if filing not found
        HTTPException: 500 if analysis initiation fails
    """
    logger.info(
        "Starting filing analysis", extra={"accession_number": accession_number}
    )

    try:
        # Validate accession number format
        accession_num = AccessionNumber(accession_number)

        # Extract CIK from accession number (first 10 digits)
        cik_str = accession_number.split('-')[0]
        # CIK expects string format, keep as string
        company_cik = CIK(cik_str)

        # Create command
        command = AnalyzeFilingCommand(
            accession_number=accession_num, company_cik=company_cik
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch command
        result: TaskResponse = await dispatcher.dispatch_command(command, dependencies)

        logger.info(
            "Filing analysis initiated successfully",
            extra={"accession_number": accession_number, "task_id": result.task_id},
        )

        return result

    except ValueError as e:
        logger.warning(
            "Invalid accession number format",
            extra={"accession_number": accession_number, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid accession number format: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to analyze filing",
            extra={"accession_number": accession_number},
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
    session: SessionDep,
    factory: ServiceFactoryDep,
) -> FilingResponse:
    """Get information about a specific SEC filing by UUID.

    Args:
        filing_id: Filing UUID identifier
        session: Database session for repository operations
        factory: Service factory for dependency injection

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
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: FilingResponse = await dispatcher.dispatch_query(query, dependencies)

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

    except ValueError as e:
        logger.warning(
            "Filing not found",
            extra={"filing_id": str(filing_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filing with ID {filing_id} not found",
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
    session: SessionDep,
    factory: ServiceFactoryDep,
) -> FilingResponse:
    """Get information about a specific SEC filing.

    Args:
        accession_number: SEC filing accession number (e.g., "0000320193-23-000077")
        session: Database session for repository operations
        factory: Service factory for dependency injection

    Returns:
        FilingResponse with complete filing information

    Raises:
        HTTPException: 422 if accession number format is invalid
        HTTPException: 404 if filing not found
        HTTPException: 500 if filing retrieval fails
    """
    logger.info(
        "Retrieving filing information", extra={"accession_number": accession_number}
    )

    try:
        # Validate accession number format
        accession_num = AccessionNumber(accession_number)

        # Create query using our new GetFilingByAccessionQuery
        query = GetFilingByAccessionQuery(
            accession_number=accession_num,
            include_analyses=True,  # Include analysis count for enriched response
            include_content_metadata=True,
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: FilingResponse = await dispatcher.dispatch_query(query, dependencies)

        logger.info(
            "Filing retrieved successfully",
            extra={
                "accession_number": accession_number,
                "filing_id": str(result.filing_id),
                "filing_type": result.filing_type,
                "processing_status": result.processing_status,
            },
        )

        return result

    except ValueError as e:
        logger.warning(
            "Invalid accession number format",
            extra={"accession_number": accession_number, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid accession number format: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to retrieve filing information",
            extra={"accession_number": accession_number},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve filing information",
        ) from None


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
    session: SessionDep,
    factory: ServiceFactoryDep,
) -> AnalysisResponse:
    """Get analysis results for a specific SEC filing.

    Args:
        accession_number: SEC filing accession number (e.g., "0000320193-23-000077")
        session: Database session for repository operations
        factory: Service factory for dependency injection

    Returns:
        AnalysisResponse with complete analysis results

    Raises:
        HTTPException: 422 if accession number format is invalid
        HTTPException: 404 if filing or analysis not found
        HTTPException: 500 if analysis retrieval fails
    """
    logger.info(
        "Retrieving filing analysis results",
        extra={"accession_number": accession_number},
    )

    try:
        # Validate accession number format
        accession_num = AccessionNumber(accession_number)

        # Create query using our new GetAnalysisByAccessionQuery
        query = GetAnalysisByAccessionQuery(
            accession_number=accession_num,
            include_full_results=True,
            include_section_details=False,
            include_processing_metadata=False,
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: AnalysisResponse = await dispatcher.dispatch_query(query, dependencies)

        logger.info(
            "Filing analysis retrieved successfully",
            extra={
                "accession_number": accession_number,
                "analysis_id": str(result.analysis_id),
                "analysis_type": result.analysis_type,
                "confidence_score": result.confidence_score,
            },
        )

        return result

    except ValueError as e:
        logger.warning(
            "Invalid accession number format",
            extra={"accession_number": accession_number, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid accession number format: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to retrieve filing analysis results",
            extra={"accession_number": accession_number},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve filing analysis results",
        ) from None
