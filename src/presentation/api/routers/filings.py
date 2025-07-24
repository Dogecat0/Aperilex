"""API router for filing-related endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.queries.get_analysis_by_accession import (
    GetAnalysisByAccessionQuery,
)
from src.application.schemas.queries.get_filing_by_accession import (
    GetFilingByAccessionQuery,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.task_response import TaskResponse
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.infrastructure.database.base import get_db
from src.presentation.api.dependencies import get_service_factory

logger = logging.getLogger(__name__)

# Create router with appropriate prefix and tags
router = APIRouter(
    prefix="/filings",
    tags=["filings"],
    responses={
        404: {"description": "Filing not found"},
        422: {"description": "Invalid accession number format"},
        500: {"description": "Internal server error"},
    },
)

# Type aliases for dependencies
SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
AccessionNumberPath = Annotated[str, Path(description="SEC filing accession number")]


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
