"""
UUID-based identifiers for type safety across the system.
"""

from typing import NewType
from uuid import UUID

# Entity Identifiers (UUID-based)
TaskId = NewType("TaskId", UUID)
FilingId = NewType("FilingId", UUID)
AnalysisId = NewType("AnalysisId", UUID)
UserId = NewType("UserId", UUID)
CompanyId = NewType("CompanyId", UUID)

# Service Identifiers (String-based)
StorageKey = NewType("StorageKey", str)
QueueMessageId = NewType("QueueMessageId", str)
ReceiptHandle = NewType("ReceiptHandle", str)
RequestId = NewType("RequestId", str)
CorrelationId = NewType("CorrelationId", str)
