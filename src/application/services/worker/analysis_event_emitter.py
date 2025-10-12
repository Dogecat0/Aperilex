"""
Event emission collaborator extracted from the legacy WorkerService.

This service centralises construction and publishing of analysis lifecycle
events so the orchestrator can delegate notifications without replicating
payload assembly or publisher guarding logic.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, cast

from src.application.interfaces.events import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    AnalysisProgressEvent,
    AnalysisStartedEvent,
    FilingImportedEvent,
    IEventPublisher,
)
from src.shared.models import AnalysisRequest, AnalysisResult, TaskData
from src.shared.types import AnalysisId, StorageKey
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


ProgressCallback = (
    Callable[[float, str], None]
    | Callable[[float, str], Coroutine[Any, Any, None]]
    | None
)


class AnalysisEventEmitter:
    """Publish analysis lifecycle events and track progress."""

    def __init__(self, event_publisher: IEventPublisher | None = None) -> None:
        self.event_publisher = event_publisher

    async def publish_analysis_started_event(
        self,
        task_data: TaskData,
        analysis_request: AnalysisRequest,
    ) -> None:
        """Emit AnalysisStartedEvent mirroring legacy behaviour."""

        if not self.event_publisher:
            return

        metadata = {
            "analysis_type": analysis_request.analysis_type.value,
            "analysis_template": task_data.metadata.get("analysis_template"),
            "source": task_data.source,
            "priority": task_data.priority.name,
            "retry_count": str(task_data.retry_count),
        }

        event = AnalysisStartedEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=analysis_request.correlation_id or task_data.correlation_id,
            user_id=task_data.user_id,
            analysis_id=analysis_request.analysis_id,
            filing_id=analysis_request.filing_id,
            task_id=task_data.task_id,
            metadata={k: v for k, v in metadata.items() if v is not None},
        )

        try:
            await self.event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to publish AnalysisStartedEvent",
                extra={
                    "task_id": str(task_data.task_id),
                    "analysis_id": str(analysis_request.analysis_id),
                },
                exc_info=True,
            )
            logger.debug(
                "AnalysisStartedEvent publish error", extra={"error": str(exc)}
            )

    async def publish_progress_event(
        self,
        *,
        analysis_request: AnalysisRequest,
        task_data: TaskData,
        progress: float,
        message: str,
    ) -> None:
        """Emit AnalysisProgressEvent with percentage guarding."""

        if not self.event_publisher:
            return

        percentage = max(0, min(100, int(round(progress * 100))))

        event = AnalysisProgressEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=analysis_request.correlation_id or task_data.correlation_id,
            user_id=task_data.user_id,
            analysis_id=analysis_request.analysis_id,
            progress_percentage=percentage,
            current_step=message,
            message=message,
            metadata={
                "task_id": str(task_data.task_id),
                "filing_id": str(analysis_request.filing_id),
                "analysis_type": analysis_request.analysis_type.value,
            },
        )

        try:
            await self.event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to publish AnalysisProgressEvent",
                extra={
                    "task_id": str(task_data.task_id),
                    "analysis_id": str(analysis_request.analysis_id),
                    "progress": percentage,
                },
                exc_info=True,
            )
            logger.debug(
                "AnalysisProgressEvent publish error", extra={"error": str(exc)}
            )

    async def publish_filing_imported_event(
        self,
        *,
        task_data: TaskData,
        storage_key: StorageKey,
    ) -> None:
        """Emit FilingImportedEvent when storage completes."""

        if not self.event_publisher:
            return

        metadata = task_data.metadata or {}
        filing_date = metadata.get("filing_date")
        if not filing_date:
            filing_date = datetime.now(UTC).date().isoformat()

        event = FilingImportedEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=task_data.correlation_id,
            user_id=task_data.user_id,
            filing_id=task_data.filing_id,
            ticker=str(task_data.ticker),
            filing_type=task_data.filing_type.value,
            filing_date=filing_date,
            metadata={
                "storage_key": str(storage_key),
                "requested_by": metadata.get("requested_by"),
                "analysis_template": metadata.get("analysis_template"),
            },
        )

        try:
            await self.event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to publish FilingImportedEvent",
                extra={
                    "filing_id": str(task_data.filing_id),
                    "task_id": str(task_data.task_id),
                },
                exc_info=True,
            )
            logger.debug("FilingImportedEvent publish error", extra={"error": str(exc)})

    async def publish_completion_event(
        self,
        task_data: TaskData,
        result: AnalysisResult,
        storage_key: StorageKey,
    ) -> None:
        """Emit AnalysisCompletedEvent and log completion payload."""

        event_timestamp = datetime.now(UTC).isoformat()
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "email": str(task_data.email),
            "analysis_id": str(result.analysis_id),
            "filing_id": str(result.filing_id),
            "status": "success" if result.is_successful else "failed",
            "storage_key": str(storage_key),
            "timestamp": event_timestamp,
        }

        logger.info("Publishing completion event", extra=event_payload)

        if not self.event_publisher:
            return

        correlation_id = (
            result.correlation_id
            if result.correlation_id is not None
            else task_data.correlation_id
        )

        event = AnalysisCompletedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_timestamp,
            correlation_id=correlation_id,
            user_id=result.user_id,
            analysis_id=result.analysis_id,
            filing_id=result.filing_id,
            task_id=task_data.task_id,
            storage_key=str(storage_key),
            processing_time_ms=result.processing_time_ms,
            metadata={"status": result.status.value},
        )

        await self.event_publisher.publish(event)

    async def publish_failure_event(
        self,
        task_data: TaskData,
        analysis_id: AnalysisId | None,
        error_message: str,
    ) -> None:
        """Emit AnalysisFailedEvent and log error context."""

        event_timestamp = datetime.now(UTC).isoformat()
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "analysis_id": str(analysis_id) if analysis_id else None,
            "filing_id": str(task_data.filing_id),
            "error_message": error_message,
            "retry_count": task_data.retry_count,
            "timestamp": event_timestamp,
        }

        logger.error(
            "Publishing failure event",
            extra=event_payload,
        )

        if not self.event_publisher:
            return

        event = AnalysisFailedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_timestamp,
            correlation_id=task_data.correlation_id,
            analysis_id=analysis_id,
            filing_id=task_data.filing_id,
            task_id=task_data.task_id,
            user_id=task_data.user_id,
            error_message=error_message,
            retry_count=task_data.retry_count,
        )

        await self.event_publisher.publish(event)

    async def track_progress(
        self,
        progress_callback: ProgressCallback,
        progress: float,
        message: str,
        *,
        analysis_request: AnalysisRequest | None,
        task_data: TaskData | None,
    ) -> None:
        """Invoke progress callbacks and emit progress events when configured."""

        if progress_callback:
            try:
                if inspect.iscoroutinefunction(progress_callback):
                    await cast(Awaitable[None], progress_callback(progress, message))
                else:
                    progress_callback(progress, message)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Progress callback failed",
                    extra={
                        "progress": progress,
                        "message": message,
                        "error": str(exc),
                    },
                )

        logger.info("Task progress: %.1f%% - %s", progress * 100, message)

        if (
            self.event_publisher is not None
            and analysis_request is not None
            and task_data is not None
        ):
            await self.publish_progress_event(
                analysis_request=analysis_request,
                task_data=task_data,
                progress=progress,
                message=message,
            )
