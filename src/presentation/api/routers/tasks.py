"""Task management endpoints for background task status tracking."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from src.application.containers.orchestrator import SSEConnectionManager
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.presentation.api.dependencies import (
    get_background_task_coordinator,
    get_sse_connection_manager,
)
from src.presentation.api.security import get_current_user, user_id_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Path parameter type for task IDs
TaskIdPath = Annotated[str, Path(description="Task ID for background task tracking")]
AuthenticatedUserDep = Annotated[AuthenticationResult, Depends(get_current_user)]


@router.get(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Get Task Status",
    description="Get the current status of a background task by its ID.",
)
async def get_task_status(
    task_id: TaskIdPath,
    current_user: AuthenticatedUserDep,
    coordinator: BackgroundTaskCoordinator = Depends(get_background_task_coordinator),
) -> TaskResponse:
    """Get status of a background task.

    Args:
        task_id: ID of the task to check
        coordinator: Background task coordinator dependency

    Returns:
        TaskResponse with current task status

    Raises:
        HTTPException: 404 if task not found, 500 if coordinator fails
    """
    logger.info(
        "Getting status for task",
        extra={"task_id": task_id, "user_id": user_id_str(current_user)},
    )

    try:
        task_status = await coordinator.get_task_status(task_id)

        if task_status is None:
            logger.warning(f"Task {task_id} not found")
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
            )

        logger.debug(f"Task {task_id} status: {task_status.status}")
        return task_status

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status",
        ) from e


@router.post(
    "/{task_id}/retry",
    response_model=TaskResponse,
    summary="Retry Failed Task",
    description="Retry a failed background task, creating a new task for the operation.",
)
async def retry_failed_task(
    task_id: TaskIdPath,
    current_user: AuthenticatedUserDep,
    coordinator: BackgroundTaskCoordinator = Depends(get_background_task_coordinator),
) -> TaskResponse:
    """Retry a failed analysis task.

    Args:
        task_id: ID of the failed task to retry
        coordinator: Background task coordinator dependency

    Returns:
        TaskResponse for the new retry task

    Raises:
        HTTPException: 404 if task not found or not in failed state, 500 if coordinator fails
    """
    logger.info(
        "Retrying failed task",
        extra={"task_id": task_id, "user_id": user_id_str(current_user)},
    )

    try:
        retry_task = await coordinator.retry_failed_task(task_id)

        if retry_task is None:
            logger.warning(f"Cannot retry task {task_id}: task not found or not failed")
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or not in failed state",
            )

        logger.info(
            f"Created retry task {retry_task.task_id} for original task {task_id}"
        )
        return retry_task

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retry task"
        ) from e


@router.get(
    "/{task_id}/stream",
    summary="Stream Task Updates",
    description="Stream real-time task updates using Server-Sent Events.",
)
async def stream_task_updates(
    task_id: TaskIdPath,
    current_user: AuthenticatedUserDep,
    sse_manager: SSEConnectionManager = Depends(get_sse_connection_manager),
    events: Annotated[
        list[str] | None, Query(description="Optional event types to subscribe to")
    ] = None,
) -> StreamingResponse:
    """Stream SSE updates for tasks processed by the authenticated user."""

    if current_user.user_id is None:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated user is missing an identifier",
        )

    event_types = None
    if events:
        filtered = [event.strip() for event in events if event.strip()]
        if filtered:
            event_types = list(dict.fromkeys(filtered))

    try:
        connection = await sse_manager.open_connection(
            user_id=current_user.user_id,
            event_types=event_types,
        )
    except Exception as exc:  # noqa: BLE001 - surface as HTTP error
        logger.error(
            "Failed to open SSE connection",
            exc_info=True,
            extra={"task_id": task_id, "user_id": user_id_str(current_user)},
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to establish SSE stream",
        ) from exc

    logger.info(
        "Opened SSE stream",
        extra={
            "task_id": task_id,
            "connection_id": connection.connection_id,
            "user_id": user_id_str(current_user),
            "event_types": event_types,
        },
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        stream = sse_manager.stream_events(connection.connection_id)
        try:
            async for payload in stream:
                yield payload
        except asyncio.CancelledError:
            logger.info(
                "SSE stream cancelled",
                extra={
                    "task_id": task_id,
                    "connection_id": connection.connection_id,
                },
            )
            raise
        except Exception:
            logger.error(
                "Error while streaming SSE events",
                exc_info=True,
                extra={
                    "task_id": task_id,
                    "connection_id": connection.connection_id,
                },
            )
            raise
        finally:
            await sse_manager.close_connection(
                connection.connection_id,
                user_id=current_user.user_id,
            )
            logger.info(
                "Closed SSE stream",
                extra={
                    "task_id": task_id,
                    "connection_id": connection.connection_id,
                },
            )

    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    response.headers.update(
        {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
    return response
