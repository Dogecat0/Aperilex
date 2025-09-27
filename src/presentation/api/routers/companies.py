"""API router for company-related endpoints."""

import logging
from typing import TYPE_CHECKING, Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.queries.list_company_filings import (
    ListCompanyFilingsQuery,
)
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysesListResponse,
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
from src.presentation.api.routers.analyses import AnalysesListParams
from src.presentation.api.security import get_current_user, user_id_str
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
if TYPE_CHECKING:
    ApplicationServiceDep = ApplicationService
else:
    ApplicationServiceDep = Annotated[Any, Depends(get_application_service)]
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]
TickerPath = Annotated[
    str, Path(description="Company ticker symbol (e.g., 'AAPL', 'MSFT')")
]
CompanyAnalysesParamsDep = Annotated[
    AnalysesListParams, Depends(AnalysesListParams.as_dependency)
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
    response_model=AnalysesListResponse,
    summary="List company analyses",
    description="""
    List all analyses for a specific company, filtered by ticker symbol.

    Exposes the same filtering contract as `/api/analyses` while
    implicitly scoping results to the selected company.
    """,
)
async def list_company_analyses(
    ticker: TickerPath,
    application_service: ApplicationServiceDep,
    current_user: AuthenticatedUserDep,
    params: CompanyAnalysesParamsDep,
) -> AnalysesListResponse:
    """List all analyses for a specific company."""
    logger.info(
        "Listing company analyses",
        extra={
            "ticker": ticker,
            "search": params.search,
            "segment": params.segment.value,
            "statuses": [status.value for status in params.statuses]
            if params.statuses
            else None,
            "page": params.page,
            "page_size": params.page_size,
        },
    )

    try:
        if not current_user.authenticated or current_user.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated user context required to list company analyses",
            )

        ticker_normalized = ticker.upper().strip()
        if not ticker_normalized:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Ticker cannot be empty",
            )

        company_query = GetCompanyQuery(
            ticker=ticker_normalized,
            user_id=user_id_str(current_user),
        )

        try:
            company_info_result = await application_service.execute_query(company_query)
        except Exception as exc:
            logger.warning(
                "Company not found for ticker",
                extra={"ticker": ticker, "error": str(exc)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found",
            ) from exc

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

        from src.shared.types import CIK  # Local import to avoid circulars during module load  # noqa: I001

        company_cik = CIK(value=company_info.cik)

        query = params.to_query(
            user_id=user_id_str(current_user),
            company_cik=company_cik,
        )

        results_obj = await application_service.execute_query(query)
        if not isinstance(results_obj, AnalysesListResponse):
            logger.error(
                "Unexpected response type when listing analyses",
                extra={
                    "ticker": ticker,
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
            "Company analyses listed successfully",
            extra={
                "ticker": ticker,
                "company_cik": company_info.cik,
                "results_count": results.pagination.total_items,
                "page": results.pagination.page,
                "page_size": results.pagination.page_size,
                "returned_count": len(results.items),
            },
        )

        return results

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Invalid ticker format", extra={"ticker": ticker, "error": str(exc)}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ticker format: {str(exc)}",
        ) from exc
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
