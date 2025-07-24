"""Background task coordinator for managing long-running analysis operations."""

import logging
from uuid import UUID

from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.task_service import TaskService

logger = logging.getLogger(__name__)


class BackgroundTaskCoordinator:
    """Coordinator for managing background analysis tasks.

    This service orchestrates long-running analysis operations by:
    - Creating task tracking entries
    - Executing analysis workflows with progress tracking
    - Handling task completion and failure scenarios
    - Preparing foundation for future Celery integration
    """

    def __init__(
        self,
        analysis_orchestrator: AnalysisOrchestrator,
        task_service: TaskService,
        use_celery: bool = False,
    ) -> None:
        """Initialize the background task coordinator.

        Args:
            analysis_orchestrator: Service for analysis workflow coordination
            task_service: Service for task tracking and management
            use_celery: Whether to use Celery for background task execution
        """
        self.analysis_orchestrator = analysis_orchestrator
        self.task_service = task_service
        self.use_celery = use_celery

    async def queue_filing_analysis(
        self, command: AnalyzeFilingCommand
    ) -> TaskResponse:
        """Queue a filing analysis for background processing.

        Args:
            command: Command containing analysis parameters

        Returns:
            TaskResponse with task tracking information
        """
        # Create task parameters for tracking
        task_parameters = {
            "company_cik": str(command.company_cik),
            "accession_number": str(command.accession_number),
            "analysis_template": command.analysis_template.value,
            "force_reprocess": command.force_reprocess,
            "llm_schemas": command.get_llm_schemas_to_use(),
        }

        # Create task entry
        task_response = await self.task_service.create_task(
            task_type="analyze_filing",
            parameters=task_parameters,
            user_id=command.user_id,
        )

        logger.info(
            f"Queued filing analysis task {task_response.task_id}",
            extra={
                "task_id": str(task_response.task_id),
                "filing_identifier": command.filing_identifier,
                "analysis_template": command.analysis_template.value,
                "user_id": command.user_id,
            },
        )

        # Execute task based on configuration
        if self.use_celery:
            try:
                await self._queue_celery_task(task_response.task_id, command)
            except Exception as e:
                logger.error(
                    f"Failed to queue Celery task {task_response.task_id}",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await self.task_service.fail_task(
                    UUID(task_response.task_id), f"Failed to queue task: {str(e)}"
                )
        else:
            # Process synchronously for development/testing
            try:
                await self._execute_analysis_task(UUID(task_response.task_id), command)
            except Exception as e:
                logger.error(
                    f"Analysis task {task_response.task_id} failed during execution",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # Task failure is already handled in _execute_analysis_task

        return task_response

    async def _queue_celery_task(
        self, task_id: str, command: AnalyzeFilingCommand
    ) -> None:
        """Queue analysis task using Celery.

        Args:
            task_id: ID of the task to execute
            command: Analysis command to execute
        """
        try:
            from src.infrastructure.tasks.analysis_tasks import analyze_filing_task

            # Queue the Celery task
            celery_task = analyze_filing_task.delay(
                filing_id=str(command.accession_number),
                analysis_type=command.analysis_template.value,
                created_by=command.user_id,
                task_id=task_id,  # Pass our task ID for tracking
                force_reprocess=command.force_reprocess,
            )

            logger.info(
                f"Queued Celery task {celery_task.id} for analysis task {task_id}",
                extra={
                    "task_id": task_id,
                    "celery_task_id": celery_task.id,
                    "filing_identifier": command.filing_identifier,
                },
            )

            # Update task to processing status
            await self.task_service.update_task_progress(
                UUID(task_id), 0.05, "Queued for background processing"
            )

        except ImportError as e:
            logger.error(f"Celery tasks not available: {e}")
            # Fallback to synchronous processing
            await self._execute_analysis_task(UUID(task_id), command)
        except Exception as e:
            logger.error(f"Failed to queue Celery task: {e}")
            await self.task_service.fail_task(
                UUID(task_id), f"Failed to queue background task: {str(e)}"
            )
            raise

    async def _execute_analysis_task(
        self, task_id: UUID, command: AnalyzeFilingCommand
    ) -> None:
        """Execute the analysis task with progress tracking.

        Args:
            task_id: ID of the task being executed
            command: Analysis command to execute
        """
        try:
            # Step 1: Validate command
            command.validate()  # Ensures accession_number is not None

            # Step 2: Validate filing access (10% progress)
            await self.task_service.update_task_progress(
                task_id, 0.1, "Validating filing access"
            )

            # accession_number is guaranteed to be not None after validation
            assert command.accession_number is not None
            is_accessible = await self.analysis_orchestrator.validate_filing_access(
                command.accession_number
            )

            if not is_accessible:
                await self.task_service.fail_task(
                    task_id, f"Filing {command.accession_number} is not accessible"
                )
                return

            # Step 2: Start analysis orchestration (30% progress)
            await self.task_service.update_task_progress(
                task_id, 0.3, "Starting analysis workflow"
            )

            # Execute analysis with progress callbacks
            analysis = await self.analysis_orchestrator.orchestrate_filing_analysis(
                command,
                progress_callback=lambda progress, message: self._update_analysis_progress(
                    task_id, 0.3 + (progress * 0.7), message  # Map 0-100% to 30-100%
                ),
            )

            # Step 3: Complete task
            result = {
                "analysis_id": str(analysis.id),
                "filing_identifier": command.filing_identifier,
                "analysis_template": command.analysis_template.value,
                "confidence_score": analysis.confidence_score,
                "sections_analyzed": (
                    len(analysis.get_section_analyses())
                    if analysis.get_section_analyses()
                    else 0
                ),
                "processing_time": analysis.get_processing_time(),
            }

            await self.task_service.complete_task(
                task_id, result, f"Analysis completed for {command.filing_identifier}"
            )

            logger.info(
                f"Analysis task {task_id} completed successfully",
                extra={
                    "analysis_id": str(analysis.id),
                    "confidence_score": analysis.confidence_score,
                    "processing_time": analysis.get_processing_time(),
                },
            )

        except Exception as e:
            await self.task_service.fail_task(task_id, f"Analysis failed: {str(e)}")
            logger.error(
                f"Analysis task {task_id} failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def _update_analysis_progress(
        self, task_id: UUID, progress: float, message: str
    ) -> None:
        """Update analysis progress (callback for orchestrator).

        Args:
            task_id: ID of the task being updated
            progress: Progress percentage (0.0 to 1.0)
            message: Progress message
        """
        await self.task_service.update_task_progress(task_id, progress, message)

    async def get_task_status(self, task_id: UUID) -> TaskResponse | None:
        """Get status of a background task.

        Args:
            task_id: ID of the task to check

        Returns:
            TaskResponse with current status, or None if not found
        """
        return await self.task_service.get_task_status(task_id)

    async def retry_failed_task(self, task_id: UUID) -> TaskResponse | None:
        """Retry a failed analysis task.

        Args:
            task_id: ID of the failed task to retry

        Returns:
            TaskResponse for the retry attempt, or None if task not found
        """
        current_status = await self.task_service.get_task_status(task_id)

        if not current_status or current_status.status != "failed":
            logger.warning(f"Cannot retry task {task_id}: task not found or not failed")
            return None

        # Get original task parameters
        task_info = self.task_service.tasks.get(task_id)
        if not task_info:
            return None

        original_params = task_info["parameters"]

        # Create new command from original parameters
        from src.domain.value_objects.accession_number import AccessionNumber
        from src.domain.value_objects.cik import CIK

        retry_command = AnalyzeFilingCommand(
            company_cik=CIK(original_params["company_cik"]),
            accession_number=AccessionNumber(original_params["accession_number"]),
            analysis_template=original_params["analysis_template"],
            force_reprocess=True,  # Force reprocess on retry
            user_id=task_info["user_id"],
        )

        logger.info(
            f"Retrying failed analysis task for {retry_command.filing_identifier}",
            extra={
                "original_task_id": str(task_id),
                "filing_identifier": retry_command.filing_identifier,
            },
        )

        # Queue new analysis
        return await self.queue_filing_analysis(retry_command)
