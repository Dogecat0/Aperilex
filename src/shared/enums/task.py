"""
Task-related enums.
"""

from enum import Enum


class TaskPriority(int, Enum):
    """Task priority levels (lower number = higher priority)."""

    CRITICAL = 0
    HIGH = 2
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9
