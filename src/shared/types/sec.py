"""
SEC-related value objects.
"""

import re
from typing import Any

from pydantic import BaseModel, field_validator


class Ticker(BaseModel):
    """Stock ticker symbol (1-5 alphanumeric characters)."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Validate ticker format."""
        v = v.strip().upper()
        if not v:
            raise ValueError("Ticker cannot be empty")

        # Allow letters, numbers, dots, and hyphens (common in ticker symbols)
        if not re.match(r"^[A-Z0-9.\-]{1,10}$", v):
            raise ValueError(
                "Ticker must be 1-10 characters and contain only uppercase letters, "
                "numbers, dots, and hyphens"
            )

        return v

    def __str__(self) -> str:
        """Return ticker as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another ticker."""
        if not isinstance(other, Ticker):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True


class CIK(BaseModel):
    """10-digit SEC Central Index Key."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_cik(cls, v: str) -> str:
        """Validate CIK format."""
        v = v.strip()
        if not v:
            raise ValueError("CIK cannot be empty")

        if not re.match(r"^\d{1,10}$", v):
            raise ValueError("CIK must be 1-10 digits")

        # Validate it's a valid number
        try:
            int(v)
        except ValueError as e:
            raise ValueError("CIK must be a valid number") from e

        return v

    def padded(self) -> str:
        """Return CIK padded with leading zeros to 10 digits."""
        return self.value.zfill(10)

    def __str__(self) -> str:
        """Return CIK as string without leading zeros."""
        return str(int(self.value))

    def __eq__(self, other: Any) -> bool:
        """Check equality with another CIK."""
        if not isinstance(other, CIK):
            return False
        return int(self.value) == int(other.value)

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(int(self.value))

    class Config:
        """Pydantic configuration."""

        frozen = True


class AccessionNumber(BaseModel):
    """SEC Accession Number (20-character unique identifier).

    Format: 0000000000-00-000000
    - First 10 digits: CIK of the entity
    - Next 2 digits: Year (YY)
    - Last 6 digits: Sequential count for the year
    """

    value: str

    @field_validator("value")
    @classmethod
    def validate_accession_number(cls, v: str) -> str:
        """Validate accession number format."""
        v = v.strip()
        if not v:
            raise ValueError("Accession number cannot be empty")

        # Remove hyphens for validation if present
        clean_value = v.replace("-", "")

        # Should be exactly 18 digits after removing hyphens
        if len(clean_value) != 18:
            raise ValueError(
                f"Accession number must be 18 digits (formatted as 0000000000-00-000000), got {v}"
            )

        # Check if all characters are digits
        if not clean_value.isdigit():
            raise ValueError(
                f"Accession number must contain only digits and hyphens, got {v}"
            )

        # If no hyphens, add them in the correct positions
        if "-" not in v:
            v = f"{clean_value[:10]}-{clean_value[10:12]}-{clean_value[12:]}"
        else:
            # Validate hyphen positions
            parts = v.split("-")
            if len(parts) != 3:
                raise ValueError(
                    f"Accession number must have exactly 2 hyphens, got {v}"
                )
            if len(parts[0]) != 10 or len(parts[1]) != 2 or len(parts[2]) != 6:
                raise ValueError(
                    f"Accession number format must be 10-2-6 digits (0000000000-00-000000), got {v}"
                )

        return v

    def get_cik(self) -> str:
        """Extract the CIK portion from the accession number."""
        return self.value[:10]

    def get_year(self) -> str:
        """Extract the year portion from the accession number."""
        return self.value[11:13]

    def get_sequence(self) -> str:
        """Extract the sequence portion from the accession number."""
        return self.value[14:]

    def __str__(self) -> str:
        """Return accession number as string."""
        return self.value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another AccessionNumber."""
        if not isinstance(other, AccessionNumber):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self.value)

    class Config:
        """Pydantic configuration."""

        frozen = True
