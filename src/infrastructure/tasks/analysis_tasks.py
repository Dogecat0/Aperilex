"""Background tasks for filing analysis using LLM providers."""

import asyncio
import logging
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from celery import Task

from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.database.base import async_session_maker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm.base import BaseLLMProvider
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_llm_provider(llm_provider: str = "openai") -> BaseLLMProvider:
    """Get LLM provider instance.

    Args:
        llm_provider: Provider name (default: openai)

    Returns:
        LLM provider instance

    Raises:
        ValueError: If provider is not supported
    """
    if llm_provider == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")


class AsyncTask(Task):
    """Base task class that supports async operations."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Run the task with async support."""
        if asyncio.iscoroutinefunction(self.run):
            # Get or create event loop for async operations
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                return loop.run_until_complete(self.run(*args, **kwargs))
            finally:
                # Don't close the loop in case it's being reused
                if loop.is_running():
                    pass  # Loop is still running, don't close
                else:
                    # Only close if we created a new loop
                    try:
                        if not loop.is_closed():
                            loop.close()
                    except Exception as e:
                        logger.warning(
                            f"Error closing event loop during cleanup: {str(e)}"
                        )
        else:
            return self.run(*args, **kwargs)


@celery_app.task(bind=True, base=AsyncTask, name="analyze_filing")
async def analyze_filing_task(
    self: AsyncTask,
    filing_id: str,
    analysis_template: str,
    created_by: str,
    force_reprocess: bool = False,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4",
) -> dict[str, Any]:
    """
    Analyze a filing using the specified LLM provider.

    Args:
        filing_id: Accession number or UUID of the filing to analyze
        analysis_template: Analysis template to use (e.g., 'comprehensive', 'financial_focused')
        created_by: Identifier of user/system creating the analysis
        force_reprocess: Whether to reprocess even if analysis exists
        llm_provider: LLM provider to use (default: openai)
        llm_model: Specific model to use

    Returns:
        Task result with analysis information
    """
    task_id = self.request.id
    logger.info(
        f"Starting analysis task {task_id} for filing {filing_id}, "
        f"template: {analysis_template}, provider: {llm_provider}, "
        f"force_reprocess: {force_reprocess}"
    )

    # Create a fresh database session for this task
    session = None
    try:
        # Create session using the factory directly to avoid context manager issues
        session = async_session_maker()

        # Initialize repositories and services
        filing_repo = FilingRepository(session)
        analysis_repo = AnalysisRepository(session)
        edgar_service = EdgarService()
        llm_provider_instance = get_llm_provider(llm_provider)
        template_service = AnalysisTemplateService()

        # Parse filing_id to determine if it's UUID or accession number
        accession_number = None
        company_cik = None
        filing = None

        # Try to parse as UUID first
        try:
            filing_uuid = UUID(filing_id)
            filing = await filing_repo.get_by_id(filing_uuid)
            if filing:
                accession_number = filing.accession_number
                # Get company CIK from filing
                from src.infrastructure.repositories.company_repository import (
                    CompanyRepository,
                )

                company_repo = CompanyRepository(session)
                company = await company_repo.get_by_id(filing.company_id)
                if company:
                    company_cik = company.cik
        except ValueError:
            # Not a UUID, try as accession number
            try:
                accession_number = AccessionNumber(filing_id)
                # Try to find existing filing by accession number
                filing = await filing_repo.get_by_accession_number(accession_number)
                if filing:
                    from src.infrastructure.repositories.company_repository import (
                        CompanyRepository,
                    )

                    company_repo = CompanyRepository(session)
                    company = await company_repo.get_by_id(filing.company_id)
                    if company:
                        company_cik = company.cik
            except ValueError as e:
                raise ValueError(
                    f"Invalid filing identifier: {filing_id}. Must be accession number or valid UUID"
                ) from e

        # If we don't have company_cik yet, we need to get it from Edgar
        if not company_cik and accession_number:
            try:
                # Get filing data from Edgar to extract CIK
                filing_data = edgar_service.get_filing_by_accession(accession_number)
                company_cik = CIK(filing_data.cik)
                logger.info(
                    f"Retrieved company CIK {company_cik} from Edgar for filing {accession_number}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to get company CIK from Edgar for filing {filing_id}: {str(e)}"
                )
                raise ValueError(
                    f"Could not determine company CIK for filing {filing_id}"
                ) from e

        # Validate we have all required information
        if not accession_number:
            raise ValueError(
                f"Could not determine accession number from filing_id: {filing_id}"
            )
        if not company_cik:
            raise ValueError(
                f"Could not determine company CIK for filing_id: {filing_id}"
            )

        # Convert analysis_template string to enum
        try:
            template_enum = AnalysisTemplate(analysis_template)
        except ValueError as e:
            raise ValueError(f"Invalid analysis template: {analysis_template}") from e

        # Create command
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=template_enum,
            force_reprocess=force_reprocess,
            user_id=created_by,
        )

        # Create orchestrator
        orchestrator = AnalysisOrchestrator(
            analysis_repository=analysis_repo,
            filing_repository=filing_repo,
            edgar_service=edgar_service,
            llm_provider=llm_provider_instance,
            template_service=template_service,
        )

        # Execute analysis using orchestrator
        analysis = await orchestrator.orchestrate_filing_analysis(command)

        # Commit the session
        await session.commit()

        result = {
            "task_id": task_id,
            "filing_id": filing_id,
            "analysis_id": str(analysis.id),
            "analysis_template": analysis_template,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "confidence_score": analysis.confidence_score,
            "status": "completed",
        }

        logger.info(
            f"Completed analysis for filing {accession_number}, "
            f"template: {analysis_template}, confidence: {analysis.confidence_score}"
        )

        return result

    except Exception as e:
        # Rollback on error if session exists
        if session is not None:
            try:
                await session.rollback()
            except Exception as rollback_error:
                logger.warning(f"Error rolling back session: {rollback_error}")

        logger.error(f"Analysis task {task_id} failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "filing_id": filing_id,
            "analysis_template": analysis_template,
            "error": str(e),
            "status": "failed",
        }

    finally:
        # Ensure session is properly closed
        if session is not None:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")


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
        filing_id: Accession number or UUID of the filing to analyze
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
        # Use comprehensive template directly
        task = analyze_filing_task.delay(
            filing_id=filing_id,
            analysis_template=AnalysisTemplate.COMPREHENSIVE.value,
            created_by=created_by,
            force_reprocess=False,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

        analysis_tasks = [
            {
                "analysis_template": AnalysisTemplate.COMPREHENSIVE.value,
                "task_id": task.id,
            }
        ]

        result = {
            "task_id": task_id,
            "filing_id": filing_id,
            "status": "queued",
            "analysis_tasks": analysis_tasks,
            "total_analyses": len(analysis_tasks),
        }

        logger.info(
            f"Queued {len(analysis_tasks)} analysis task for filing {filing_id}"
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
    analysis_template: str,
    created_by: str,
    limit: int = 10,
    llm_provider: str = "openai",
) -> dict[str, Any]:
    """
    Perform batch analysis on recent filings for a company.

    Args:
        company_cik: Company CIK to analyze filings for
        analysis_template: Analysis template to use
        created_by: Identifier of user/system creating the analysis
        limit: Maximum number of filings to analyze
        llm_provider: LLM provider to use

    Returns:
        Task result with batch analysis summary
    """
    task_id = self.request.id
    logger.info(
        f"Starting batch analysis task {task_id} for company {company_cik}, "
        f"template: {analysis_template}, limit: {limit}"
    )

    # Create a fresh database session for this task
    session = None
    try:
        # Create session using the factory directly to avoid context manager issues
        session = async_session_maker()

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
                analysis_template=analysis_template,
                created_by=created_by,
                force_reprocess=False,
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
            "analysis_template": analysis_template,
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

    finally:
        # Ensure session is properly closed
        if session is not None:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")


async def _create_filing_from_edgar_data(session: Any, filing_data: Any) -> Filing:
    """Create filing entity from edgar service data.

    Args:
        session: Database session
        filing_data: Filing data from EdgarService

    Returns:
        Created Filing entity

    Raises:
        Exception: If filing creation fails
    """
    try:
        # Extract CIK from filing data
        cik = CIK(filing_data.cik)

        # Get or create company entity
        company_repo = CompanyRepository(session)
        company = await company_repo.get_by_cik(cik)

        if not company:
            # Create new company entity
            company_id = uuid4()
            company_metadata = {}

            # Add ticker to metadata if available
            if filing_data.ticker:
                company_metadata["ticker"] = filing_data.ticker

            company = Company(
                id=company_id,
                cik=cik,
                name=filing_data.company_name,
                metadata=company_metadata,
            )
            company = await company_repo.create(company)
            logger.info(f"Created new company: {company.name} [CIK: {cik}]")

        # Parse filing date
        filing_date_obj = date.fromisoformat(filing_data.filing_date.split('T')[0])

        # Create filing entity
        from src.domain.value_objects.accession_number import AccessionNumber

        filing = Filing(
            id=uuid4(),
            company_id=company.id,
            accession_number=AccessionNumber(filing_data.accession_number),
            filing_type=FilingType(filing_data.filing_type),
            filing_date=filing_date_obj,
            processing_status=ProcessingStatus.PENDING,
            metadata={
                "source": "edgar_service",
                "content_length": len(filing_data.content_text),
                "has_html": filing_data.raw_html is not None,
                "sections_count": len(filing_data.sections),
                "created_via": "celery_task",
                "text": filing_data.content_text,  # Store text content for analysis
            },
        )

        # Persist the filing
        filing_repo = FilingRepository(session)
        filing = await filing_repo.create(filing)

        logger.info(
            f"Created filing {filing.id} for {filing.filing_type} "
            f"[{filing.accession_number}] - Company: {company.name}"
        )

        return filing

    except Exception as e:
        logger.error(
            f"Failed to create filing from Edgar data: {str(e)}",
            extra={
                "accession_number": filing_data.accession_number,
                "company_name": filing_data.company_name,
                "filing_type": filing_data.filing_type,
            },
            exc_info=True,
        )
        raise
