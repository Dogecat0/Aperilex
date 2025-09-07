"""
Queue-related value objects.
"""

import re
from typing import Any

from pydantic import BaseModel, field_validator


class DeduplicationId(BaseModel):
    """Queue message deduplication identifier."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_deduplication_id(cls, v: str) -> str:
        """Validate deduplication ID format."""
        v = v.strip()
        if not v:
            raise ValueError("Deduplication ID cannot be empty")

        # AWS SQS allows up to 128 characters
        if len(v) > 128:
            raise ValueError("Deduplication ID must be 128 characters or less")

        # Allow alphanumeric characters with hyphens, underscores, and dots
        if not re.match(r"^[a-zA-Z0-9\-_.]+$", v):
            raise ValueError(f"Invalid deduplication ID format: {v}")

        return v

    def __str__(self) -> str:
        """Return deduplication ID as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another DeduplicationId."""
        if not isinstance(other, DeduplicationId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True


class MessageGroupId(BaseModel):
    """Queue message group identifier for FIFO queues."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_message_group_id(cls, v: str) -> str:
        """Validate message group ID format."""
        v = v.strip()
        if not v:
            raise ValueError("Message group ID cannot be empty")

        # AWS SQS allows up to 128 characters
        if len(v) > 128:
            raise ValueError("Message group ID must be 128 characters or less")

        # Allow alphanumeric characters with hyphens, underscores, and dots
        if not re.match(r"^[a-zA-Z0-9\-_.]+$", v):
            raise ValueError(f"Invalid message group ID format: {v}")

        return v

    def __str__(self) -> str:
        """Return message group ID as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another MessageGroupId."""
        if not isinstance(other, MessageGroupId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True


class VisibilityTimeout(BaseModel):
    """Queue message visibility timeout in seconds."""

    value: int

    @field_validator("value")
    @classmethod
    def validate_visibility_timeout(cls, v: int) -> int:
        """Validate visibility timeout constraints."""
        # AWS SQS limits: 0 to 43200 seconds (12 hours)
        if not 0 <= v <= 43200:
            raise ValueError(
                f"Visibility timeout must be between 0 and 43200 seconds, got {v}"
            )
        return v

    def __int__(self) -> int:
        """Return visibility timeout as integer."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another VisibilityTimeout."""
        if not isinstance(other, VisibilityTimeout):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True
