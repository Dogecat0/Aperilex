"""Analysis Orchestrator Service for coordinating filing analysis workflows."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.value_objects.accession_number import AccessionNumber
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm.base import BaseLLMProvider
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository

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
            filing_repository: Repository for filing data
            edgar_service: Service for SEC filing retrieval
            llm_provider: LLM provider for analysis processing
            template_service: Service for analysis template management
        """
        self.analysis_repository = analysis_repository
        self.filing_repository = filing_repository
        self.edgar_service = edgar_service
        self.llm_provider = llm_provider
        self.template_service = template_service

    async def orchestrate_filing_analysis(
        self, command: AnalyzeFilingCommand
    ) -> Analysis:
        """Orchestrate the complete filing analysis workflow.

        This is the main orchestration method that coordinates:
        1. Filing access validation
        2. Filing content retrieval via EdgarService
        3. Template and schema resolution
        4. LLM analysis processing
        5. Result persistence and metadata management

        Args:
            command: Analysis command with filing details and parameters

        Returns:
            Analysis entity with complete results

        Raises:
            FilingAccessError: If filing cannot be accessed or validated
            AnalysisProcessingError: If LLM analysis fails
            AnalysisOrchestrationError: For other orchestration failures
        """
        try:
            # Validate command first to ensure required fields are present
            command.validate()

            logger.info(
                f"Starting analysis orchestration for filing {command.filing_identifier}"
            )

            # Step 1: Validate filing access and retrieve filing data
            # After validation, accession_number is guaranteed to be non-None
            assert command.accession_number is not None
            await self.validate_filing_access(command.accession_number)
            filing_data = self.edgar_service.get_filing_by_accession(
                command.accession_number
            )

            # Get or create filing entity in database
            filing = await self.filing_repository.get_by_accession_number(
                command.accession_number
            )
            if not filing:
                # Create filing entity from edgar data
                filing = await self._create_filing_from_edgar_data(
                    filing_data, command.company_cik
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

            # Step 4: Resolve analysis template and schemas
            schemas_to_use = self.template_service.map_template_to_schemas(
                command.analysis_template, command.custom_schema_selection
            )
            await self.track_analysis_progress(analysis.id, 0.2, "Template resolved")

            # Step 5: Extract filing sections based on schemas needed
            filing_sections = await self._extract_relevant_filing_sections(
                filing_data, schemas_to_use
            )
            await self.track_analysis_progress(
                analysis.id, 0.4, "Filing sections extracted"
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
            except Exception as e:
                await self.handle_analysis_failure(analysis.id, e)
                raise AnalysisProcessingError(f"LLM analysis failed: {str(e)}") from e

            # Step 7: Update analysis with results and metadata
            analysis.update_results(llm_response.model_dump())
            analysis.update_confidence_score(llm_response.confidence_score)

            # Update metadata with processing details
            metadata = {
                "template_used": command.analysis_template.value,
                "schemas_processed": schemas_to_use,
                "processing_time_minutes": command.estimated_processing_time_minutes,
                "custom_instructions": command.custom_instructions,
                "edgar_accession": command.accession_number.value,
                "force_reprocessed": command.force_reprocess,
            }
            # Update metadata directly since there's no update_metadata method
            analysis._metadata.update(metadata)

            # Step 8: Persist final analysis
            analysis = await self.analysis_repository.update(analysis)
            await self.track_analysis_progress(analysis.id, 1.0, "Analysis completed")

            logger.info(f"Analysis orchestration completed: {analysis.id}")
            return analysis

        except (FilingAccessError, AnalysisProcessingError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected orchestration error: {str(e)}", exc_info=True)
            raise AnalysisOrchestrationError(
                f"Analysis orchestration failed: {str(e)}"
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
            # Attempt to retrieve filing data via EdgarService
            filing_data = self.edgar_service.get_filing_by_accession(accession_number)

            # Basic validation checks
            if not filing_data.company_name:
                raise FilingAccessError("Filing missing required company name")

            if not filing_data.filing_type:
                raise FilingAccessError("Filing missing required filing type")

            logger.debug(f"Filing validation successful: {accession_number.value}")
            return True

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
        """Handle analysis processing failures with proper logging and cleanup.

        Args:
            analysis_id: ID of the failed analysis
            error: Exception that caused the failure
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
        """Track progress of long-running analysis operations.

        Args:
            analysis_id: ID of the analysis to track
            progress: Progress percentage (0.0 to 1.0)
            status: Human-readable status message
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
        """Create new analysis entity from command parameters.

        Args:
            filing_id: ID of the filing being analyzed
            command: Analysis command with configuration

        Returns:
            New Analysis entity
        """
        analysis = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=command.user_id,
            llm_provider="openai",  # Default provider
            llm_model="gpt-4",  # Default model
            created_at=datetime.now(UTC),
        )

        return await self.analysis_repository.create(analysis)

    async def _find_existing_analysis(
        self, filing_id: UUID, command: AnalyzeFilingCommand
    ) -> Analysis | None:
        """Find existing analysis for the same filing and template.

        Args:
            filing_id: ID of the filing
            command: Analysis command to match against

        Returns:
            Existing Analysis if found, None otherwise
        """
        # This would need to be implemented based on repository search capabilities
        # For now, return None to always create new analysis
        return None

    async def _create_filing_from_edgar_data(
        self, filing_data: Any, company_cik: Any
    ) -> Any:
        """Create filing entity from edgar service data.

        Args:
            filing_data: Filing data from EdgarService
            company_cik: Company CIK from command

        Returns:
            Created Filing entity
        """
        # This would need to create a Filing entity and persist it
        # Implementation depends on Filing entity structure
        # For now, raise NotImplementedError as placeholder
        raise NotImplementedError("Filing creation from edgar data not yet implemented")

    async def _extract_relevant_filing_sections(
        self, filing_data: Any, schemas_to_use: list[str]
    ) -> dict[str, str]:
        """Extract only the filing sections needed for the specified schemas.

        Args:
            filing_data: Filing data from EdgarService
            schemas_to_use: List of schema names that need specific sections

        Returns:
            Dictionary mapping section names to section text
        """
        # Map schemas to required filing sections
        schema_section_mapping = {
            "BusinessAnalysisSection": ["Item 1 - Business"],
            "RiskFactorsAnalysisSection": ["Item 1A - Risk Factors"],
            "MDAAnalysisSection": ["Item 7 - Management Discussion & Analysis"],
            "BalanceSheetAnalysisSection": ["Balance Sheet"],
            "IncomeStatementAnalysisSection": ["Income Statement"],
            "CashFlowAnalysisSection": ["Cash Flow Statement"],
        }

        # Determine which sections we need
        sections_needed: set[Any] = set()
        for schema in schemas_to_use:
            sections_needed.update(schema_section_mapping.get(schema, []))

        # Extract sections using EdgarService
        # For now, extract all sections and filter later
        # This would need to be optimized based on EdgarService capabilities
        try:
            # Import required types for EdgarService call
            from src.domain.value_objects.filing_type import FilingType
            from src.domain.value_objects.ticker import Ticker

            ticker = Ticker(filing_data.ticker)
            filing_type = FilingType(filing_data.filing_type)

            all_sections = self.edgar_service.extract_filing_sections(
                ticker, filing_type
            )

            # Filter to only needed sections
            relevant_sections = {
                section: content
                for section, content in all_sections.items()
                if section in sections_needed
            }

            return relevant_sections

        except Exception as e:
            logger.warning(
                f"Failed to extract specific sections, using all sections: {str(e)}"
            )
            # Fallback to returning all available sections
            return getattr(filing_data, "sections", {})
