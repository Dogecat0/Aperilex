"""SEC filing accession number value object."""

import re
from typing import Any


class AccessionNumber:
    """SEC filing accession number.

    Accession numbers are unique identifiers assigned to SEC filings.
    Format: NNNNNNNNNN-NN-NNNNNN (10 digits, 2 digits, 6 digits)
    Where the first 10 digits are the CIK of the filer.
    """

    def __init__(self, value: str) -> None:
        """Initialize accession number with validation.

        Args:
            value: Accession number string in format NNNNNNNNNN-NN-NNNNNN

        Raises:
            ValueError: If accession number format is invalid
        """
        self._value = str(value).strip()
        self.validate()

    def validate(self) -> None:
        """Validate accession number format.

        Raises:
            ValueError: If accession number format is invalid
        """
        if not self._value:
            raise ValueError("Accession number cannot be empty")

        pattern = r'^\d{10}-\d{2}-\d{6}$'
        if not re.match(pattern, self._value):
            raise ValueError("Accession number must be in format NNNNNNNNNN-NN-NNNNNN")

    def __str__(self) -> str:
        """Return accession number as string."""
        return self._value

    def __eq__(self, other: Any) -> bool:
        """Check equality with another accession number."""
        if not isinstance(other, AccessionNumber):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"AccessionNumber('{self._value}')"

    def get_cik(self) -> str:
        """Extract CIK from accession number.

        Returns:
            CIK as string (first 10 digits)
        """
        return self._value[:10]

    def get_year(self) -> int:
        """Extract year from accession number.

        Returns:
            Year as integer (digits 11-12 represent year suffix)
        """
        year_suffix = int(self._value[11:13])
        # Convert 2-digit year to 4-digit year
        # Assume years 00-30 are 2000-2030, 31-99 are 1931-1999
        if year_suffix <= 30:
            return 2000 + year_suffix
        else:
            return 1900 + year_suffix

    def get_sequence(self) -> int:
        """Extract sequence number from accession number.

        Returns:
            Sequence number as integer (last 6 digits)
        """
        return int(self._value[14:20])

    @property
    def value(self) -> str:
        """Return the accession number value."""
        return self._value
