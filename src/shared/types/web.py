"""
Web and communication value objects.
"""

import re
from typing import Any

from pydantic import BaseModel, field_validator


class Email(BaseModel):
    """Validated email address value object."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        v = v.strip().lower()
        if not v:
            raise ValueError("Email cannot be empty")

        # Basic email validation pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")

        return v

    def __str__(self) -> str:
        """Return email as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another email."""
        if not isinstance(other, Email):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True


class URL(BaseModel):
    """Validated URL value object."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")

        # Basic URL validation pattern
        url_pattern = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v):
            raise ValueError(f"Invalid URL format: {v}")

        return v

    def __str__(self) -> str:
        """Return URL as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another URL."""
        if not isinstance(other, URL):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True
