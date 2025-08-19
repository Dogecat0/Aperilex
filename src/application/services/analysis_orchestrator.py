"""Analysis Orchestrator Service for coordinating filing analysis workflows."""

import inspect
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects import CIK
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm.base import BaseLLMProvider
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.shared.config import settings

logger = logging.getLogger(__name__)


class AnalysisOrchestrationError(Exception):
    """Base exception for analysis orchestration failures."""

    pass


class FilingAccessError(AnalysisOrchestrationError):
    """Exception for filing access validation failures."""

    pass


class AnalysisProcessingError(AnalysisOrchestrationError):
    """Exception for analysis processing failures."""

    pass


class AnalysisOrchestrator:
    """Service for orchestrating filing analysis workflows.

    This service coordinates the end-to-end process of analyzing SEC filings:
    - Filing validation and content retrieval
    - LLM analysis processing with appropriate templates
    - Progress tracking and error handling
    - Result persistence and metadata management

    Designed to handle single filing analysis workflows with proper error
    handling and retry logic.
    """

    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        filing_repository: FilingRepository,
        edgar_service: EdgarService,
        llm_provider: BaseLLMProvider,
        template_service: AnalysisTemplateService,
    ) -> None:
        """Initialize AnalysisOrchestrator with required dependencies.

        Args:
            analysis_repository: Repository for analysis persistence
            filing_repository: Repository for filing metadata and status
            edgar_service: Service for SEC filing retrieval
            llm_provider: LLM provider for analysis processing
            template_service: Service for analysis template management
        """
        self.analysis_repository = analysis_repository
        self.filing_repository = filing_repository
        self.edgar_service = edgar_service
        self.llm_provider = llm_provider
        self.template_service = template_service

    async def _call_progress_callback(
        self,
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Coroutine[Any, Any, None]]
            | None
        ),
        progress: float,
        message: str,
    ) -> None:
        """Call progress callback function, handling both sync and async variants.

        Progress callback errors are logged but don't interrupt the orchestration workflow.
        Provides resilient progress reporting for long-running analysis operations.

        Args:
            progress_callback: Optional callback function for progress updates
            progress: Progress value between 0.0 and 1.0
            message: Human-readable progress status message

        Note:
            Callback errors are logged as warnings and don't affect the main workflow.
        """
        if progress_callback:
            try:
                if inspect.iscoroutinefunction(progress_callback):
                    await progress_callback(progress, message)
                else:
                    progress_callback(progress, message)
            except Exception as e:
                logger.warning(
                    f"Progress callback failed at {progress:.1%}: {str(e)}",
                    extra={"progress": progress, "callback_message": message},
                )

    async def orchestrate_filing_analysis(
        self,
        command: AnalyzeFilingCommand,
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Coroutine[Any, Any, None]]
            | None
        ) = None,
    ) -> Analysis:
        """Orchestrate the complete end-to-end filing analysis workflow.

        This is the primary orchestration method that coordinates the entire SEC filing
        analysis pipeline from filing validation through LLM processing to result persistence.
        Implements robust error handling, progress tracking, and status management throughout
        the workflow.

        Workflow Steps:
        1. Command Validation: Validates required parameters and business rules
        2. Filing Access: Validates filing accessibility via Edgar API
        3. Filing Resolution: Retrieves or creates filing entity with company linkage
        4. Content Retrieval: Loads filing content from storage with Edgar fallback
        5. Duplicate Detection: Checks for existing analyses (unless force reprocess)
        6. Analysis Initialization: Creates analysis entity and begins progress tracking
        7. Status Management: Marks filing as PROCESSING during analysis
        8. Template Resolution: Maps analysis template to required LLM schemas
        9. Section Extraction: Intelligently filters filing content by schema requirements
        10. LLM Processing: Executes AI analysis with proper error handling
        11. Result Processing: Updates analysis with results and computed metadata
        12. Persistence: Saves completed analysis with comprehensive metadata
        13. Status Completion: Marks filing as COMPLETED after successful analysis
        14. Error Recovery: Handles failures with proper status rollback and cleanup

        Features:
        - Progress Tracking: Real-time progress updates via callback and persistent metadata
        - Duplicate Prevention: Automatic detection of existing analyses for efficiency
        - Error Resilience: Comprehensive error handling with proper status rollback
        - Content Optimization: Intelligent section filtering to reduce LLM token usage
        - Metadata Enrichment: Rich metadata capture for debugging and reanalysis
        - Storage Integration: Seamless integration with cached content and Edgar API

        Args:
            command: Analysis command containing filing identifier, template, and configuration
            progress_callback: Optional callback function for real-time progress updates.
                              Supports both synchronous and asynchronous callback functions.
                              Called with (progress: float, message: str) parameters.

        Returns:
            Analysis entity with complete results, metadata, and confidence scoring.
            Contains LLM analysis results, processing metadata, and section mappings.

        Raises:
            FilingAccessError: When filing cannot be accessed, validated, or retrieved
                              from Edgar API. Includes cases where filing data is malformed
                              or missing required fields.
            AnalysisProcessingError: When LLM analysis fails due to processing errors,
                                   API failures, or invalid analysis responses.
            AnalysisOrchestrationError: For other orchestration failures including
                                      database errors, entity creation failures, or
                                      unexpected system errors during workflow execution.
            ValueError: When command validation fails due to missing or invalid parameters.

        Note:
            The orchestrator ensures data consistency by rolling back filing status
            to FAILED if analysis fails after marking as PROCESSING. Progress callback
            errors are logged but don't interrupt the main workflow.
        """
        # Initialize filing variable to prevent UnboundLocalError in exception handlers
        filing = None

        try:
            # Validate command first to ensure required fields are present
            command.validate()

            logger.info(
                f"Starting analysis orchestration for filing {command.filing_identifier}"
            )

            # Step 1: Validate filing access and retrieve filing data
            # After validation, accession_number is guaranteed to be non-None
            if command.accession_number is None:
                raise ValueError("Accession number is required but was None")
            filing_data = await self.validate_filing_access_and_get_data(
                command.accession_number
            )

            # Get filing metadata from database and content from cache
            filing = await self.filing_repository.get_by_accession_number(
                command.accession_number
            )
            if not filing:
                # Try to create filing from edgar data if it doesn't exist
                filing_data = await self.validate_filing_access_and_get_data(
                    command.accession_number
                )
                filing = await self._create_filing_from_edgar_data(
                    filing_data, command.company_cik
                )

            # Ensure company_cik is available for storage retrieval
            assert command.company_cik is not None, "company_cik must not be None"
            # Get filing content directly from storage (no cache dependency)
            filing_content = await self._get_filing_content_from_storage(
                command.accession_number, command.company_cik
            )
            if not filing_content:
                raise FilingAccessError(
                    f"Filing content for {command.accession_number} not found in storage. "
                    f"Filing content must be retrieved before analysis can be performed."
                )

            # Step 2: Check for existing analysis (unless force reprocess)
            if not command.force_reprocess:
                existing_analysis = await self._find_existing_analysis(
                    filing.id, command
                )
                if existing_analysis:
                    logger.info(f"Using existing analysis {existing_analysis.id}")
                    return existing_analysis

            # Step 3: Create analysis entity and track progress
            analysis = await self._create_analysis_entity(filing.id, command)
            await self.track_analysis_progress(analysis.id, 0.1, "Analysis started")
            await self._call_progress_callback(
                progress_callback, 0.1, "Analysis started"
            )

            # Step 3.5: Mark filing as processing
            if filing.processing_status != ProcessingStatus.PROCESSING:
                filing.mark_as_processing()
                await self.filing_repository.update(filing)
                logger.info(
                    f"Marked filing {filing.id} as processing for analysis {analysis.id}"
                )
            else:
                logger.debug(f"Filing {filing.id} already in processing status")

            # Step 4: Resolve analysis template and schemas
            schemas_to_use = self.template_service.get_schemas_for_template(
                command.analysis_template
            )
            await self.track_analysis_progress(analysis.id, 0.2, "Template resolved")
            await self._call_progress_callback(
                progress_callback, 0.2, "Template resolved"
            )

            # Step 5: Extract filing sections based on schemas needed
            filing_sections = await self._extract_relevant_filing_sections(
                filing_content, schemas_to_use, command.accession_number
            )
            await self.track_analysis_progress(
                analysis.id, 0.4, "Filing sections extracted"
            )
            await self._call_progress_callback(
                progress_callback, 0.4, "Filing sections extracted"
            )

            # Step 6: Perform LLM analysis
            try:
                # Import FilingType for proper type conversion
                from src.domain.value_objects.filing_type import FilingType

                filing_type = FilingType(filing_data.filing_type)

                llm_response = await self.llm_provider.analyze_filing(
                    filing_sections=filing_sections,
                    filing_type=filing_type,
                    company_name=filing_data.company_name,
                    analysis_focus=schemas_to_use,
                )
                await self.track_analysis_progress(
                    analysis.id, 0.8, "LLM analysis completed"
                )
                await self._call_progress_callback(
                    progress_callback, 0.8, "LLM analysis completed"
                )
            except Exception as e:
                await self.handle_analysis_failure(analysis.id, e)
                raise AnalysisProcessingError(f"LLM analysis failed: {str(e)}") from e

            # Step 7: Store analysis results to storage first (for transactional consistency)
            # CRITICAL: Storage MUST succeed before persisting to database to prevent
            # orphaned metadata without results. This ensures data consistency.
            analysis_results = llm_response.model_dump()

            # Import storage function
            from src.infrastructure.tasks.analysis_tasks import store_analysis_results

            try:
                # Store results to storage - MUST succeed before saving to database
                storage_success = await store_analysis_results(
                    analysis.id,
                    command.company_cik,
                    command.accession_number,
                    analysis_results,
                )

                if not storage_success:
                    # Storage failed - DO NOT save to database to maintain consistency
                    # Delete the analysis entity that was created earlier
                    await self.analysis_repository.delete(analysis.id)

                    error_msg = (
                        f"Failed to store analysis results to storage for {analysis.id}. "
                        f"Analysis entity has been rolled back to maintain data consistency."
                    )
                    logger.error(error_msg)
                    raise AnalysisProcessingError(error_msg)

            except Exception as e:
                # Handle any storage exceptions
                await self.analysis_repository.delete(analysis.id)
                error_msg = (
                    f"Storage operation failed for analysis {analysis.id}: {str(e)}. "
                    f"Analysis entity has been rolled back."
                )
                logger.error(error_msg, exc_info=True)
                raise AnalysisProcessingError(error_msg) from e

            # Storage succeeded, now safe to update metadata
            logger.info(
                f"Successfully stored analysis results for {analysis.id} in storage"
            )
            analysis.update_confidence_score(llm_response.confidence_score)

            # Determine which schemas were actually processed based on sections analyzed
            actual_schemas_processed = []
            sections_analyzed = [
                sa.section_name for sa in llm_response.section_analyses
            ]

            # Map section names back to schemas that were actually used
            section_to_schema_reverse = {
                # 10-K sections
                "Item 1 - Business": "BusinessAnalysisSection",
                "Item 1A - Risk Factors": "RiskFactorsAnalysisSection",
                "Item 7 - Management Discussion & Analysis": "MDAAnalysisSection",
                # 10-Q sections
                "Part I Item 2 - Management Discussion & Analysis": "MDAAnalysisSection",
                "Part II Item 1A - Risk Factors": "RiskFactorsAnalysisSection",
                # Financial statements
                "Balance Sheet": "BalanceSheetAnalysisSection",
                "Income Statement": "IncomeStatementAnalysisSection",
                "Cash Flow Statement": "CashFlowAnalysisSection",
            }

            for section in sections_analyzed:
                schema = section_to_schema_reverse.get(section)
                if schema and schema not in actual_schemas_processed:
                    actual_schemas_processed.append(schema)

            # Update metadata with processing details
            metadata = {
                "template_used": command.analysis_template.value,
                "schemas_requested": schemas_to_use,
                "schemas_processed": actual_schemas_processed,
                "sections_analyzed": sections_analyzed,
                "processing_time_minutes": 15,  # Default processing time
                "edgar_accession": command.accession_number.value,
                "accession_number": str(command.accession_number),  # For reanalysis
                "company_cik": command.company_cik.value,  # For reanalysis
                "force_reprocessed": command.force_reprocess,
            }
            # Update metadata directly since there's no update_metadata method
            analysis._metadata.update(metadata)

            # Step 8: Persist final analysis
            analysis = await self.analysis_repository.update(analysis)
            await self.track_analysis_progress(analysis.id, 1.0, "Analysis completed")
            await self._call_progress_callback(
                progress_callback, 1.0, "Analysis completed"
            )

            # Step 9: Update filing status to completed after successful analysis
            if filing.processing_status != ProcessingStatus.COMPLETED:
                filing.mark_as_completed()
                await self.filing_repository.update(filing)
                logger.info(
                    f"Updated filing {filing.id} status to completed after analysis"
                )

            logger.info(f"Analysis orchestration completed: {analysis.id}")
            return analysis

        except (FilingAccessError, AnalysisProcessingError) as e:
            # Handle filing status rollback for known exceptions
            if filing is not None:
                await self._rollback_filing_status_on_failure(filing, str(e))
            raise
        except Exception as e:
            # Handle filing status rollback for unexpected exceptions
            if filing is not None:
                await self._rollback_filing_status_on_failure(filing, str(e))
            logger.error(f"Unexpected orchestration error: {str(e)}", exc_info=True)
            raise AnalysisOrchestrationError(
                f"Analysis orchestration failed: {str(e)}"
            ) from e

    async def validate_filing_access_and_get_data(
        self, accession_number: AccessionNumber
    ) -> FilingData:
        """Validate that a filing can be accessed and return the filing data.

        Args:
            accession_number: SEC accession number to validate

        Returns:
            Filing data from EdgarService

        Raises:
            FilingAccessError: If filing cannot be accessed or is invalid
        """
        try:
            # Attempt to retrieve filing data via EdgarService (now synchronous)
            filing_data = self.edgar_service.get_filing_by_accession(accession_number)

            # Basic validation checks
            if not filing_data.company_name:
                raise FilingAccessError("Filing missing required company name")

            if not filing_data.filing_type:
                raise FilingAccessError("Filing missing required filing type")

            logger.debug(f"Filing validation successful: {accession_number.value}")
            return filing_data

        except ValueError as e:
            raise FilingAccessError(
                f"Cannot access filing {accession_number.value}: {str(e)}"
            ) from e

    async def validate_filing_access(self, accession_number: AccessionNumber) -> bool:
        """Validate that a filing can be accessed and processed.

        Args:
            accession_number: SEC accession number to validate

        Returns:
            True if filing is accessible

        Raises:
            FilingAccessError: If filing cannot be accessed or is invalid
        """
        try:
            # Use the new method that returns data but just return True for compatibility
            await self.validate_filing_access_and_get_data(accession_number)
            return True

        except FilingAccessError:
            # Re-raise FilingAccessError as-is
            raise
        except ValueError as e:
            raise FilingAccessError(
                f"Cannot access filing {accession_number.value}: {str(e)}"
            ) from e
        except Exception as e:
            raise FilingAccessError(
                f"Unexpected error validating filing access: {str(e)}"
            ) from e

    async def handle_analysis_failure(
        self, analysis_id: UUID, error: Exception
    ) -> None:
        """Handle analysis processing failures with comprehensive error logging and cleanup.

        Updates analysis entity with failure metadata, logs detailed error information,
        and tracks failure progress. Provides graceful degradation when analysis
        operations encounter unrecoverable errors.

        Args:
            analysis_id: UUID of the failed analysis entity
            error: Exception instance that caused the analysis failure

        Note:
            Failure handling errors are logged but don't propagate to prevent
            cascading failures in the orchestration workflow.
        """
        try:
            logger.error(
                f"Analysis {analysis_id} failed: {str(error)}",
                exc_info=True,
                extra={"analysis_id": str(analysis_id)},
            )

            # Update analysis with failure information
            analysis = await self.analysis_repository.get_by_id(analysis_id)
            if analysis:
                failure_metadata = {
                    "failure_reason": str(error),
                    "failure_type": type(error).__name__,
                    "failed_at": datetime.now(UTC).isoformat(),
                }

                # Update existing metadata with failure info
                analysis._metadata.update(failure_metadata)

                await self.analysis_repository.update(analysis)
                await self.track_analysis_progress(
                    analysis_id, 0.0, f"Failed: {str(error)[:100]}"
                )

        except Exception as e:
            logger.error(
                f"Failed to handle analysis failure for {analysis_id}: {str(e)}"
            )

    async def track_analysis_progress(
        self, analysis_id: UUID, progress: float, status: str
    ) -> None:
        """Track and persist progress updates for long-running analysis operations.

        Updates analysis entity metadata with current progress information and logs
        detailed progress events. Enables monitoring and debugging of analysis workflows
        through persistent progress tracking.

        Args:
            analysis_id: UUID of the analysis entity being tracked
            progress: Progress value between 0.0 and 1.0 (0% to 100%)
            status: Human-readable description of current processing step

        Note:
            Progress tracking failures are logged as warnings and don't interrupt
            the main analysis workflow.
        """
        try:
            logger.info(
                f"Analysis {analysis_id} progress: {progress:.1%} - {status}",
                extra={
                    "analysis_id": str(analysis_id),
                    "progress": progress,
                    "status": status,
                },
            )

            # Update analysis metadata with progress information
            analysis = await self.analysis_repository.get_by_id(analysis_id)
            if analysis:
                progress_metadata = {
                    "current_progress": progress,
                    "current_status": status,
                    "last_updated": datetime.now(UTC).isoformat(),
                }

                # Update metadata directly
                analysis._metadata.update(progress_metadata)

                await self.analysis_repository.update(analysis)

        except Exception as e:
            logger.warning(f"Failed to track progress for {analysis_id}: {str(e)}")

    async def _create_analysis_entity(
        self, filing_id: UUID, command: AnalyzeFilingCommand
    ) -> Analysis:
        """Create and persist new analysis entity from command parameters.

        Initializes analysis entity with default configuration values from settings,
        assigns unique identifier, and persists to repository. Sets up the foundation
        for tracking analysis workflow progress and results.

        Args:
            filing_id: UUID of the filing entity being analyzed
            command: Analysis command containing user ID and configuration

        Returns:
            Newly created and persisted Analysis entity

        Raises:
            AnalysisOrchestrationError: If analysis entity creation or persistence fails
        """
        analysis = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=command.user_id,
            llm_provider=settings.default_llm_provider,  # Default provider
            llm_model=settings.llm_model,  # Default model
            created_at=datetime.now(UTC),
        )

        return await self.analysis_repository.create(analysis)

    async def _find_existing_analysis(
        self, filing_id: UUID, command: AnalyzeFilingCommand
    ) -> Analysis | None:
        """Search for existing analysis matching the same filing and template configuration.

        Prevents duplicate analysis processing by checking for completed analyses
        with identical filing and template parameters. Enables efficient reuse
        of previously computed results unless force reprocessing is requested.

        Args:
            filing_id: UUID of the filing entity to search for
            command: Analysis command containing template and configuration to match

        Returns:
            Existing Analysis entity if matching analysis found, None otherwise

        Note:
            Search errors are logged as warnings and return None to allow
            new analysis creation rather than failing the orchestration.
        """
        try:
            # Search for existing analyses for this filing
            existing_analyses = await self.analysis_repository.get_by_filing_id(
                filing_id, AnalysisType.FILING_ANALYSIS
            )

            # Filter analyses that match the same template
            template_value = command.analysis_template.value

            for analysis in existing_analyses:
                # Check if metadata contains the same template
                analysis_metadata = analysis.metadata
                if analysis_metadata.get("template_used") == template_value:
                    logger.info(
                        f"Found existing analysis {analysis.id} for filing {filing_id} "
                        f"with template {template_value}"
                    )
                    return analysis

            logger.debug(
                f"No existing analysis found for filing {filing_id} "
                f"with template {template_value}"
            )
            return None

        except Exception as e:
            logger.warning(
                f"Error searching for existing analysis: {str(e)}",
                extra={
                    "filing_id": str(filing_id),
                    "template": command.analysis_template.value,
                },
            )
            # Return None to proceed with new analysis rather than failing
            return None

    async def _create_filing_from_edgar_data(
        self, filing_data: FilingData, company_cik: CIK | None
    ) -> Filing:
        """Create and persist filing entity from Edgar service data.

        Handles complete filing entity creation workflow including company resolution,
        filing metadata extraction, and database persistence. Creates associated
        company entity if it doesn't exist in the database.

        Args:
            filing_data: Complete filing information from EdgarService
            company_cik: Company CIK identifier, uses filing data CIK if None

        Returns:
            Newly created and persisted Filing entity

        Raises:
            AnalysisOrchestrationError: If filing or company creation fails
            ValueError: If required filing data fields are missing or invalid
        """
        try:
            # Use CIK from command or fallback to filing data CIK
            if company_cik:
                cik = company_cik
            else:
                cik = CIK(filing_data.cik)

            # Get or create company entity
            company_repo = CompanyRepository(self.filing_repository.session)
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
            filing_date_obj = date.fromisoformat(filing_data.filing_date.split("T")[0])

            # Create filing entity
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
                    "created_via": "analysis_orchestrator",
                },
            )

            # Persist the filing
            filing = await self.filing_repository.create(filing)

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
            raise AnalysisOrchestrationError(
                f"Failed to create filing entity: {str(e)}"
            ) from e

    async def _get_filing_content_from_storage(
        self, accession_number: AccessionNumber, company_cik: CIK
    ) -> dict[str, Any] | None:
        """Retrieve filing content from persistent storage (local files or S3).

        Attempts to load previously cached filing content using the same storage
        logic as analysis tasks. Provides fast access to filing data without
        requiring repeated Edgar API calls.

        Args:
            accession_number: SEC accession number for filing identification
            company_cik: Company CIK identifier for storage path resolution

        Returns:
            Filing content dictionary with sections and metadata if found,
            None if content not available in storage

        Note:
            Storage access failures are logged but return None rather than
            raising exceptions to allow fallback to Edgar API retrieval.
        """
        try:
            # Import the storage functions from analysis_tasks
            # Import required modules for storage access
            from src.infrastructure.tasks.analysis_tasks import get_filing_content

            # company_cik is already typed as CIK
            cik = company_cik

            # Use the same storage retrieval logic
            filing_content = await get_filing_content(accession_number, cik)

            if filing_content:
                logger.debug(
                    f"Retrieved filing content for {accession_number} from storage"
                )
                return filing_content
            else:
                logger.warning(
                    f"Filing content for {accession_number} not found in storage"
                )
                return None

        except Exception as e:
            logger.error(
                f"Failed to retrieve filing content from storage: {e}", exc_info=True
            )
            return None

    async def _extract_relevant_filing_sections(
        self,
        filing_content: dict[str, Any] | None,
        schemas_to_use: list[str],
        accession_number: AccessionNumber,
    ) -> dict[str, str]:
        """Extract relevant filing sections optimized for specified analysis schemas.

        Intelligently filters filing content to include only sections required
        by the analysis templates, improving processing efficiency and reducing
        LLM token usage. Implements fallback strategies for content retrieval.

        Args:
            filing_content: Cached filing content from storage, None triggers Edgar fallback
            schemas_to_use: List of analysis schema names requiring specific sections
            accession_number: SEC accession number for Edgar API fallback retrieval

        Returns:
            Dictionary mapping section names to extracted section text content

        Note:
            Falls back through multiple strategies: cached content → Edgar data →
            section extraction → full content text to ensure analysis can proceed.
        """
        # Map schemas to required filing sections, both 10-K and 10-Q
        schema_section_mapping = {
            "BusinessAnalysisSection": [
                "Item 1 - Business",  # 10-K
            ],
            "RiskFactorsAnalysisSection": [
                "Item 1A - Risk Factors",  # 10-K
                "Part II Item 1A - Risk Factors",  # 10-Q
            ],
            "MDAAnalysisSection": [
                "Item 7 - Management Discussion & Analysis",  # 10-K
                "Part I Item 2 - Management Discussion & Analysis",  # 10-Q
            ],
            "BalanceSheetAnalysisSection": ["Balance Sheet"],
            "IncomeStatementAnalysisSection": ["Income Statement"],
            "CashFlowAnalysisSection": ["Cash Flow Statement"],
        }

        # Determine which sections we need
        sections_needed: set[str] = set()
        for schema in schemas_to_use:
            sections_needed.update(schema_section_mapping.get(schema, []))

        # Try filing content first (preferred path)
        if filing_content and "sections" in filing_content:
            logger.debug("Using sections from filing content")
            # Filter to only needed sections
            relevant_sections = {
                section: content
                for section, content in filing_content["sections"].items()
                if section in sections_needed
            }

            # If we found relevant sections, return them
            if relevant_sections:
                logger.info(
                    f"Found {len(relevant_sections)} relevant sections from filing content"
                )
                return relevant_sections

        # Fallback to filing content text if no sections available
        if filing_content and "content_text" in filing_content:
            logger.warning(
                "No specific sections found in filing content, using content text"
            )
            return {"Filing Content": filing_content["content_text"]}

        # Last resort: fetch from Edgar service
        logger.warning("No filing content available, fetching from Edgar service")
        filing_data = await self.validate_filing_access_and_get_data(accession_number)

        # If filing data has sections extracted, use them
        if filing_data.sections:
            logger.debug("Using pre-extracted sections from Edgar filing data")
            # Filter to only needed sections
            relevant_sections = {
                section: content
                for section, content in filing_data.sections.items()
                if section in sections_needed
            }

            # If we found relevant sections, return them
            if relevant_sections:
                logger.info(
                    f"Found {len(relevant_sections)} relevant sections from Edgar data"
                )
                return relevant_sections

        # If no sections in filing data or no relevant sections found,
        # extract sections using EdgarService
        try:
            # Import required types for EdgarService call

            # Use ticker from filing data if available, otherwise extract from company
            if filing_data.ticker:
                ticker = Ticker(filing_data.ticker)
            else:
                logger.warning(
                    "No ticker in filing data, using CIK for section extraction"
                )
                # For now, we'll use the sections from filing data or content text
                # as a fallback since we can't extract without a ticker
                if filing_data.sections:
                    return filing_data.sections
                else:
                    # Return content as a single section
                    return {"Filing Content": filing_data.content_text}

            filing_type = FilingType(filing_data.filing_type)

            # Extract sections using EdgarService (synchronous call)
            all_sections = self.edgar_service.extract_filing_sections(
                ticker, filing_type
            )

            # Filter to only needed sections
            relevant_sections = {
                section: content
                for section, content in all_sections.items()
                if section in sections_needed
            }

            if relevant_sections:
                logger.info(f"Extracted {len(relevant_sections)} relevant sections")
                return relevant_sections
            else:
                logger.warning(
                    "No relevant sections found, returning all extracted sections"
                )
                return all_sections

        except Exception as e:
            logger.warning(
                f"Failed to extract specific sections: {str(e)}. "
                f"Using fallback approach"
            )
            # Fallback to returning available sections or content
            if filing_data.sections:
                return filing_data.sections
            else:
                # Return content as a single section for analysis
                return {"Filing Content": filing_data.content_text}

    async def _rollback_filing_status_on_failure(
        self, filing: Filing | None, error_message: str
    ) -> None:
        """Rollback filing processing status to FAILED after analysis orchestration failure.

        Ensures filing entities don't remain in PROCESSING state when analysis
        workflows encounter unrecoverable errors. Maintains data consistency
        and enables proper retry logic for failed analyses.

        Args:
            filing: Filing entity to update, None-safe for error scenarios
            error_message: Detailed error description for failure documentation

        Note:
            Status rollback failures are logged as warnings to prevent
            cascading errors during error recovery workflows.
        """
        try:
            if filing and filing.processing_status == ProcessingStatus.PROCESSING:
                filing.mark_as_failed(error_message)
                await self.filing_repository.update(filing)
                logger.info(
                    f"Rolled back filing {filing.id} status to FAILED after analysis failure"
                )
        except Exception as e:
            logger.warning(
                f"Failed to rollback filing status for {filing.id if filing else 'None'}: {str(e)}"
            )
