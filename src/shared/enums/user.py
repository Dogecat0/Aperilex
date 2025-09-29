"""
User-related enums.
"""

from enum import Enum


class UserTier(str, Enum):
    """User subscription tier levels."""

    DEMO = "DEMO"
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class UserStatus(str, Enum):
    """Lifecycle status for a user account."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
