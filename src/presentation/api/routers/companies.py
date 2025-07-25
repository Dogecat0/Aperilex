"""API router for company-related endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.application.schemas.queries.get_company import GetCompanyQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.company_response import CompanyResponse
from src.domain.entities.analysis import AnalysisType
from src.infrastructure.database.base import get_db
from src.presentation.api.dependencies import get_service_factory

logger = logging.getLogger(__name__)

# Create router with appropriate prefix and tags
router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    responses={
        404: {"description": "Company not found"},
        422: {"description": "Invalid ticker format"},
        500: {"description": "Internal server error"},
    },
)

# Type aliases for dependencies
SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
TickerPath = Annotated[
    str, Path(description="Company ticker symbol (e.g., 'AAPL', 'MSFT')")
]


@router.get(
    "/{ticker}",
    response_model=CompanyResponse,
    summary="Get company information",
    description="""
    Retrieve comprehensive information about a company by ticker symbol.

    Returns company profile including basic information, industry classification,
    address, and optional enrichments like recent Aperilex analysis summaries.
    Data is combined from local database and live SEC EDGAR sources.
    """,
)
async def get_company(
    ticker: TickerPath,
    session: SessionDep,
    factory: ServiceFactoryDep,
    # Enrichment options
    include_recent_analyses: Annotated[
        bool, Query(description="Include recent Aperilex analysis summaries")
    ] = False,
) -> CompanyResponse:
    """Get comprehensive company information by ticker.

    Args:
        ticker: Company ticker symbol (case-insensitive)
        session: Database session for repository operations
        factory: Service factory for dependency injection
        include_recent_analyses: Whether to include recent analysis summaries

    Returns:
        CompanyResponse with comprehensive company information

    Raises:
        HTTPException: 422 if ticker format is invalid
        HTTPException: 404 if company not found
        HTTPException: 500 if company retrieval fails
    """
    logger.info(
        "Retrieving company information",
        extra={
            "ticker": ticker,
            "include_recent_analyses": include_recent_analyses,
        },
    )

    try:
        # Normalize ticker to uppercase
        ticker_normalized = ticker.upper().strip()

        # Basic validation
        if not ticker_normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ticker cannot be empty",
            )

        if not ticker_normalized.replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ticker must contain only alphanumeric characters and hyphens",
            )

        # Create query with enrichment options
        query = GetCompanyQuery(
            ticker=ticker_normalized,
            include_recent_analyses=include_recent_analyses,
        )

        # Get dependencies and dispatcher
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        # Dispatch query
        result: CompanyResponse = await dispatcher.dispatch_query(query, dependencies)

        logger.info(
            "Company information retrieved successfully",
            extra={
                "ticker": ticker,
                "company_id": str(result.company_id),
                "cik": result.cik,
            },
        )

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(
            "Invalid ticker format", extra={"ticker": ticker, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ticker format: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to retrieve company information",
            extra={"ticker": ticker},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company information",
        ) from None


@router.get(
    "/{ticker}/analyses",
    response_model=list[AnalysisResponse],
    summary="List company analyses",
    description="""
    List all analyses for a specific company, filtered by ticker symbol.

    Returns analyses ordered by creation date (newest first) with optional
    filtering by analysis type, confidence score, and pagination support.
    """,
)
async def list_company_analyses(
    ticker: TickerPath,
    session: SessionDep,
    factory: ServiceFactoryDep,
    # Filtering parameters
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
    """List all analyses for a specific company.

    Args:
        ticker: Company ticker symbol (case-insensitive)
        session: Database session for repository operations
        factory: Service factory for dependency injection
        analysis_type: Optional analysis type filter
        min_confidence: Optional minimum confidence score filter
        page: Page number for pagination (1-based)
        page_size: Number of results per page

    Returns:
        List of AnalysisResponse objects for the company

    Raises:
        HTTPException: 422 if ticker format is invalid
        HTTPException: 404 if company not found
        HTTPException: 500 if listing fails
    """
    logger.info(
        "Listing company analyses",
        extra={
            "ticker": ticker,
            "analysis_type": analysis_type.value if analysis_type else None,
            "min_confidence": min_confidence,
            "page": page,
            "page_size": page_size,
        },
    )

    try:
        # Normalize ticker
        ticker_normalized = ticker.upper().strip()

        # Basic validation
        if not ticker_normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ticker cannot be empty",
            )

        # First, we need to get the company to find its CIK
        # This is needed because ListAnalysesQuery filters by CIK, not ticker
        company_query = GetCompanyQuery(ticker=ticker_normalized)
        dispatcher = factory.create_dispatcher()
        dependencies = factory.get_handler_dependencies(session)

        try:
            company_info: CompanyResponse = await dispatcher.dispatch_query(
                company_query, dependencies
            )
            company_cik_str = company_info.cik
        except Exception as e:
            logger.warning(
                "Company not found for ticker",
                extra={"ticker": ticker, "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found",
            ) from e

        # Convert CIK string to CIK object for the analyses query
        from src.domain.value_objects.cik import CIK

        company_cik = CIK(company_cik_str)

        # Calculate offset for pagination
        (page - 1) * page_size

        # Create analyses list query filtered by company CIK
        # Convert single analysis_type to list for schema compatibility
        analysis_types = [analysis_type] if analysis_type else None

        analyses_query = ListAnalysesQuery(
            company_cik=company_cik,
            analysis_types=analysis_types,
            # Note: ListAnalysesQuery doesn't support min_confidence_score, offset, limit
            # These parameters need to be handled differently or the schema needs updating
        )

        # Dispatch analyses query
        results: list[AnalysisResponse] = await dispatcher.dispatch_query(
            analyses_query, dependencies
        )

        logger.info(
            "Company analyses listed successfully",
            extra={
                "ticker": ticker,
                "company_cik": company_cik_str,
                "results_count": len(results),
                "page": page,
                "page_size": page_size,
            },
        )

        return results

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(
            "Invalid ticker format", extra={"ticker": ticker, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ticker format: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to list company analyses", extra={"ticker": ticker}, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list company analyses",
        ) from None
