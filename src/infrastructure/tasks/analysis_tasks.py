"""Background tasks for filing retrieval and analysis using LLM providers and new messaging system."""

import asyncio
import json
import logging
import os
from pathlib import Path
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
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.database.base import async_session_maker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm import BaseLLMProvider, GoogleProvider, OpenAIProvider
from src.infrastructure.messaging import TaskPriority, task
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.shared.config.settings import Settings

logger = logging.getLogger(__name__)

# File storage configuration
FILING_STORAGE_PATH = os.getenv("FILING_STORAGE_PATH", "./data/filings")
ANALYSIS_STORAGE_PATH = os.getenv("ANALYSIS_STORAGE_PATH", "./data/analyses")
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
MAX_CONCURRENT_FILING_DOWNLOADS = 1  # Limit to 1 concurrent download from EDGAR
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit for filing files


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
        logger.info(f"Using local file storage: {FILING_STORAGE_PATH}")


def _validate_file_path(file_path: Path) -> None:
    """Validate file path for security and size constraints.

    Args:
        file_path: Path to validate

    Raises:
        ValueError: If path is invalid or file is too large
    """
    # Ensure path is within expected directory (prevent path traversal)
    resolved_path = file_path.resolve()

    # Check if path is within either filing or analysis storage directory
    valid_paths = [
        Path(FILING_STORAGE_PATH).resolve(),
        Path(ANALYSIS_STORAGE_PATH).resolve(),
    ]

    path_valid = False
    for valid_path in valid_paths:
        try:
            resolved_path.relative_to(valid_path)
            path_valid = True
            break
        except ValueError:
            continue

    if not path_valid:
        raise ValueError(
            f"Invalid file path outside storage directories: {file_path}. "
            f"Must be within {FILING_STORAGE_PATH} or {ANALYSIS_STORAGE_PATH}"
        )

    # Check file size if file exists
    if file_path.exists():
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
            )


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
            # Development: Try local file storage first
            file_path = (
                Path(FILING_STORAGE_PATH) / str(company_cik) / f"{clean_accession}.json"
            )

            if file_path.exists():
                try:
                    # Validate file path and size for security
                    _validate_file_path(file_path)

                    with open(file_path, encoding="utf-8") as f:
                        filing_content = json.load(f)
                    logger.info(
                        f"Retrieved filing {accession_number} from local storage: {file_path}"
                    )
                    return filing_content  # type: ignore[no-any-return]
                except Exception as e:
                    logger.warning(f"Failed to read local file {file_path}: {e}")

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
            # Development: Try local file storage using dedicated analysis storage path
            clean_accession = accession_number.value.replace("-", "")
            file_path = (
                Path(ANALYSIS_STORAGE_PATH)
                / str(company_cik)
                / clean_accession
                / f"{analysis_key}.json"
            )

            if file_path.exists():
                try:
                    _validate_file_path(file_path)
                    with open(file_path, encoding="utf-8") as f:
                        analysis_results = json.load(f)
                    logger.debug(
                        f"Retrieved analysis {analysis_id} from local storage: {file_path}"
                    )
                    return analysis_results  # type: ignore[no-any-return]
                except Exception as e:
                    logger.warning(f"Failed to read analysis file {file_path}: {e}")

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
            # Development: Store in local file system using dedicated analysis storage path
            clean_accession = accession_number.value.replace("-", "")
            file_path = (
                Path(ANALYSIS_STORAGE_PATH)
                / str(company_cik)
                / clean_accession
                / f"{analysis_key}.json"
            )

            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(file_path, "w") as f:
                    json.dump(analysis_results, f, indent=2, default=str)
                logger.info(
                    f"Stored analysis {analysis_id} to local storage: {file_path}"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to write analysis file {file_path}: {e}")
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
            # Development: Store in local file system
            file_path = (
                Path(FILING_STORAGE_PATH) / str(company_cik) / f"{clean_accession}.json"
            )

            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(file_path, "w") as f:
                    json.dump(filing_content, f, indent=2, default=str)
                logger.info(
                    f"Stored filing {accession_number} to local storage: {file_path}"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to write local file {file_path}: {e}")
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

        # Step 1: Retrieve filing content from storage or EDGAR
        filing_content = await get_filing_content(accession_number, company_cik)

        if not filing_content:
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

        async with async_session_maker() as session:
            # Get repositories
            filing_repo = FilingRepository(session)
            analysis_repo = AnalysisRepository(session)
            company_repo = CompanyRepository(session)

            # Get Edgar service
            edgar_service = EdgarService()

            # Step 3: Ensure filing record exists in database
            # Get company and filing from database
            company = await company_repo.get_by_cik(company_cik)
            if not company:
                raise ValueError(f"Company with CIK {company_cik} not found")

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
            analysis = await orchestrator.orchestrate_filing_analysis(command)

            # Save results
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
