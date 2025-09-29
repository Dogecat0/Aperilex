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
    UserStatus,
    UserTier,
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
    LearningProgressId,
    MessageGroupId,
    QueueMessageId,
    QuizAttemptId,
    ReceiptHandle,
    RequestId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
    UserIdentityId,
    UserProfileId,
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
    "UserTier",
    "UserStatus",
    # Identifiers
    "TaskId",
    "FilingId",
    "AnalysisId",
    "UserId",
    "UserIdentityId",
    "UserProfileId",
    "LearningProgressId",
    "QuizAttemptId",
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
