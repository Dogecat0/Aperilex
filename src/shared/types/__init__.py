"""
Types module for identifiers and value objects.
"""

from .filing import FilingType
from .identifiers import (
    AnalysisId,
    CompanyId,
    CorrelationId,
    FilingId,
    QueueMessageId,
    ReceiptHandle,
    RequestId,
    StorageKey,
    TaskId,
    UserId,
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
    "StorageKey",
    "QueueMessageId",
    "ReceiptHandle",
    "RequestId",
    "CorrelationId",
    # SEC types
    "FilingType",
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
