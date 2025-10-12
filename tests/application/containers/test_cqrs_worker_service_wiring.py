"""Ensure CQRS container wiring stays aligned with WorkerService dependencies."""

from dependency_injector import providers

from src.application.containers.cqrs import CQRSContainer
from src.application.containers.providers import ProvidersContainer


def _build_providers_container() -> ProvidersContainer:
    """Create a ProvidersContainer with lightweight stub implementations."""

    container = ProvidersContainer()

    # The CQRS container only inspects provider configuration when we read kwargs,
    # so simple lambda-backed singletons keep the wiring test-focused and cheap.
    container.storage_provider.override(providers.Singleton(lambda: "storage"))
    container.queue_provider.override(providers.Singleton(lambda: "queue"))
    container.worker_provider.override(providers.Singleton(lambda: "worker"))
    container.llm_provider.override(providers.Singleton(lambda: "llm"))
    container.data_source_provider.override(providers.Singleton(lambda: "datasource"))
    container.event_publisher.override(providers.Singleton(lambda: "publisher"))

    # These enums are accessed via providers.Object; the concrete values are irrelevant
    # for wiring assertions, so strings keep the setup lightweight.
    container.worker_provider_type.override(providers.Object("DOCKER"))
    container.queue_provider_type.override(providers.Object("RABBITMQ"))
    container.storage_provider_type.override(providers.Object("LOCAL"))

    return container


def test_worker_service_dependencies_match_constructor_signature() -> None:
    """The CQRS worker_service provider should only supply the new constructor kwargs."""

    providers_container = _build_providers_container()
    container = CQRSContainer(providers_container=providers_container)

    # Inspect provider configuration without instantiating WorkerService (avoids async concerns).
    worker_service_kwargs = set(container.worker_service.kwargs.keys())

    expected_kwargs = {
        "worker_provider_type",
        "repository_factory",
        "analysis_task_builder",
        "filing_lifecycle_service",
        "analysis_execution_service",
        "analysis_summary_builder",
        "template_registry",
        "analysis_persistence_service",
        "analysis_event_emitter",
        "worker_retry_coordinator",
        "priority_queue",
    }

    assert worker_service_kwargs == expected_kwargs, (
        "WorkerService provider wiring drifted from constructor signature. "
        f"Current kwargs: {worker_service_kwargs}"
    )
