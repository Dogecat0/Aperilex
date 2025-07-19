"""Background tasks for filing analysis using LLM providers."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import Task

from src.domain.entities.analysis import Analysis, AnalysisType
from src.infrastructure.database.base import get_session
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task class that supports async operations."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Run the task with async support."""
        if asyncio.iscoroutinefunction(self.run):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.run(*args, **kwargs))
            finally:
                loop.close()
        else:
            return self.run(*args, **kwargs)


@celery_app.task(bind=True, base=AsyncTask, name="analyze_filing")
async def analyze_filing_task(
    self: AsyncTask,
    filing_id: str,
    analysis_type: str,
    created_by: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4",
) -> dict[str, Any]:
    """
    Analyze a filing using the specified LLM provider.

    Args:
        filing_id: UUID of the filing to analyze
        analysis_type: Type of analysis to perform
        created_by: Identifier of user/system creating the analysis
        llm_provider: LLM provider to use (default: openai)
        llm_model: Specific model to use

    Returns:
        Task result with analysis information
    """
    task_id = self.request.id
    filing_uuid = UUID(filing_id)
    logger.info(
        f"Starting analysis task {task_id} for filing {filing_id}, "
        f"type: {analysis_type}, provider: {llm_provider}"
    )

    try:
        async with get_session() as session:
            filing_repo = FilingRepository(session)
            analysis_repo = AnalysisRepository(session)

            # Get filing
            filing = await filing_repo.get_by_id(filing_uuid)
            if not filing:
                raise ValueError(f"Filing {filing_id} not found")

            # Check if analysis already exists
            existing_analysis = await analysis_repo.get_latest_analysis_for_filing(
                filing_uuid, AnalysisType(analysis_type)
            )
            if existing_analysis:
                logger.info(
                    f"Analysis already exists for filing {filing_id}, "
                    f"type {analysis_type}"
                )
                return {
                    "task_id": task_id,
                    "filing_id": filing_id,
                    "analysis_id": str(existing_analysis.id),
                    "status": "already_exists",
                    "confidence_score": existing_analysis.confidence_score,
                }

            # Initialize LLM provider
            if llm_provider == "openai":
                provider = OpenAIProvider()
            else:
                raise ValueError(f"Unsupported LLM provider: {llm_provider}")

            # Get filing content from metadata
            filing_text = filing.metadata.get("text", "")
            if not filing_text:
                raise ValueError(f"No text content found for filing {filing_id}")

            # Perform analysis based on type
            analysis_results = await _perform_analysis(
                provider, analysis_type, filing_text, llm_model
            )

            # Create analysis entity
            analysis = Analysis.create(
                filing_id=filing_uuid,
                analysis_type=AnalysisType(analysis_type),
                created_by=created_by,
                results=analysis_results["results"],
                llm_provider=llm_provider,
                llm_model=llm_model,
                confidence_score=analysis_results.get("confidence_score"),
                metadata=analysis_results.get("metadata", {}),
            )

            # Save analysis
            await analysis_repo.create(analysis)
            await analysis_repo.commit()

            result = {
                "task_id": task_id,
                "filing_id": filing_id,
                "analysis_id": str(analysis.id),
                "analysis_type": analysis_type,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "confidence_score": analysis.confidence_score,
                "status": "completed",
            }

            logger.info(
                f"Completed analysis for filing {filing.accession_number}, "
                f"type: {analysis_type}, confidence: {analysis.confidence_score}"
            )

            return result

    except Exception as e:
        logger.error(f"Analysis task {task_id} failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "filing_id": filing_id,
            "analysis_type": analysis_type,
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(bind=True, base=AsyncTask, name="analyze_filing_comprehensive")
async def analyze_filing_comprehensive_task(
    self: AsyncTask,
    filing_id: str,
    created_by: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4",
) -> dict[str, Any]:
    """
    Perform comprehensive analysis on a filing using multiple analysis types.

    Args:
        filing_id: UUID of the filing to analyze
        created_by: Identifier of user/system creating the analysis
        llm_provider: LLM provider to use
        llm_model: Specific model to use

    Returns:
        Task result with all analysis information
    """
    task_id = self.request.id
    logger.info(
        f"Starting comprehensive analysis task {task_id} for filing {filing_id}"
    )

    try:
        # Define analysis types to perform
        analysis_types = [
            "risk_factors",
            "business_overview",
            "financial_highlights",
            "mda_analysis",
        ]

        # Queue individual analysis tasks
        analysis_tasks = []
        for analysis_type in analysis_types:
            task = analyze_filing_task.delay(
                filing_id=filing_id,
                analysis_type=analysis_type,
                created_by=created_by,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            analysis_tasks.append({"analysis_type": analysis_type, "task_id": task.id})

        result = {
            "task_id": task_id,
            "filing_id": filing_id,
            "status": "queued",
            "analysis_tasks": analysis_tasks,
            "total_analyses": len(analysis_types),
        }

        logger.info(
            f"Queued {len(analysis_types)} analysis tasks for filing {filing_id}"
        )

        return result

    except Exception as e:
        logger.error(
            f"Comprehensive analysis task {task_id} failed: {str(e)}", exc_info=True
        )
        return {
            "task_id": task_id,
            "filing_id": filing_id,
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(bind=True, base=AsyncTask, name="batch_analyze_filings")
async def batch_analyze_filings_task(
    self: AsyncTask,
    company_cik: str,
    analysis_type: str,
    created_by: str,
    limit: int = 10,
    llm_provider: str = "openai",
) -> dict[str, Any]:
    """
    Perform batch analysis on recent filings for a company.

    Args:
        company_cik: Company CIK to analyze filings for
        analysis_type: Type of analysis to perform
        created_by: Identifier of user/system creating the analysis
        limit: Maximum number of filings to analyze
        llm_provider: LLM provider to use

    Returns:
        Task result with batch analysis summary
    """
    task_id = self.request.id
    logger.info(
        f"Starting batch analysis task {task_id} for company {company_cik}, "
        f"type: {analysis_type}, limit: {limit}"
    )

    try:
        async with get_session() as session:
            filing_repo = FilingRepository(session)

            # Get recent filings for the company
            filings = await filing_repo.get_by_company_id(
                company_id=None, limit=limit  # We'll need to look up by CIK
            )

            if not filings:
                return {
                    "task_id": task_id,
                    "company_cik": company_cik,
                    "status": "completed",
                    "message": "No filings found for company",
                    "analyzed_count": 0,
                }

            # Queue analysis tasks
            analysis_tasks = []
            for filing in filings:
                task = analyze_filing_task.delay(
                    filing_id=str(filing.id),
                    analysis_type=analysis_type,
                    created_by=created_by,
                    llm_provider=llm_provider,
                )
                analysis_tasks.append(
                    {
                        "filing_id": str(filing.id),
                        "accession_number": str(filing.accession_number),
                        "task_id": task.id,
                    }
                )

            result = {
                "task_id": task_id,
                "company_cik": company_cik,
                "analysis_type": analysis_type,
                "status": "queued",
                "filings_found": len(filings),
                "analysis_tasks": analysis_tasks,
            }

            logger.info(
                f"Queued {len(analysis_tasks)} analysis tasks for company {company_cik}"
            )

            return result

    except Exception as e:
        logger.error(f"Batch analysis task {task_id} failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "company_cik": company_cik,
            "error": str(e),
            "status": "failed",
        }


async def _perform_analysis(
    provider: OpenAIProvider, analysis_type: str, text: str, model: str
) -> dict[str, Any]:
    """
    Perform the actual analysis using the LLM provider.

    Args:
        provider: LLM provider instance
        analysis_type: Type of analysis to perform
        text: Filing text content
        model: Model to use for analysis

    Returns:
        Analysis results including confidence score
    """
    if analysis_type == "risk_factors":
        return await provider.analyze_risk_factors(text, model)
    elif analysis_type == "business_overview":
        return await provider.analyze_business_overview(text, model)
    elif analysis_type == "financial_highlights":
        return await provider.analyze_financial_highlights(text, model)
    elif analysis_type == "mda_analysis":
        return await provider.analyze_mda(text, model)
    else:
        raise ValueError(f"Unsupported analysis type: {analysis_type}")
