"""Background task coordinator for managing long-running analysis operations."""

import logging

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
                original_task_id = task_response.task_id
                celery_task_id = await self._queue_celery_task(
                    task_response.task_id, command
                )
                # Create new TaskResponse with Celery task ID for frontend polling when using Celery
                from src.application.schemas.responses.task_response import TaskResponse

                task_response = TaskResponse(
                    task_id=celery_task_id,
                    status=task_response.status,
                    result=task_response.result,
                    error_message=task_response.error_message,
                    started_at=task_response.started_at,
                    completed_at=task_response.completed_at,
                    progress_percent=task_response.progress_percent,
                    current_step=task_response.current_step,
                )
                logger.info(
                    f"Updated task response to use Celery task ID {celery_task_id} for frontend polling",
                    extra={
                        "original_task_id": str(original_task_id),
                        "celery_task_id": celery_task_id,
                        "filing_identifier": command.filing_identifier,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to queue Celery task {task_response.task_id}",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await self.task_service.fail_task(
                    task_response.task_id, f"Failed to queue task: {str(e)}"
                )
        else:
            # Process synchronously for development/testing
            try:
                await self._execute_analysis_task(task_response.task_id, command)
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
    ) -> str:
        """Queue analysis task using Celery.

        Args:
            task_id: ID of the task to execute
            command: Analysis command to execute

        Returns:
            Celery task ID for polling
        """
        try:
            from src.infrastructure.tasks.analysis_tasks import analyze_filing_task

            # Queue the Celery task
            celery_task = analyze_filing_task.delay(
                filing_id=str(command.accession_number),
                analysis_template=command.analysis_template.value,
                created_by=command.user_id,
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
                task_id, 0.05, "Queued for background processing"
            )

            return str(celery_task.id)

        except ImportError as e:
            logger.error(f"Celery tasks not available: {e}")
            # Fallback to synchronous processing
            await self._execute_analysis_task(task_id, command)
            return task_id
        except Exception as e:
            logger.error(f"Failed to queue Celery task: {e}")
            await self.task_service.fail_task(
                task_id, f"Failed to queue background task: {str(e)}"
            )
            raise

    async def _execute_analysis_task(
        self, task_id: str, command: AnalyzeFilingCommand
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
            if command.accession_number is None:
                raise ValueError("Accession number is required after validation")
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
                    task_id,
                    0.3 + (progress * 0.7),
                    message,  # Map 0-100% to 30-100%
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
        self, task_id: str, progress: float, message: str
    ) -> None:
        """Update analysis progress (callback for orchestrator).

        Args:
            task_id: ID of the task being updated
            progress: Progress percentage (0.0 to 1.0)
            message: Progress message
        """
        await self.task_service.update_task_progress(task_id, progress, message)

    async def get_task_status(self, task_id: str) -> TaskResponse | None:
        """Get status of a background task.

        Args:
            task_id: ID of the task to check (either application task ID or Celery task ID)

        Returns:
            TaskResponse with current status, or None if not found
        """
        # First try to get from TaskService (for non-Celery tasks or application task IDs)
        task_status = await self.task_service.get_task_status(task_id)
        if task_status is not None:
            return task_status

        # If not found and Celery is enabled, try to query Celery task status
        if self.use_celery:
            try:
                from datetime import datetime

                from celery.result import AsyncResult  # type: ignore[import-untyped]

                from src.infrastructure.tasks.celery_app import celery_app

                # Query Celery for task status
                celery_result = AsyncResult(task_id, app=celery_app)

                # Extract timing information from Celery's result backend
                started_at = None
                completed_at = None
                progress_percent = None
                current_step = None

                try:
                    # Access Celery's internal task metadata (if available)
                    task_meta = celery_result._get_task_meta()
                    if task_meta:
                        # Extract timing information
                        if "date_done" in task_meta and task_meta["date_done"]:
                            completed_at = task_meta["date_done"]

                        # For progress information, check if info contains progress data
                        if celery_result.info and isinstance(celery_result.info, dict):
                            progress_percent = celery_result.info.get(
                                "current_progress"
                            )
                            current_step = celery_result.info.get("current_step")

                            # Extract started_at from task meta if available
                            if "started_at" in celery_result.info:
                                started_at_str = celery_result.info.get("started_at")
                                if started_at_str:
                                    try:
                                        from datetime import datetime

                                        started_at = datetime.fromisoformat(
                                            started_at_str.replace("Z", "+00:00")
                                        )
                                    except ValueError as e:
                                        logger.debug(
                                            f"Failed to parse started_at timestamp '{started_at_str}': {e}"
                                        )
                            # Convert progress to percentage if it's between 0 and 1
                            if (
                                progress_percent is not None
                                and 0 <= progress_percent <= 1
                            ):
                                progress_percent = progress_percent * 100

                except Exception as meta_error:
                    logger.debug(
                        f"Could not extract task metadata for {task_id}: {meta_error}"
                    )

                if celery_result.state == "PENDING":
                    # Task is waiting or doesn't exist
                    if celery_result.info is None:
                        # Task likely doesn't exist
                        return None
                    return TaskResponse(
                        task_id=task_id,
                        status="pending",
                        result=None,
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                elif celery_result.state == "STARTED":
                    return TaskResponse(
                        task_id=task_id,
                        status="started",
                        result=None,
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                elif celery_result.state == "SUCCESS":
                    return TaskResponse(
                        task_id=task_id,
                        status="success",
                        result=celery_result.result,
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=100.0,  # Task is complete
                        current_step="Completed",
                    )
                elif celery_result.state == "FAILURE":
                    return TaskResponse(
                        task_id=task_id,
                        status="failure",
                        result=None,
                        error_message=(
                            str(celery_result.info)
                            if celery_result.info
                            else "Task failed"
                        ),
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                elif celery_result.state == "RETRY":
                    return TaskResponse(
                        task_id=task_id,
                        status="retry",
                        result=None,
                        error_message=(
                            str(celery_result.info)
                            if celery_result.info
                            else "Task retrying"
                        ),
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                elif celery_result.state == "REVOKED":
                    return TaskResponse(
                        task_id=task_id,
                        status="revoked",
                        result=None,
                        error_message="Task was revoked",
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                elif celery_result.state == "PROGRESS":
                    return TaskResponse(
                        task_id=task_id,
                        status="progress",
                        result=None,
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )
                else:
                    # Custom state (like progress updates)
                    return TaskResponse(
                        task_id=task_id,
                        status=celery_result.state.lower(),
                        result=celery_result.info,
                        started_at=started_at,
                        completed_at=completed_at,
                        progress_percent=progress_percent,
                        current_step=current_step,
                    )

            except ImportError:
                logger.warning("Celery not available for task status query")
            except Exception as e:
                logger.error(f"Error querying Celery task status for {task_id}: {e}")

        return None

    async def retry_failed_task(self, task_id: str) -> TaskResponse | None:
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
