#!/usr/bin/env python3
"""Aperilex background worker bootstrap using the CompositionRoot container."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

# Add project root to Python path for src imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.application.handlers.schemas.queries.get_analysis import (  # noqa: E402
    GetAnalysisQuery,
)
from src.application.interfaces.worker import WorkerContext  # noqa: E402
from src.application.services.application_service import (  # noqa: E402
    ApplicationService,
)
from src.application.services.priority_queue_service import (  # noqa: E402
    PriorityQueueService,
)
from src.application.services.worker_service import WorkerService  # noqa: E402
from src.composition import CompositionRoot  # noqa: E402
from src.shared.enums import TaskStatus  # noqa: E402
from src.shared.models.queue import TaskQueueMessage  # noqa: E402
from src.shared.types import CorrelationId, RequestId, TaskId  # noqa: E402


def setup_logging(level: str) -> None:
    """Configure structured logging for the worker process."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@dataclass(slots=True)
class WorkerRunner:
    """Simple worker loop that polls the queue and invokes WorkerService."""

    worker_service: WorkerService
    priority_queue: PriorityQueueService
    application_service: ApplicationService | None
    wait_time_seconds: int
    batch_size: int
    _stop_event: asyncio.Event = field(
        default_factory=asyncio.Event, init=False, repr=False
    )

    async def run(self) -> None:
        """Start processing queue messages until a shutdown signal is received."""

        self._install_signal_handlers()
        logging.info(
            "Worker loop started (wait_time=%s, batch_size=%s)",
            self.wait_time_seconds,
            self.batch_size,
        )

        while not self._stop_event.is_set():
            try:
                messages = await self.priority_queue.receive_tasks(
                    max_messages=self.batch_size,
                    wait_time_seconds=self.wait_time_seconds,
                )
            except Exception as exc:  # noqa: BLE001 - surface queue errors for diagnostics
                logging.error("Failed to receive messages: %s", exc, exc_info=True)
                await asyncio.sleep(min(self.wait_time_seconds, 5))
                continue

            if not messages:
                continue

            for message in messages:
                if self._stop_event.is_set():
                    break
                await self._process_message(message)

        logging.info("Worker loop stopped")

    def stop(self) -> None:
        """Signal the runner to stop after the current iteration."""

        if not self._stop_event.is_set():
            self._stop_event.set()

    async def _process_message(self, message: TaskQueueMessage) -> None:
        """Process a single queue message and handle acknowledgement."""

        message.receive_count += 1
        message.task_data["retry_count"] = max(message.receive_count - 1, 0)

        context = self._build_worker_context(message)

        try:
            result = await self.worker_service.process_task(message, context)
        except Exception as exc:  # noqa: BLE001 - keep worker alive on failure
            logging.error(
                "Worker processing failed for %s: %s",
                message.message_id,
                exc,
                exc_info=True,
            )
            return

        status = result.status
        logging.info(
            "Processed task %s with status %s",
            result.task_id,
            status.value,
            extra={
                "message_id": str(message.message_id),
                "retry_count": result.retry_count,
            },
        )

        if (
            status in (TaskStatus.COMPLETED, TaskStatus.RETRY)
            or message.should_move_to_dlq
        ):
            await self._acknowledge(message)

        await self._maybe_emit_dispatcher_metrics(message, result)

    async def _acknowledge(self, message: TaskQueueMessage) -> None:
        """Remove a processed message from the queue."""

        if not message.receipt_handle:
            logging.warning(
                "Cannot acknowledge message %s without receipt handle",
                message.message_id,
            )
            return

        success = await self.priority_queue.delete_task(message)
        if not success:
            logging.warning("Failed to delete message %s", message.message_id)

    async def _maybe_emit_dispatcher_metrics(
        self, message: TaskQueueMessage, result: Any
    ) -> None:
        """Optionally invoke the CQRS dispatcher for post-processing telemetry."""

        if self.application_service is None:
            return

        analysis_id = getattr(result, "analysis_id", None)
        if analysis_id is None:
            return

        user_identifier = (
            message.task_data.get("user_id") if message.task_data else None
        )

        try:
            query = GetAnalysisQuery(
                analysis_id=analysis_id,
                user_id=str(user_identifier) if user_identifier else None,
                include_full_results=False,
                include_processing_metadata=True,
            )
            await self.application_service.execute_query(query)
        except Exception:
            logging.debug(
                "Dispatcher query failed for analysis %s",
                analysis_id,
                exc_info=True,
            )

    def _build_worker_context(self, message: TaskQueueMessage) -> WorkerContext:
        """Create a WorkerContext matching the queue payload."""

        payload = message.task_data

        correlation = payload.get("correlation_id") or str(uuid4())
        payload["correlation_id"] = correlation

        task_id_raw = payload.get("task_id")
        task_uuid = (
            task_id_raw if isinstance(task_id_raw, UUID) else UUID(str(task_id_raw))
        )

        retry_attempt = self._coerce_int(payload.get("retry_count"), default=0)
        max_retries = self._coerce_int(payload.get("max_retries"), default=3)

        metadata = payload.get("metadata") or {}
        timeout_seconds = self._coerce_int(metadata.get("timeout_seconds"), default=300)

        return WorkerContext(
            schema_version=1,
            correlation_id=CorrelationId(correlation),
            task_id=TaskId(task_uuid),
            request_id=RequestId(str(uuid4())),
            provider=self.worker_service.worker_provider_type,
            start_time=datetime.now(UTC),
            timeout_seconds=timeout_seconds,
            retry_attempt=retry_attempt,
            max_retries=max_retries,
            enable_strict_validation=True,
            metadata=None,
            tags={},
        )

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.stop)


async def async_main(args: argparse.Namespace) -> None:
    """Initialize DI container, log provider info, and start the worker loop."""

    environment = args.environment or os.getenv("ENVIRONMENT", "development")
    composition_root = CompositionRoot.initialize(environment)
    app_container = composition_root.get_application_container()

    providers_container = app_container.providers_container()
    cqrs_container = app_container.cqrs()

    handler_registrar = cqrs_container.handler_registrar()
    handler_registrar.register_all_handlers()
    logging.info("CQRS handlers registered for worker runtime")

    queue_provider_type = providers_container.queue_provider_type()
    worker_provider_type = providers_container.worker_provider_type()

    logging.info(
        "Worker bootstrap complete (env=%s, queue_provider=%s, worker_provider=%s)",
        environment,
        queue_provider_type,
        worker_provider_type,
    )

    priority_queue: PriorityQueueService = cqrs_container.priority_queue()
    worker_service: WorkerService = cqrs_container.worker_service()
    application_service: ApplicationService = cqrs_container.application_service()

    runner = WorkerRunner(
        worker_service=worker_service,
        priority_queue=priority_queue,
        application_service=application_service,
        wait_time_seconds=args.wait_time,
        batch_size=args.batch_size,
    )

    try:
        await runner.run()
    finally:
        runner.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment",
        choices=["development", "testing", "production"],
        help="Environment to load (defaults to ENVIRONMENT or development)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level for the worker process",
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=20,
        help="Long polling wait time in seconds",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Maximum number of messages to process per poll",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logging.info("Worker interrupted by user")
    except Exception as exc:  # noqa: BLE001 - log unexpected failures
        logging.error("Worker terminated with error: %s", exc, exc_info=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
