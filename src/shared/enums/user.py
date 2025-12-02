"""
User-related enums.
"""

from enum import Enum


class UserTier(str, Enum):
    """User subscription tier levels."""

    ESSENTIAL = "ESSENTIAL"
    PLUS = "PLUS"


class UserStatus(str, Enum):
    """Lifecycle status for a user account."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
