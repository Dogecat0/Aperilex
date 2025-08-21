"""Background tasks for filing retrieval and analysis using LLM providers and new messaging system."""

import asyncio
import logging
import os
from typing import Any
from uuid import UUID, uuid4

from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.domain.entities.filing import Filing
from src.domain.value_objects import CIK
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.analysis_stage import AnalysisStage
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.database.base import async_session_maker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm import BaseLLMProvider, GoogleProvider, OpenAIProvider
from src.infrastructure.messaging import TaskPriority, task
from src.infrastructure.messaging.interfaces import IStorageService
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.shared.config.settings import Settings

logger = logging.getLogger(__name__)

# File storage configuration
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
MAX_CONCURRENT_FILING_DOWNLOADS = 1  # Limit to 1 concurrent download from EDGAR
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit for filing files

# Storage service (replaces direct file operations)
_local_storage_service: IStorageService | None = None


async def get_local_storage_service() -> IStorageService:
    """Get local storage service instance."""
    global _local_storage_service
    if _local_storage_service is None:
        from src.infrastructure.messaging.factory import (
            EnvironmentType,
            MessagingFactory,
        )

        _local_storage_service = MessagingFactory.create_storage_service(
            EnvironmentType.DEVELOPMENT
        )
        await _local_storage_service.connect()
    return _local_storage_service


def _validate_s3_configuration() -> None:
    """Validate S3 configuration when S3 storage is enabled.

    Raises:
        ValueError: If required S3 configuration is missing
    """
    if USE_S3_STORAGE:
        settings = Settings()
        if not settings.aws_s3_bucket:
            raise ValueError(
                "AWS_S3_BUCKET must be set when USE_S3_STORAGE=true. "
                "Check your environment configuration."
            )
        if not settings.aws_region:
            raise ValueError(
                "AWS_REGION must be set when USE_S3_STORAGE=true. "
                "Check your environment configuration."
            )
        logger.info(
            f"Using S3 storage: bucket={settings.aws_s3_bucket}, "
            f"region={settings.aws_region}"
        )
    else:
        logger.info("Using local storage service (development mode)")


async def get_filing_content(
    accession_number: AccessionNumber, company_cik: CIK
) -> dict[str, Any] | None:
    """Retrieve filing content from storage or download from EDGAR.

    Retrieval priority:
    1. Local file storage (development)
    2. AWS S3 storage (production)
    3. Download from EDGAR (with rate limiting)

    Args:
        accession_number: SEC accession number
        company_cik: Company CIK

    Returns:
        Filing content dictionary or None if not found
    """
    try:
        # Clean accession number for file path
        clean_accession = str(accession_number).replace("-", "")

        if USE_S3_STORAGE:
            # Production: Try S3 storage first
            try:
                from src.infrastructure.messaging.implementations.s3_storage import (
                    S3StorageService,
                )

                # Validate S3 configuration before creating service
                _validate_s3_configuration()

                settings = Settings()
                s3_service = S3StorageService(
                    bucket_name=settings.aws_s3_bucket,
                    aws_region=settings.aws_region,
                    prefix=f"filings/{company_cik}/",
                )
                await s3_service.connect()

                filing_content = await s3_service.get(clean_accession)
                if filing_content:
                    logger.info(f"Retrieved filing {accession_number} from S3 storage")
                    return filing_content  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning(f"Failed to retrieve from S3: {e}")
        else:
            # Development: Try local storage service first
            try:
                storage_service = await get_local_storage_service()
                filing_key = f"filing:{company_cik}/{clean_accession}"
                filing_content = await storage_service.get(filing_key)

                if filing_content:
                    logger.info(
                        f"Retrieved filing {accession_number} from local storage service"
                    )
                    return filing_content  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning(f"Failed to retrieve from local storage service: {e}")

        # If not in storage, download from EDGAR (with rate limiting)
        logger.info(
            f"Filing {accession_number} not found in storage, downloading from EDGAR"
        )

        # Use EdgarService to download filing
        edgar_service = EdgarService()

        # Get filing data
        filing_data = edgar_service.get_filing_by_accession(accession_number)

        if filing_data:
            # Prepare filing content for storage
            filing_content = {
                "accession_number": str(accession_number),
                "company_cik": str(company_cik),
                "filing_type": filing_data.filing_type,
                "filing_date": filing_data.filing_date,
                "company_name": filing_data.company_name,
                "ticker": filing_data.ticker,
                "content_text": filing_data.content_text,
                "sections": filing_data.sections,
                "raw_html": filing_data.raw_html,
                "metadata": {
                    "downloaded_at": asyncio.get_event_loop().time(),
                    "source": "edgar_service",
                },
            }

            # Store for future use - MUST succeed for data consistency
            storage_success = await store_filing_content(
                accession_number, company_cik, filing_content
            )

            if not storage_success:
                logger.error(
                    f"Failed to store filing {accession_number} to storage. "
                    f"Filing will not be available for future use."
                )
                # Still return the content for immediate use, but storage failed
                # This is acceptable as we can re-download from EDGAR if needed
            else:
                logger.info(f"Successfully stored filing {accession_number} to storage")

            return filing_content

        logger.error(f"Failed to download filing {accession_number} from EDGAR")
        return None

    except Exception as e:
        logger.error(f"Error retrieving filing content: {e}")
        return None


async def get_analysis_results(
    analysis_id: UUID, company_cik: CIK, accession_number: AccessionNumber
) -> dict[str, Any] | None:
    """Retrieve analysis results from storage.

    Args:
        analysis_id: Analysis ID
        company_cik: Company CIK for storage path
        accession_number: Accession number for storage path

    Returns:
        Analysis results dictionary or None if not found
    """
    try:
        # Create storage key for analysis results
        analysis_key = f"analysis_{analysis_id}"

        if USE_S3_STORAGE:
            # Production: Try S3 storage first
            try:
                from src.infrastructure.messaging.implementations.s3_storage import (
                    S3StorageService,
                )

                _validate_s3_configuration()
                settings = Settings()
                s3_service = S3StorageService(
                    bucket_name=settings.aws_s3_bucket,
                    aws_region=settings.aws_region,
                    prefix=f"analyses/{company_cik}/{accession_number.value.replace('-', '')}/",
                )
                await s3_service.connect()

                analysis_results = await s3_service.get(analysis_key)
                if analysis_results:
                    logger.debug(f"Retrieved analysis {analysis_id} from S3 storage")
                    return analysis_results  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning(f"Failed to retrieve analysis from S3: {e}")
        else:
            # Development: Try local storage service
            try:
                storage_service = await get_local_storage_service()
                clean_accession = accession_number.value.replace("-", "")
                analysis_storage_key = (
                    f"analysis:{company_cik}/{clean_accession}/{analysis_key}"
                )
                analysis_results = await storage_service.get(analysis_storage_key)

                if analysis_results:
                    logger.debug(
                        f"Retrieved analysis {analysis_id} from local storage service"
                    )
                    return analysis_results  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve analysis from local storage service: {e}"
                )

        return None

    except Exception as e:
        logger.error(f"Error retrieving analysis results: {e}")
        return None


async def store_analysis_results(
    analysis_id: UUID,
    company_cik: CIK,
    accession_number: AccessionNumber,
    analysis_results: dict[str, Any],
) -> bool:
    """Store analysis results to appropriate storage backend.

    Args:
        analysis_id: Analysis ID
        company_cik: Company CIK for storage path
        accession_number: Accession number for storage path
        analysis_results: Analysis results to store

    Returns:
        True if successfully stored, False otherwise
    """
    try:
        # Create storage key for analysis results
        analysis_key = f"analysis_{analysis_id}"

        if USE_S3_STORAGE:
            # Production: Store in S3
            try:
                from src.infrastructure.messaging.implementations.s3_storage import (
                    S3StorageService,
                )

                _validate_s3_configuration()
                settings = Settings()
                s3_service = S3StorageService(
                    bucket_name=settings.aws_s3_bucket,
                    aws_region=settings.aws_region,
                    prefix=f"analyses/{company_cik}/{accession_number.value.replace('-', '')}/",
                )
                await s3_service.connect()

                success = await s3_service.set(analysis_key, analysis_results)
                if success:
                    logger.info(f"Stored analysis {analysis_id} to S3 storage")
                return success
            except Exception as e:
                logger.error(f"Failed to store analysis to S3: {e}")
                return False
        else:
            # Development: Store in local storage service
            try:
                storage_service = await get_local_storage_service()
                clean_accession = accession_number.value.replace("-", "")
                analysis_storage_key = (
                    f"analysis:{company_cik}/{clean_accession}/{analysis_key}"
                )
                success = await storage_service.set(
                    analysis_storage_key, analysis_results
                )

                if success:
                    logger.info(
                        f"Stored analysis {analysis_id} to local storage service"
                    )
                return success
            except Exception as e:
                logger.error(f"Failed to store analysis to local storage service: {e}")
                return False

    except Exception as e:
        logger.error(f"Error storing analysis results: {e}")
        return False


async def store_filing_content(
    accession_number: AccessionNumber,
    company_cik: CIK,
    filing_content: dict[str, Any],
) -> bool:
    """Store filing content to appropriate storage backend.

    Args:
        accession_number: SEC accession number
        company_cik: Company CIK
        filing_content: Filing content to store

    Returns:
        True if successfully stored, False otherwise
    """
    try:
        # Clean accession number for file path
        clean_accession = str(accession_number).replace("-", "")

        if USE_S3_STORAGE:
            # Production: Store in S3
            try:
                from src.infrastructure.messaging.implementations.s3_storage import (
                    S3StorageService,
                )

                # Validate S3 configuration before creating service
                _validate_s3_configuration()

                settings = Settings()
                s3_service = S3StorageService(
                    bucket_name=settings.aws_s3_bucket,
                    aws_region=settings.aws_region,
                    prefix=f"filings/{company_cik}/",
                )
                await s3_service.connect()

                success = await s3_service.set(clean_accession, filing_content)
                if success:
                    logger.info(f"Stored filing {accession_number} to S3 storage")
                return success
            except Exception as e:
                logger.error(f"Failed to store to S3: {e}")
                return False
        else:
            # Development: Store in local storage service
            try:
                storage_service = await get_local_storage_service()
                filing_key = f"filing:{company_cik}/{clean_accession}"
                success = await storage_service.set(filing_key, filing_content)

                if success:
                    logger.info(
                        f"Stored filing {accession_number} to local storage service"
                    )
                return success
            except Exception as e:
                logger.error(f"Failed to store to local storage service: {e}")
                return False

    except Exception as e:
        logger.error(f"Error storing filing content: {e}")
        return False


@task(
    name="retrieve_and_analyze_filing",
    queue="analysis_queue",
    priority=TaskPriority.HIGH,
    max_retries=3,
)
async def retrieve_and_analyze_filing(
    company_cik: CIK | str,
    accession_number: AccessionNumber | str,
    analysis_template: AnalysisTemplate | str,
    force_reprocess: bool = False,
    llm_schemas: list[str] | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    task_id: str | None = None,  # Add task ID parameter
) -> dict[str, Any]:
    """Retrieve filing content and analyze using the specified LLM provider.

    This unified task:
    1. Retrieves filing content from storage or EDGAR
    2. Stores filing content for future use
    3. Performs LLM analysis on the filing

    Args:
        company_cik: Company CIK to identify the filing
        accession_number: SEC accession number to identify the filing
        analysis_template: Analysis template to use
        force_reprocess: Whether to reprocess if analysis already exists
        llm_schemas: List of LLM schema class names to use for analysis
        llm_provider: LLM provider to use (openai, google)
        llm_model: Specific model to use
        user_id: ID of the user requesting the analysis

    Returns:
        Analysis result with status and findings
    """
    start_time = asyncio.get_event_loop().time()

    # Convert string arguments to value objects if needed (for messaging serialization)
    if isinstance(company_cik, str):
        company_cik = CIK(company_cik)
    if isinstance(accession_number, str):
        accession_number = AccessionNumber(accession_number)
    if isinstance(analysis_template, str):
        analysis_template = AnalysisTemplate(analysis_template)

    # Initialize settings and set defaults if not provided
    settings = Settings()
    if llm_provider is None:
        llm_provider = settings.default_llm_provider
    if llm_model is None:
        llm_model = settings.llm_model

    try:
        logger.info(
            f"Starting analysis for filing {company_cik}/{accession_number} with template {analysis_template}"
        )

        # Initialize task tracking
        task_service = None
        if task_id:
            try:
                from src.application.services.task_service import TaskService

                task_service = TaskService()
                await task_service.update_task_status(
                    task_id=task_id,
                    status="running",
                    message="Starting filing analysis",
                    progress=5,
                    analysis_stage=AnalysisStage.INITIATING.value,
                )
            except Exception as e:
                logger.warning(f"Could not initialize task tracking: {e}")

        # Step 1: Retrieve filing content from storage or EDGAR
        if task_service and task_id:
            await task_service.update_task_status(
                task_id=task_id,
                status="running",
                message="Retrieving filing content",
                progress=15,
                analysis_stage=AnalysisStage.LOADING_FILING.value,
            )

        filing_content = await get_filing_content(accession_number, company_cik)

        if not filing_content:
            if task_service and task_id:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    message="Failed to retrieve filing content",
                    error=f"Unable to retrieve filing content for {accession_number}",
                    analysis_stage=AnalysisStage.ERROR.value,
                )
            raise ValueError(
                f"Unable to retrieve filing content for {accession_number}. "
                f"Filing could not be found in storage or downloaded from EDGAR."
            )

        logger.debug(
            f"Retrieved filing content for {accession_number} "
            f"(source: {filing_content.get('metadata', {}).get('source', 'unknown')})"
        )

        # Step 2: Filing content is now passed directly to orchestrator
        # No need to cache since orchestrator retrieves from storage directly
        logger.debug(
            f"Filing content retrieved for {accession_number}, proceeding with analysis"
        )

        if task_service and task_id:
            await task_service.update_task_status(
                task_id=task_id,
                status="running",
                message="Setting up database connections",
                progress=25,
                analysis_stage=AnalysisStage.LOADING_FILING.value,
            )

        async with async_session_maker() as session:
            # Get repositories
            filing_repo = FilingRepository(session)
            analysis_repo = AnalysisRepository(session)
            company_repo = CompanyRepository(session)

            # Get Edgar service
            edgar_service = EdgarService()

            # Step 3: Ensure company and filing records exist in database
            # Get company from database, auto-populate if not found
            company = await company_repo.get_by_cik(company_cik)
            if not company:
                logger.info(
                    f"Company with CIK {company_cik} not found, fetching from EDGAR"
                )
                try:
                    # Fetch company data from SEC EDGAR
                    company_data = edgar_service.get_company_by_cik(company_cik)

                    # Create new company entity
                    from src.domain.entities.company import Company

                    company = Company(
                        id=uuid4(),
                        cik=company_cik,
                        name=company_data.name,
                        metadata={
                            "ticker": company_data.ticker,
                            "sic": company_data.sic,
                            "sector": company_data.sector,
                            "auto_populated": True,
                            "auto_populated_date": filing_content.get("filing_date"),
                            "source": "edgar_api",
                        },
                    )

                    # Save to database
                    await company_repo.update(company)
                    await session.commit()

                    logger.info(
                        f"Successfully created company record for CIK {company_cik}: {company_data.name}"
                    )

                except Exception as company_error:
                    raise ValueError(
                        f"Company with CIK {company_cik} not found in database and could not be auto-populated from EDGAR: {str(company_error)}"
                    ) from company_error

            filing = await filing_repo.get_by_accession_number(
                accession_number=accession_number
            )
            if not filing:
                # CRITICAL: Only create filing record if content is in storage
                # First, verify that content exists in storage
                stored_content = await get_filing_content(accession_number, company_cik)

                if not stored_content:
                    # Content not in storage - try to store it first
                    storage_success = await store_filing_content(
                        accession_number, company_cik, filing_content
                    )
                    if not storage_success:
                        raise ValueError(
                            f"Cannot create filing record for {accession_number}: "
                            f"Failed to store filing content. Data consistency requires "
                            f"content in storage before creating database record."
                        )

                # Now safe to create filing record
                logger.info(
                    f"Creating filing record for {accession_number} in database"
                )

                filing = Filing(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=accession_number,
                    filing_type=FilingType(filing_content["filing_type"]),
                    filing_date=filing_content["filing_date"],
                    processing_status=ProcessingStatus.PENDING,
                    metadata={
                        "source": filing_content.get("metadata", {}).get(
                            "source", "unknown"
                        ),
                        "content_length": len(filing_content.get("content_text", "")),
                        "sections_count": len(filing_content.get("sections", {})),
                        "storage_verified": True,  # Mark that storage was verified
                    },
                )
                await filing_repo.update(filing)
                await session.commit()

                logger.info(f"Created filing record {filing.id} for {accession_number}")

            # Step 4: Create LLM provider
            provider: BaseLLMProvider
            if llm_provider.lower() == "openai":
                provider = OpenAIProvider()
            elif llm_provider.lower() == "google":
                provider = GoogleProvider()
            else:
                raise ValueError(f"Unsupported LLM provider: {llm_provider}")

            # Get analysis template service
            template_service = AnalysisTemplateService()

            # Create analysis orchestrator with filing repository
            orchestrator = AnalysisOrchestrator(
                llm_provider=provider,
                analysis_repository=analysis_repo,
                edgar_service=edgar_service,
                filing_repository=filing_repo,
                template_service=template_service,
            )

            command = AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                analysis_template=analysis_template,
                force_reprocess=force_reprocess,
            )

            # Use provided llm_schemas if available, otherwise derive from command
            if llm_schemas:
                logger.info(f"Using provided LLM schemas: {llm_schemas}")
            else:
                llm_schemas = command.get_llm_schemas_to_use()
                logger.info(f"Using LLM schemas from template: {llm_schemas}")

            # Step 5: Perform analysis using orchestrator
            if task_service and task_id:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="running",
                    message="Running LLM analysis",
                    progress=60,
                    analysis_stage=AnalysisStage.ANALYZING_CONTENT.value,
                )

            analysis = await orchestrator.orchestrate_filing_analysis(command)

            # Save results
            if task_service and task_id:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="running",
                    message="Saving analysis results",
                    progress=90,
                    analysis_stage=AnalysisStage.COMPLETING.value,
                )

            await analysis_repo.update(analysis)
            await session.commit()

            duration = asyncio.get_event_loop().time() - start_time

            result = {
                "status": "success",
                "analysis_id": str(analysis.id),
                "company_cik": company_cik,
                "accession_number": accession_number,
                "analysis_template": analysis_template,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "confidence_score": analysis.confidence_score,
                "processing_duration": duration,
                "results_summary": "Results stored in storage",  # Results are now in storage, not in entity
                "filing_source": filing_content.get("metadata", {}).get(
                    "source", "unknown"
                ),
            }

            # Mark task as completed
            if task_service and task_id:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="completed",
                    message="Analysis completed successfully",
                    progress=100,
                    result=result,
                    analysis_stage=AnalysisStage.COMPLETED.value,
                )

            logger.info(
                f"Analysis completed for filing {company_cik}/{accession_number}: {result}"
            )
            return result

    except Exception as e:
        duration = asyncio.get_event_loop().time() - start_time
        error_msg = (
            f"Analysis failed for filing {company_cik}/{accession_number}: {str(e)}"
        )
        logger.error(error_msg)

        # Mark task as failed
        if task_service and task_id:
            try:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    message="Analysis failed",
                    error=error_msg,
                    analysis_stage=AnalysisStage.ERROR.value,
                )
            except Exception as update_error:
                logger.warning(
                    f"Could not update task status on failure: {update_error}"
                )

        # Re-raise for task retry logic
        raise e


@task(
    name="validate_analysis_quality",
    queue="validation_queue",
    priority=TaskPriority.LOW,
    max_retries=1,
)
async def validate_analysis_quality(analysis_id: UUID) -> dict[str, Any]:
    """Validate the quality of an analysis result.

    Args:
        analysis_id: ID of the analysis to validate

    Returns:
        Quality validation result
    """
    start_time = asyncio.get_event_loop().time()

    try:
        logger.info(f"Starting quality validation for analysis {analysis_id}")

        async with async_session_maker() as session:
            analysis_repo = AnalysisRepository(session)

            analysis = await analysis_repo.get_by_id(analysis_id)
            if not analysis:
                raise ValueError(f"Analysis {analysis_id} not found")

            # Perform quality checks
            quality_metrics = {}

            # Check confidence score
            if analysis.confidence_score is not None:
                quality_metrics["has_confidence_score"] = True
                quality_metrics["confidence_score"] = True
                quality_metrics["confidence_level"] = (
                    True if (analysis.confidence_score > 0.8) else True
                )
            else:
                quality_metrics["has_confidence_score"] = False

            # Check results completeness
            if analysis.results:
                quality_metrics["has_results"] = True
                quality_metrics["result_keys"] = True
                quality_metrics["result_length"] = True
            else:
                quality_metrics["has_results"] = False

            # Check for metadata
            if analysis.metadata:
                quality_metrics["has_metadata"] = True
                quality_metrics["metadata_keys"] = True
            else:
                quality_metrics["has_metadata"] = False

            # Overall quality score
            quality_score = 0.0
            if quality_metrics.get("has_confidence_score"):
                quality_score += 0.3
            if quality_metrics.get("has_results"):
                quality_score += 0.5
            if quality_metrics.get("has_metadata"):
                quality_score += 0.2

            duration = asyncio.get_event_loop().time() - start_time

            result = {
                "status": "success",
                "analysis_id": str(analysis_id),
                "quality_score": quality_score,
                "quality_level": (
                    "excellent"
                    if quality_score > 0.9
                    else (
                        "good"
                        if quality_score > 0.7
                        else "fair" if quality_score > 0.5 else "poor"
                    )
                ),
                "quality_metrics": quality_metrics,
                "processing_duration": duration,
            }

            logger.info(
                f"Quality validation completed for analysis {analysis_id}: score={quality_score}"
            )
            return result

    except Exception as e:
        duration = asyncio.get_event_loop().time() - start_time
        error_msg = f"Quality validation failed for analysis {analysis_id}: {str(e)}"
        logger.error(error_msg)

        return {
            "status": "error",
            "analysis_id": str(analysis_id),
            "error": str(e),
            "processing_duration": duration,
        }
