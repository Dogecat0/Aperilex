"""
Shared module for domain value objects, types, enums, and utilities.
"""

# Re-export from submodules for backward compatibility
from .enums import (
    AnalysisStatus,
    DatabaseProvider,
    DataSourceProvider,
    LLMProvider,
    QueueProvider,
    StorageProvider,
    TaskPriority,
    TaskStatus,
    WorkerProvider,
)
from .models import (
    LLMModelInfo,
    MetadataDict,
    MetadataValue,
    QueueMessage,
    QueueMessageBody,
    StorageMetadataFields,
    TaskMessage,
    TaskMetadata,
)
from .types import (
    CIK,
    URL,
    AccessionNumber,
    AnalysisId,
    CompanyId,
    CorrelationId,
    DeduplicationId,
    Email,
    FilingId,
    MessageGroupId,
    QueueMessageId,
    ReceiptHandle,
    RequestId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
    VisibilityTimeout,
)
from .utils import SecRateLimiter

__all__ = [
    # Enums
    "StorageProvider",
    "QueueProvider",
    "WorkerProvider",
    "LLMProvider",
    "DataSourceProvider",
    "DatabaseProvider",
    "TaskStatus",
    "AnalysisStatus",
    "TaskPriority",
    # Identifiers
    "TaskId",
    "FilingId",
    "AnalysisId",
    "UserId",
    "CompanyId",
    "StorageKey",
    "QueueMessageId",
    "ReceiptHandle",
    "RequestId",
    "CorrelationId",
    # Value Objects
    "Email",
    "Ticker",
    "CIK",
    "URL",
    "DeduplicationId",
    "MessageGroupId",
    "VisibilityTimeout",
    "AccessionNumber",
    # Models - Base
    "MetadataValue",
    "MetadataDict",
    # Models - Task
    "TaskMetadata",
    "TaskMessage",
    # Models - Storage
    "StorageMetadataFields",
    # Models - Queue
    "QueueMessageBody",
    "QueueMessage",
    # Models - LLM
    "LLMModelInfo",
    # Utils
    "SecRateLimiter",
]
