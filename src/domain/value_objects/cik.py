"""Central Index Key (CIK) value object."""

import re
from typing import Any


class CIK:
    """Central Index Key - SEC company identifier.

    CIK is a 10-digit number assigned by the SEC to identify companies.
    It can be stored with or without leading zeros, but should be validated
    and can be formatted consistently.
    """

    def __init__(self, value: str) -> None:
        """Initialize CIK with validation.

        Args:
            value: CIK string (1-10 digits, leading zeros optional)

        Raises:
            ValueError: If CIK format is invalid
        """
        self._value = str(value).strip()
        self.validate()

    def validate(self) -> None:
        """Validate CIK format.

        Raises:
            ValueError: If CIK is not 1-10 digits
        """
        if not self._value:
            raise ValueError("CIK cannot be empty")

        if not re.match(r'^\d{1,10}$', self._value):
            raise ValueError("CIK must be 1-10 digits")

        # Convert to int and back to validate it's a valid number
        try:
            int(self._value)
        except ValueError as e:
            raise ValueError("CIK must be a valid number") from e

    def __str__(self) -> str:
        """Return CIK as string without leading zeros."""
        return str(int(self._value))

    def __eq__(self, other: Any) -> bool:
        """Check equality with another CIK."""
        if not isinstance(other, CIK):
            return False
        return int(self._value) == int(other._value)

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(int(self._value))

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"CIK('{self._value}')"

    def to_padded_string(self) -> str:
        """Return CIK as zero-padded 10-digit string.

        Returns:
            CIK formatted as 10-digit string with leading zeros
        """
        return str(int(self._value)).zfill(10)

    @property
    def value(self) -> str:
        """Return the raw CIK value."""
        return self._value
