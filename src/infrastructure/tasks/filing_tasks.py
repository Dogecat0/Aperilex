"""Background tasks for filing processing."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import Task

from src.domain.entities.filing import Filing
from src.infrastructure.database.base import async_session_maker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.company_repository import CompanyRepository
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


@celery_app.task(bind=True, base=AsyncTask, name="fetch_company_filings")
async def fetch_company_filings_task(
    self: AsyncTask, cik: str, form_types: list[str] | None = None, limit: int = 100
) -> dict[str, Any]:
    """
    Fetch and store SEC filings for a company.

    Args:
        cik: Company CIK identifier
        form_types: List of form types to fetch (e.g., ['10-K', '10-Q'])
        limit: Maximum number of filings to fetch

    Returns:
        Task result with summary information
    """
    task_id = self.request.id
    logger.info(f"Starting filing fetch task {task_id} for CIK {cik}")

    try:
        async with async_session_maker() as session:
            company_repo = CompanyRepository(session)
            filing_repo = FilingRepository(session)
            edgar_service = EdgarService()

            # Get or create company
            company = await company_repo.get_by_cik(cik)
            if not company:
                # Fetch company info from Edgar
                company_data = await edgar_service.get_company_info(cik)
                company = await company_repo.create(company_data)
                await company_repo.commit()
                logger.info(f"Created new company: {company.name} ({company.cik})")

            # Fetch filings from Edgar
            filing_data_list = await edgar_service.get_filings(
                cik=str(company.cik), form_types=form_types, limit=limit
            )

            created_count = 0
            updated_count = 0

            for filing_data in filing_data_list:
                # Check if filing already exists
                existing_filing = await filing_repo.get_by_accession_number(
                    filing_data.accession_number
                )

                if existing_filing:
                    updated_count += 1
                    logger.debug(
                        f"Filing {filing_data.accession_number} already exists"
                    )
                    continue

                # Create new filing
                filing = Filing.create(
                    company_id=company.id,
                    accession_number=filing_data.accession_number,
                    filing_type=filing_data.filing_type,
                    filing_date=filing_data.filing_date,
                    metadata=filing_data.metadata or {},
                )

                await filing_repo.create(filing)
                created_count += 1

                logger.debug(f"Created filing {filing_data.accession_number}")

            await filing_repo.commit()

            result = {
                "task_id": task_id,
                "cik": cik,
                "company_name": company.name,
                "total_filings_processed": len(filing_data_list),
                "created_count": created_count,
                "updated_count": updated_count,
                "status": "completed",
            }

            logger.info(
                f"Completed filing fetch for {company.name}: "
                f"{created_count} created, {updated_count} existing"
            )

            return result

    except Exception as e:
        logger.error(f"Filing fetch task {task_id} failed: {str(e)}", exc_info=True)
        return {"task_id": task_id, "cik": cik, "error": str(e), "status": "failed"}


@celery_app.task(bind=True, base=AsyncTask, name="process_filing")
async def process_filing_task(self: AsyncTask, filing_id: str) -> dict[str, Any]:
    """
    Process a single filing by extracting its content and sections.

    Args:
        filing_id: UUID of the filing to process

    Returns:
        Task result with processing status
    """
    task_id = self.request.id
    filing_uuid = UUID(filing_id)
    logger.info(f"Starting filing processing task {task_id} for filing {filing_id}")

    try:
        async with async_session_maker() as session:
            filing_repo = FilingRepository(session)
            edgar_service = EdgarService()

            # Get filing
            filing = await filing_repo.get_by_id(filing_uuid)
            if not filing:
                raise ValueError(f"Filing {filing_id} not found")

            # Mark as processing
            filing.mark_as_processing()
            await filing_repo.update(filing)
            await filing_repo.commit()

            # Extract filing content
            filing_content = await edgar_service.get_filing_content(
                str(filing.accession_number)
            )

            # Update filing with extracted content
            filing.metadata.update(
                {
                    "content_extracted": True,
                    "sections": filing_content.get("sections", {}),
                    "text_length": len(filing_content.get("text", "")),
                    "processing_completed_at": filing_content.get("processed_at"),
                }
            )

            # Mark as completed
            filing.mark_as_completed()
            await filing_repo.update(filing)
            await filing_repo.commit()

            result = {
                "task_id": task_id,
                "filing_id": filing_id,
                "accession_number": str(filing.accession_number),
                "status": "completed",
                "content_length": len(filing_content.get("text", "")),
                "sections_extracted": len(filing_content.get("sections", {})),
            }

            logger.info(f"Completed processing filing {filing.accession_number}")
            return result

    except Exception as e:
        logger.error(
            f"Filing processing task {task_id} failed: {str(e)}", exc_info=True
        )

        # Mark filing as failed if we can access it
        try:
            async with async_session_maker() as session:
                filing_repo = FilingRepository(session)
                filing = await filing_repo.get_by_id(filing_uuid)
                if filing:
                    filing.mark_as_failed(str(e))
                    await filing_repo.update(filing)
                    await filing_repo.commit()
        except Exception as repo_error:
            logger.error(f"Failed to update filing status: {str(repo_error)}")

        return {
            "task_id": task_id,
            "filing_id": filing_id,
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(bind=True, base=AsyncTask, name="process_pending_filings")
async def process_pending_filings_task(
    self: AsyncTask, limit: int = 50
) -> dict[str, Any]:
    """
    Process pending filings in batch.

    Args:
        limit: Maximum number of filings to process

    Returns:
        Task result with batch processing summary
    """
    task_id = self.request.id
    logger.info(f"Starting batch processing task {task_id} with limit {limit}")

    try:
        async with async_session_maker() as session:
            filing_repo = FilingRepository(session)

            # Get pending filings
            pending_filings = await filing_repo.get_pending_filings(limit)

            if not pending_filings:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "message": "No pending filings found",
                    "processed_count": 0,
                }

            # Queue individual processing tasks
            processing_tasks = []
            for filing in pending_filings:
                task = process_filing_task.delay(str(filing.id))
                processing_tasks.append(task.id)

            result = {
                "task_id": task_id,
                "status": "completed",
                "pending_filings_found": len(pending_filings),
                "processing_tasks_queued": len(processing_tasks),
                "task_ids": processing_tasks,
            }

            logger.info(f"Queued {len(processing_tasks)} filing processing tasks")

            return result

    except Exception as e:
        logger.error(f"Batch processing task {task_id} failed: {str(e)}", exc_info=True)
        return {"task_id": task_id, "error": str(e), "status": "failed"}
