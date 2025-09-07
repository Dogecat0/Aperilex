"""
Status enums for task and analysis processing states.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task processing status."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    RETRY = "RETRY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnalysisStatus(str, Enum):
    """Analysis processing status."""

    INITIATED = "INITIATED"
    FETCHING = "FETCHING"
    PARSING = "PARSING"
    ANALYZING = "ANALYZING"
    STORING = "STORING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"
