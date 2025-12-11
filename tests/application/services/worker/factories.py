"""Shared factories for constructing worker-related collaborators in tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.application.services.priority_queue_service import PriorityQueueService
from src.application.services.worker import (
    AnalysisEventEmitter,
    AnalysisExecutionService,
    AnalysisPersistenceService,
    AnalysisSummaryBuilder,
    AnalysisTaskBuilder,
    FilingLifecycleService,
    TemplateRegistry,
    WorkerRetryCoordinator,
)
from src.application.services.worker_service import WorkerService
from src.shared.enums import WorkerProvider


def build_worker_service(
    *,
    storage_provider: Any | None = None,
    queue_provider: Any | None = None,
    llm_provider: Any | None = None,
    repository_factory: Any | None = None,
    event_publisher: Any | None = None,
    priority_queue: PriorityQueueService | None = None,
) -> WorkerService:
    """Construct a WorkerService instance with extracted collaborators."""

    storage = storage_provider or MagicMock()
    queue = queue_provider or MagicMock()
    llm = llm_provider or MagicMock()
    repository = repository_factory or MagicMock()
    publisher = event_publisher or MagicMock()

    task_builder = AnalysisTaskBuilder()
    template_registry = TemplateRegistry()
    filing_lifecycle = FilingLifecycleService(
        storage=storage,
        repository_factory=repository,
        template_registry=template_registry,
    )
    execution_service = AnalysisExecutionService(
        llm_provider=llm,
        storage=storage,
        template_registry=template_registry,
    )
    summary_builder = AnalysisSummaryBuilder()
    persistence_service = AnalysisPersistenceService(
        repository_factory=repository,
        storage=storage,
    )
    event_emitter = AnalysisEventEmitter(event_publisher=publisher)
    retry_coordinator = WorkerRetryCoordinator(
        priority_queue=priority_queue,
        queue_provider=queue,
    )

    return WorkerService(
        worker_provider_type=WorkerProvider.DOCKER,
        repository_factory=repository,
        analysis_task_builder=task_builder,
        filing_lifecycle_service=filing_lifecycle,
        analysis_execution_service=execution_service,
        analysis_summary_builder=summary_builder,
        template_registry=template_registry,
        analysis_persistence_service=persistence_service,
        analysis_event_emitter=event_emitter,
        worker_retry_coordinator=retry_coordinator,
        priority_queue=priority_queue,
    )


__all__ = ["build_worker_service"]
