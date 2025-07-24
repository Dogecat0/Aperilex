"""Task management endpoints for background task status tracking."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.status import HTTP_404_NOT_FOUND

from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.presentation.api.dependencies import get_background_task_coordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Path parameter type for task IDs
TaskIdPath = Annotated[str, Path(description="Task ID for background task tracking")]


@router.get(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Get Task Status",
    description="Get the current status of a background task by its ID.",
)
async def get_task_status(
    task_id: TaskIdPath,
    coordinator: BackgroundTaskCoordinator = Depends(get_background_task_coordinator),
) -> TaskResponse:
    """Get status of a background task.

    Args:
        task_id: ID of the task to check
        coordinator: Background task coordinator dependency

    Returns:
        TaskResponse with current task status

    Raises:
        HTTPException: 404 if task not found
    """
    logger.info(f"Getting status for task {task_id}")

    task_status = await coordinator.get_task_status(task_id)

    if task_status is None:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )

    logger.debug(f"Task {task_id} status: {task_status.status}")
    return task_status


@router.post(
    "/{task_id}/retry",
    response_model=TaskResponse,
    summary="Retry Failed Task",
    description="Retry a failed background task, creating a new task for the operation.",
)
async def retry_failed_task(
    task_id: TaskIdPath,
    coordinator: BackgroundTaskCoordinator = Depends(get_background_task_coordinator),
) -> TaskResponse:
    """Retry a failed analysis task.

    Args:
        task_id: ID of the failed task to retry
        coordinator: Background task coordinator dependency

    Returns:
        TaskResponse for the new retry task

    Raises:
        HTTPException: 404 if task not found or not in failed state
    """
    logger.info(f"Retrying failed task {task_id}")

    retry_task = await coordinator.retry_failed_task(task_id)

    if retry_task is None:
        logger.warning(f"Cannot retry task {task_id}: task not found or not failed")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or not in failed state",
        )

    logger.info(f"Created retry task {retry_task.task_id} for original task {task_id}")
    return retry_task
