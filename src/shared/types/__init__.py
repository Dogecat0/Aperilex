"""
Types module for identifiers and value objects.
"""

from .identifiers import (
    AnalysisId,
    CompanyId,
    CorrelationId,
    FilingId,
    LearningProgressId,
    QueueMessageId,
    QuizAttemptId,
    ReceiptHandle,
    RequestId,
    StorageKey,
    TaskId,
    UserId,
    UserIdentityId,
    UserProfileId,
)
from .queue import DeduplicationId, MessageGroupId, VisibilityTimeout
from .sec import CIK, AccessionNumber, Ticker
from .web import URL, Email

__all__ = [
    # Identifiers
    "TaskId",
    "FilingId",
    "AnalysisId",
    "UserId",
    "CompanyId",
    "UserIdentityId",
    "UserProfileId",
    "LearningProgressId",
    "QuizAttemptId",
    "StorageKey",
    "QueueMessageId",
    "ReceiptHandle",
    "RequestId",
    "CorrelationId",
    # SEC types
    "Ticker",
    "CIK",
    "AccessionNumber",
    # Web types
    "Email",
    "URL",
    # Queue types
    "DeduplicationId",
    "MessageGroupId",
    "VisibilityTimeout",
]
