"""API router for company-related endpoints."""

import logging
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.queries.list_analyses import (
    ListAnalysesQuery,
)
from src.application.handlers.schemas.queries.list_company_filings import (
    ListCompanyFilingsQuery,
)
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysisResponse,
)
from src.application.handlers.schemas.responses.company_response import (
    CompanyResponse,
)
from src.application.handlers.schemas.responses.filing_response import FilingResponse
from src.application.handlers.schemas.responses.paginated_response import (
    PaginatedResponse,
)
from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.application_service import ApplicationService
from src.presentation.api.dependencies import get_application_service
from src.presentation.api.security import get_current_user, user_id_str
from src.shared.enums.analysis import AnalysisType
from src.shared.enums.filing import FilingType

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
ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]
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
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    # Enrichment options
    include_recent_analyses: Annotated[
        bool, Query(description="Include recent Aperilex analysis summaries")
    ] = False,
) -> CompanyResponse:
    """Get comprehensive company information by ticker.

    Args:
        ticker: Company ticker symbol (case-insensitive)
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
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result_obj = await application_service.execute_query(query)
        if not isinstance(result_obj, CompanyResponse):
            logger.error(
                "Unexpected response type from application service",
                extra={
                    "ticker": ticker,
                    "returned_type": type(result_obj).__name__,
                    "expected_type": "CompanyResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        logger.info(
            "Company information retrieved successfully",
            extra={
                "ticker": ticker,
                "company_id": str(result_obj.company_id),
                "cik": result_obj.cik,
            },
        )

        return result_obj

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
    response_model=PaginatedResponse[AnalysisResponse],
    summary="List company analyses",
    description="""
    List all analyses for a specific company, filtered by ticker symbol.

    Returns analyses ordered by creation date (newest first) with optional
    filtering by analysis type, confidence score, and pagination support.
    """,
)
async def list_company_analyses(
    ticker: TickerPath,
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
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
) -> PaginatedResponse[AnalysisResponse]:
    """List all analyses for a specific company.

    Args:
        ticker: Company ticker symbol (case-insensitive)
        analysis_type: Optional analysis type filter
        min_confidence: Optional minimum confidence score filter
        page: Page number for pagination (1-based)
        page_size: Number of results per page

    Returns:
        PaginatedResponse containing AnalysisResponse objects for the company

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
        company_query = GetCompanyQuery(
            ticker=ticker_normalized,
            user_id=user_id_str(current_user),
        )

        try:
            company_info_result = await application_service.execute_query(
                company_query
            )
        except Exception as e:
            logger.warning(
                "Company not found for ticker",
                extra={"ticker": ticker, "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found",
            ) from e

        if not isinstance(company_info_result, CompanyResponse):
            logger.error(
                "Unexpected response type when resolving company",
                extra={
                    "ticker": ticker,
                    "returned_type": type(company_info_result).__name__,
                    "expected_type": "CompanyResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        company_info = company_info_result
        company_cik_str = company_info.cik

        # Convert CIK string to CIK object for the analyses query
        from src.shared.types import CIK

        company_cik = CIK(value=company_cik_str)

        # Create analyses list query filtered by company CIK
        # Convert single analysis_type to list for schema compatibility
        analysis_types = [analysis_type] if analysis_type else None

        analyses_query = ListAnalysesQuery(
            company_cik=company_cik,
            analysis_types=analysis_types,
            min_confidence_score=min_confidence,
            page=page,
            page_size=page_size,
            user_id=user_id_str(current_user),
        )

        # Dispatch analyses query
        results_obj = await application_service.execute_query(analyses_query)
        if not isinstance(results_obj, PaginatedResponse):
            logger.error(
                "Unexpected response type when listing analyses",
                extra={
                    "ticker": ticker,
                    "returned_type": type(results_obj).__name__,
                    "expected_type": "PaginatedResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        results = cast(PaginatedResponse[AnalysisResponse], results_obj)

        logger.info(
            "Company analyses listed successfully",
            extra={
                "ticker": ticker,
                "company_cik": company_cik_str,
                "results_count": results.pagination.total_items,
                "page": results.pagination.page,
                "page_size": results.pagination.page_size,
                "returned_count": len(results.items),
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


@router.get(
    "/{ticker}/filings",
    response_model=PaginatedResponse[FilingResponse] | list[FilingResponse],
    summary="List company filings",
    description="""
    List all filings for a specific company, filtered by ticker symbol.

    Returns filings ordered by filing date (newest first) with optional
    filtering by filing type, date range, and pagination support.

    If pagination parameters (page, page_size) are provided, returns a PaginatedResponse.
    Otherwise, returns a simple list of FilingResponse objects.
    """,
)
async def list_company_filings(
    ticker: TickerPath,
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    # Filtering parameters
    filing_type: Annotated[
        str | None,
        Query(description="Filter by filing type (e.g., '10-K', '10-Q', '8-K')"),
    ] = None,
    start_date: Annotated[
        str | None, Query(description="Filter filings from this date (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[
        str | None, Query(description="Filter filings to this date (YYYY-MM-DD)")
    ] = None,
    # Pagination parameters
    page: Annotated[
        int | None, Query(ge=1, description="Page number (1-based)")
    ] = None,
    page_size: Annotated[
        int | None,
        Query(ge=1, le=100, description="Number of filings per page (max 100)"),
    ] = None,
) -> PaginatedResponse[FilingResponse] | list[FilingResponse]:
    """List all filings for a specific company.

    Args:
        ticker: Company ticker symbol (case-insensitive)
        filing_type: Optional filing type filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        page: Page number for pagination (1-based)
        page_size: Number of results per page

    Returns:
        PaginatedResponse[FilingResponse] if pagination params provided,
        otherwise list[FilingResponse] for the company

    Raises:
        HTTPException: 422 if ticker format is invalid or date format is invalid
        HTTPException: 404 if company not found
        HTTPException: 500 if listing fails
    """
    logger.info(
        "Listing company filings",
        extra={
            "ticker": ticker,
            "filing_type": filing_type,
            "start_date": start_date,
            "end_date": end_date,
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

        # Validate and convert filing type if provided
        filing_type_obj = None
        if filing_type:
            try:
                filing_type_obj = FilingType(filing_type.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid filing type '{filing_type}'. Must be one of: {', '.join([ft.value for ft in FilingType])}",
                ) from None

        # Validate and convert dates if provided
        start_date_obj = None
        end_date_obj = None

        if start_date:
            try:
                from datetime import datetime

                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid start_date format. Use YYYY-MM-DD",
                ) from None

        if end_date:
            try:
                from datetime import datetime

                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid end_date format. Use YYYY-MM-DD",
                ) from None

        # Set default pagination if only one pagination param is provided
        if page is not None and page_size is None:
            page_size = 20
        elif page is None and page_size is not None:
            page = 1

        # Create query
        query = ListCompanyFilingsQuery(
            ticker=ticker_normalized,
            filing_type=filing_type_obj,
            start_date=start_date_obj,
            end_date=end_date_obj,
            page=page if page is not None else 1,
            page_size=page_size if page_size is not None else 20,
            user_id=user_id_str(current_user),
        )

        # Execute query through application service
        result_obj = await application_service.execute_query(query)
        if not isinstance(result_obj, PaginatedResponse):
            logger.error(
                "Unexpected response type when listing filings",
                extra={
                    "ticker": ticker,
                    "returned_type": type(result_obj).__name__,
                    "expected_type": "PaginatedResponse",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response type from application service",
            )

        result = cast(PaginatedResponse[FilingResponse], result_obj)

        # If pagination was requested, return paginated response
        if page is not None or page_size is not None:
            logger.info(
                "Company filings listed successfully (paginated)",
                extra={
                    "ticker": ticker,
                    "total_count": result.pagination.total_items,
                    "page": result.pagination.page,
                    "page_size": result.pagination.page_size,
                    "returned_count": len(result.items),
                },
            )
            return result

        # Otherwise, return just the items list
        logger.info(
            "Company filings listed successfully (list)",
            extra={
                "ticker": ticker,
                "returned_count": len(result.items),
            },
        )
        return result.items

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(
            "Invalid request parameters", extra={"ticker": ticker, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid parameters: {str(e)}",
        ) from e
    except Exception:
        logger.error(
            "Failed to list company filings",
            extra={"ticker": ticker},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list company filings",
        ) from None
