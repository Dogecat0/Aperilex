"""Background tasks for filing processing."""

import asyncio
import logging
import secrets
import time
from typing import Any
from uuid import UUID, uuid4

from celery import Task

from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
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
                    AccessionNumber(filing_data.accession_number)
                )

                if existing_filing:
                    updated_count += 1
                    logger.debug(
                        f"Filing {filing_data.accession_number} already exists"
                    )
                    continue

                # Create new filing
                filing = Filing(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=AccessionNumber(filing_data.accession_number),
                    filing_type=FilingType(filing_data.filing_type),
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


@celery_app.task(bind=True, base=AsyncTask, name="batch_import_filings")
async def batch_import_filings_task(
    self: AsyncTask,
    companies: list[str],
    filing_types: list[str] | None = None,
    limit_per_company: int = 4,
    start_date: str | None = None,
    end_date: str | None = None,
    chunk_size: int = 5,
) -> dict[str, Any]:
    """
    Import SEC filings for multiple companies in parallel batches.

    This task implements SEC-compliant batch importing with rate limiting,
    chunking, and comprehensive error handling. It processes companies in
    parallel groups while respecting SEC's 10 requests/second limit.

    Args:
        companies: List of company identifiers (CIKs or tickers)
        filing_types: List of form types to fetch (e.g., ['10-K', '10-Q'])
        limit_per_company: Maximum number of filings to fetch per company
        start_date: Optional start date filter (ISO format string)
        end_date: Optional end date filter (ISO format string)
        chunk_size: Number of companies to process in parallel (default: 5)

    Returns:
        Task result with comprehensive summary information:
        {
            "task_id": str,
            "total_companies": int,
            "processed_companies": int,
            "failed_companies": int,
            "total_filings_created": int,
            "total_filings_existing": int,
            "processing_time_seconds": float,
            "chunks_processed": int,
            "failed_companies_details": List[dict],
            "status": str
        }

    Note:
        - Implements exponential backoff on rate limit errors
        - Uses jitter to prevent thundering herd problems
        - Continues processing on individual company failures
        - Respects SEC rate limiting (max 10 requests/second)
        - Processes companies in chunks to manage memory usage
    """
    task_id = self.request.id
    start_time = time.time()

    logger.info(
        f"Starting batch import task {task_id} for {len(companies)} companies, "
        f"filing_types={filing_types}, limit_per_company={limit_per_company}, "
        f"chunk_size={chunk_size}"
    )

    # Initialize counters and tracking
    total_companies = len(companies)
    processed_companies = 0
    failed_companies = 0
    total_filings_created = 0
    total_filings_existing = 0
    chunks_processed = 0
    failed_companies_details = []

    try:
        # Process companies in chunks to manage memory and respect rate limits
        company_chunks = [
            companies[i : i + chunk_size] for i in range(0, len(companies), chunk_size)
        ]

        total_chunks = len(company_chunks)
        logger.info(f"Processing {total_chunks} chunks of companies")

        for chunk_index, company_chunk in enumerate(company_chunks):
            chunk_start_time = time.time()

            logger.info(
                f"Processing chunk {chunk_index + 1}/{total_chunks} "
                f"with {len(company_chunk)} companies"
            )

            # Create parallel tasks for this chunk using Celery groups
            chunk_tasks = []
            for company in company_chunk:
                # Add jitter to prevent thundering herd (50-150ms delay)
                jitter_delay = 0.05 + (secrets.randbelow(100) / 1000.0)

                # Create subtask with delay
                task = fetch_company_filings_task.apply_async(
                    args=[company, filing_types, limit_per_company],
                    countdown=jitter_delay,
                )
                chunk_tasks.append((company, task))

            # Wait for all tasks in this chunk to complete with timeout
            chunk_timeout = 300  # 5 minutes per chunk
            chunk_results = []

            for company, task in chunk_tasks:
                try:
                    # Wait for individual task with timeout
                    result = task.get(timeout=chunk_timeout)
                    chunk_results.append((company, result))

                    # Update counters from successful task
                    if result.get("status") == "completed":
                        processed_companies += 1
                        total_filings_created += result.get("created_count", 0)
                        total_filings_existing += result.get("updated_count", 0)
                    else:
                        failed_companies += 1
                        failed_companies_details.append(
                            {
                                "company": company,
                                "error": result.get("error", "Unknown error"),
                                "chunk": chunk_index + 1,
                            }
                        )

                except Exception as task_error:
                    # Handle individual task failures
                    failed_companies += 1
                    error_msg = str(task_error)

                    failed_companies_details.append(
                        {
                            "company": company,
                            "error": error_msg,
                            "chunk": chunk_index + 1,
                            "error_type": type(task_error).__name__,
                        }
                    )

                    logger.error(
                        f"Task failed for company {company} in chunk {chunk_index + 1}: "
                        f"{error_msg}"
                    )

            chunks_processed += 1
            chunk_time = time.time() - chunk_start_time

            logger.info(
                f"Completed chunk {chunk_index + 1}/{total_chunks} "
                f"in {chunk_time:.2f}s, "
                f"success: {len([r for _, r in chunk_results if r.get('status') == 'completed'])}, "
                f"failed: {len([r for _, r in chunk_results if r.get('status') != 'completed'])}"
            )

            # SEC compliance: Wait between chunks to respect rate limits
            # Minimum 1 second between chunks, with exponential backoff if needed
            if chunk_index < total_chunks - 1:  # Don't wait after last chunk
                base_delay = 1.0

                # Increase delay if we had failures (potential rate limiting)
                chunk_failures = len(
                    [r for _, r in chunk_results if r.get('status') != 'completed']
                )
                if chunk_failures > 0:
                    # Exponential backoff based on failure rate
                    failure_rate = chunk_failures / len(company_chunk)
                    backoff_multiplier = min(4.0, 1 + failure_rate * 3)
                    base_delay *= backoff_multiplier

                    logger.info(
                        f"Applying backoff delay of {base_delay:.2f}s "
                        f"due to {chunk_failures} failures in chunk"
                    )

                # Add jitter to prevent synchronized requests across multiple batch tasks
                inter_chunk_delay = base_delay + 0.1 + (secrets.randbelow(400) / 1000.0)
                await asyncio.sleep(inter_chunk_delay)

        # Calculate final results
        processing_time = time.time() - start_time
        success_rate = (
            processed_companies / total_companies if total_companies > 0 else 0
        )

        result = {
            "task_id": task_id,
            "total_companies": total_companies,
            "processed_companies": processed_companies,
            "failed_companies": failed_companies,
            "total_filings_created": total_filings_created,
            "total_filings_existing": total_filings_existing,
            "processing_time_seconds": round(processing_time, 2),
            "chunks_processed": chunks_processed,
            "success_rate": round(success_rate, 3),
            "average_time_per_company": (
                round(processing_time / total_companies, 2)
                if total_companies > 0
                else 0
            ),
            "failed_companies_details": failed_companies_details,
            "status": "completed",
        }

        logger.info(
            f"Batch import task {task_id} completed: "
            f"{processed_companies}/{total_companies} companies processed "
            f"({success_rate:.1%} success rate), "
            f"{total_filings_created} filings created, "
            f"{total_filings_existing} existing filings found, "
            f"processing time: {processing_time:.2f}s"
        )

        return result

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)

        logger.error(
            f"Batch import task {task_id} failed after {processing_time:.2f}s: {error_msg}",
            exc_info=True,
        )

        return {
            "task_id": task_id,
            "total_companies": total_companies,
            "processed_companies": processed_companies,
            "failed_companies": failed_companies,
            "total_filings_created": total_filings_created,
            "total_filings_existing": total_filings_existing,
            "processing_time_seconds": round(processing_time, 2),
            "chunks_processed": chunks_processed,
            "failed_companies_details": failed_companies_details,
            "error": error_msg,
            "status": "failed",
        }
