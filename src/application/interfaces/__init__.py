"""
Provider interfaces for dependency injection and abstraction.
"""

from .authentication import (
    AuthenticationCredentials,
    AuthenticationError,
    AuthenticationResult,
    AuthorizationError,
    IAuthenticationProvider,
    RateLimitInfo,
)
from .config import IConfigProvider
from .database import IDatabaseProvider
from .datasource import IDataSourceProvider
from .events import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    AnalysisProgressEvent,
    AnalysisStartedEvent,
    DomainEvent,
    EventPublishError,
    FilingImportedEvent,
    IEventPublisher,
    IEventSubscriber,
    SSEConnectionEvent,
    TaskProcessingEvent,
    TaskQueuedEvent,
)
from .llm import ILLMProvider
from .queue import IQueueProvider
from .secret import ISecretManager
from .sse import ISSEProvider, SSEConnection, SSEConnectionError, SSEMessage
from .storage import IStorageProvider
from .worker import IWorkerProvider

__all__ = [
    "IStorageProvider",
    "IQueueProvider",
    "IWorkerProvider",
    "ILLMProvider",
    "IDataSourceProvider",
    "IDatabaseProvider",
    "IConfigProvider",
    "ISecretManager",
    "IEventPublisher",
    "IEventSubscriber",
    "DomainEvent",
    "FilingImportedEvent",
    "AnalysisStartedEvent",
    "AnalysisProgressEvent",
    "AnalysisCompletedEvent",
    "AnalysisFailedEvent",
    "TaskQueuedEvent",
    "TaskProcessingEvent",
    "SSEConnectionEvent",
    "EventPublishError",
    "IAuthenticationProvider",
    "AuthenticationCredentials",
    "AuthenticationResult",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitInfo",
    "ISSEProvider",
    "SSEConnection",
    "SSEMessage",
    "SSEConnectionError",
]
