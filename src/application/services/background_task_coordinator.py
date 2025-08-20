"""Background task coordinator for managing long-running analysis operations using new messaging system."""

import logging
from uuid import UUID, uuid4

from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.task_service import TaskService
from src.infrastructure.messaging import task_service as messaging_task_service

logger = logging.getLogger(__name__)


class BackgroundTaskCoordinator:
    """Coordinator for managing background analysis tasks using the new messaging system.

    This service orchestrates long-running analysis operations by:
    - Creating task tracking entries
    - Queuing tasks to the new messaging system
    - Providing task status and result tracking
    - Supporting both immediate and background execution
    """

    def __init__(
        self,
        analysis_orchestrator: AnalysisOrchestrator,
        task_service: TaskService,
        use_background: bool = True,
    ) -> None:
        """Initialize the background task coordinator.

        Args:
            analysis_orchestrator: Service for analysis workflow coordination
            task_service: Service for task tracking and management
            use_background: Whether to use background task execution
        """
        self.analysis_orchestrator = analysis_orchestrator
        self.task_service = task_service
        self.use_background = use_background

    async def queue_filing_analysis(
        self, command: AnalyzeFilingCommand
    ) -> TaskResponse:
        """Queue a filing analysis for background processing.

        Args:
            command: Command containing analysis parameters

        Returns:
            TaskResponse with task tracking information
        """
        try:
            logger.info(f"Queuing analysis for filing {command.filing_identifier}")

            # Create task tracking entry
            task_id = str(uuid4())

            # Record task start in our tracking service
            await self.task_service.create_task(
                task_id=task_id,
                task_type="filing_analysis",
                parameters={
                    "company_cik": str(command.company_cik),
                    "accession_number": str(command.accession_number),
                    "analysis_template": command.analysis_template.value,
                    "force_reprocess": command.force_reprocess,
                    "llm_schemas": command.get_llm_schemas_to_use(),
                },
                user_id=None,
            )

            if self.use_background:
                # Queue task using proper messaging system abstraction
                result = await messaging_task_service.send_task(
                    task_name="retrieve_and_analyze_filing",
                    kwargs={
                        "company_cik": str(command.company_cik),
                        "accession_number": str(command.accession_number),
                        "analysis_template": command.analysis_template.value,
                        "force_reprocess": command.force_reprocess,
                        "llm_schemas": command.get_llm_schemas_to_use(),
                        "task_id": task_id,  # Pass task_id as parameter
                    },
                    queue="analysis_queue",
                    task_id=UUID(task_id),  # Pass the same task_id to messaging system
                )

                # Update task with messaging task ID
                await self.task_service.update_task_status(
                    task_id=task_id,
                    status="queued",
                    metadata={"messaging_task_id": result.id},
                )

                logger.info(
                    f"Analysis task queued with ID {task_id} (messaging ID: {result.id})"
                )

                return TaskResponse(
                    task_id=task_id,
                    status="queued",
                    result={
                        "message": "Analysis queued for background processing",
                        "filing_identifier": command.filing_identifier,
                        "company_cik": str(command.company_cik),
                        "accession_number": str(command.accession_number),
                        "analysis_template": command.analysis_template.value,
                        "messaging_task_id": result.id,
                    },
                )
            else:
                # Execute synchronously
                logger.info(f"Executing analysis synchronously for task {task_id}")

                await self.task_service.update_task_status(
                    task_id=task_id,
                    status="running",
                )

                try:
                    # Execute analysis directly
                    analysis = (
                        await self.analysis_orchestrator.orchestrate_filing_analysis(
                            command
                        )
                    )

                    # Update task as completed
                    await self.task_service.update_task_status(
                        task_id=task_id,
                        status="completed",
                        result={
                            "analysis_id": str(analysis.id),
                            "confidence_score": analysis.confidence_score,
                            "results_summary": (
                                analysis.results.get("summary")
                                if analysis.results
                                else None
                            ),
                        },
                    )

                    logger.info(f"Analysis completed synchronously for task {task_id}")

                    return TaskResponse(
                        task_id=task_id,
                        status="completed",
                        result={
                            "message": "Analysis completed successfully",
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                            "analysis_id": str(analysis.id),
                            "confidence_score": analysis.confidence_score,
                        },
                    )

                except Exception as e:
                    # Update task as failed
                    await self.task_service.update_task_status(
                        task_id=task_id, status="failed", error=str(e)
                    )

                    logger.error(
                        f"Analysis failed synchronously for task {task_id}: {e}"
                    )

                    return TaskResponse(
                        task_id=task_id,
                        status="failed",
                        error_message=f"Analysis failed: {str(e)}",
                        result={
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                        },
                    )

        except Exception as e:
            logger.error(f"Failed to queue analysis task: {e}")

            # Try to update task status if task was created
            try:
                await self.task_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    error=f"Failed to queue task: {str(e)}",
                )
            except Exception as update_error:
                logger.debug(
                    f"Could not update task status (task might not have been created yet): {update_error}"
                )

            return TaskResponse(
                task_id=task_id if "task_id" in locals() else str(uuid4()),
                status="failed",
                error_message=f"Failed to queue analysis: {str(e)}",
            )

    async def get_task_status(self, task_id: str) -> TaskResponse:
        """Get the status of a background task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse with current task status
        """
        try:
            # Get task from our tracking service (it handles messaging sync internally)
            task_data = await self.task_service.get_task_status(task_id)

            if not task_data:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            return TaskResponse(
                task_id=task_id,
                status=task_data.get("status", "unknown"),
                result=task_data.get("result"),
                error_message=task_data.get("error"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                progress_percent=task_data.get("progress_percent"),
                current_step=task_data.get("message", ""),
            )

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to get task status: {str(e)}",
            )

    async def cancel_task(self, task_id: str) -> TaskResponse:
        """Cancel a background task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse with cancellation result
        """
        try:
            # Get task from our tracking service
            task_data = await self.task_service.get_task_status(task_id)

            if not task_data:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            # Try to cancel messaging task (TaskService handles messaging integration)
            messaging_cancelled = await self.task_service.cancel_messaging_task(task_id)

            # Update our tracking to cancelled status
            await self.task_service.update_task_status(
                task_id=task_id, status="cancelled", message="Task cancelled by user"
            )

            return TaskResponse(
                task_id=task_id,
                status="cancelled",
                result={
                    "message": "Task cancelled successfully",
                    "messaging_cancelled": messaging_cancelled,
                    **task_data.get("metadata", {}),
                },
            )

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to cancel task: {str(e)}",
            )

    async def retry_failed_task(self, task_id: str) -> TaskResponse | None:
        """Retry a failed task by creating a new task with same parameters.

        Args:
            task_id: ID of the failed task to retry

        Returns:
            TaskResponse for new retry task, or None if cannot retry
        """
        try:
            # Get the original task
            task_data = await self.task_service.get_task_status(task_id)

            if not task_data:
                logger.warning(f"Cannot retry task {task_id}: task not found")
                return None

            if task_data.get("status") != "failed":
                logger.warning(
                    f"Cannot retry task {task_id}: task status is {task_data.get('status')}, not failed"
                )
                return None

            # Extract original parameters
            parameters = task_data.get("parameters", {})

            # Create new command from original parameters
            from src.application.schemas.commands.analyze_filing import (
                AnalysisTemplate,
                AnalyzeFilingCommand,
            )

            try:
                command = AnalyzeFilingCommand(
                    company_cik=parameters.get("company_cik"),
                    accession_number=parameters.get("accession_number"),
                    analysis_template=AnalysisTemplate(
                        parameters.get("analysis_template")
                    ),
                    force_reprocess=parameters.get("force_reprocess", False),
                )

                # Queue the retry as a new task
                retry_task = await self.queue_filing_analysis(command)

                logger.info(
                    f"Created retry task {retry_task.task_id} for original task {task_id}"
                )
                return retry_task

            except Exception as e:
                logger.error(
                    f"Failed to recreate command for retry of task {task_id}: {e}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return None
