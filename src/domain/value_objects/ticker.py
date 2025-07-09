"""Stock ticker symbol value object."""

import re
from typing import Any


class Ticker:
    """Stock ticker symbol.

    Ticker symbols are typically 1-5 uppercase letters used to identify
    publicly traded companies on stock exchanges.
    """

    def __init__(self, value: str) -> None:
        """Initialize ticker with validation.

        Args:
            value: Ticker symbol string (1-5 letters)

        Raises:
            ValueError: If ticker format is invalid
        """
        self._value = str(value).strip().upper()
        self.validate()

    def validate(self) -> None:
        """Validate ticker format.

        Raises:
            ValueError: If ticker is not 1-5 uppercase letters
        """
        if not self._value:
            raise ValueError("Ticker cannot be empty")

        if not re.match(r'^[A-Z]{1,5}$', self._value):
            raise ValueError("Ticker must be 1-5 uppercase letters")

    def __str__(self) -> str:
        """Return ticker as string."""
        return self._value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another ticker."""
        if not isinstance(other, Ticker):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"Ticker('{self._value}')"

    def normalize(self) -> str:
        """Return normalized ticker (uppercase).

        Returns:
            Ticker symbol in uppercase
        """
        return self._value

    @property
    def value(self) -> str:
        """Return the ticker value."""
        return self._value
