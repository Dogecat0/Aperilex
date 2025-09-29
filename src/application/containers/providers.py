"""
Providers container for managing external service providers.
"""

from dependency_injector import containers, providers

from src.application.interfaces.authentication import IAuthenticationProvider
from src.application.interfaces.database import IDatabaseProvider
from src.application.interfaces.datasource import IDataSourceProvider
from src.application.interfaces.events import IEventPublisher, IEventStore
from src.application.interfaces.llm import ILLMProvider
from src.application.interfaces.queue import IQueueProvider
from src.application.interfaces.rate_limiting import IRateLimitingProvider
from src.application.interfaces.sse import ISSEProvider
from src.application.interfaces.storage import IStorageProvider
from src.application.interfaces.worker import IWorkerProvider
from src.shared.enums import (
    AuthenticationProvider,
    DatabaseProvider,
    DataSourceProvider,
    LLMProvider,
    QueueProvider,
    RateLimitingProvider,
    StorageProvider,
    WorkerProvider,
)


class ProvidersContainer(containers.DeclarativeContainer):
    """Container for all external service providers."""

    # Provider configuration from parent container
    config = providers.DependenciesContainer()

    # Storage provider (S3, Local, etc.)
    storage_provider_type = providers.Object(StorageProvider.LOCAL)
    storage_provider = providers.AbstractSingleton(IStorageProvider)

    # Queue provider (SQS, RabbitMQ, etc.)
    queue_provider_type = providers.Object(QueueProvider.RABBITMQ)
    queue_provider = providers.AbstractSingleton(IQueueProvider)

    # Worker provider (Lambda, Docker, etc.)
    worker_provider_type = providers.Object(WorkerProvider.DOCKER)
    worker_provider = providers.AbstractSingleton(IWorkerProvider)

    # LLM provider (OpenAI, Bedrock, etc.)
    llm_provider_type = providers.Object(LLMProvider.OPENAI)
    llm_provider = providers.AbstractSingleton(ILLMProvider)

    # Data source provider (EDGAR, etc.)
    data_source_provider_type = providers.Object(DataSourceProvider.EDGAR)
    data_source_provider = providers.AbstractSingleton(IDataSourceProvider)

    # Database provider (Postgres, Aurora, etc.)
    database_provider_type = providers.Object(DatabaseProvider.POSTGRES)
    database_provider = providers.AbstractSingleton(IDatabaseProvider)

    # Rate limiting provider (InMemory, etc.)
    rate_limiting_provider_type = providers.Object(RateLimitingProvider.IN_MEMORY)
    rate_limiting_provider = providers.AbstractSingleton(IRateLimitingProvider)

    # Event publisher for domain events and SSE
    event_publisher = providers.AbstractSingleton(IEventPublisher)

    # Event store for event sourcing / replay support
    event_store = providers.AbstractSingleton(IEventStore)

    # Authentication provider for API security
    authentication_provider_type = providers.Object(AuthenticationProvider.MOCK)
    authentication_provider = providers.AbstractSingleton(IAuthenticationProvider)

    # SSE provider for real-time updates
    sse_provider = providers.AbstractSingleton(ISSEProvider)
