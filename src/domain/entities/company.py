"""Company entity for reference and caching.

This minimal entity stores only essential identifiers. All detailed company
information should be retrieved directly from edgartools when needed.
"""

from typing import Any
from uuid import UUID

from src.domain.value_objects.cik import CIK


class Company:
    """Minimal company entity for reference purposes.

    This entity stores only the essential identifiers needed to reference
    a company in our analysis system. For detailed company information
    (ticker, SIC code, financials, etc.), use edgartools directly.

    Attributes:
        id: Unique identifier for the company in our system
        cik: Central Index Key assigned by SEC
        name: Company name for display purposes
    """

    def __init__(
        self,
        id: UUID,
        cik: CIK,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a Company entity.

        Args:
            id: Unique identifier for the company
            cik: Central Index Key
            name: Company name
            metadata: Additional metadata (optional)

        Raises:
            ValueError: If name is empty
        """
        self._id = id
        self._cik = cik
        self._name = name.strip() if name else name
        self._metadata = metadata or {}

        self._validate_invariants()

    @property
    def id(self) -> UUID:
        """Get company ID."""
        return self._id

    @property
    def cik(self) -> CIK:
        """Get company CIK."""
        return self._cik

    @property
    def name(self) -> str:
        """Get company name."""
        return self._name

    @property
    def metadata(self) -> dict[str, Any]:
        """Get company metadata."""
        return self._metadata.copy()

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata entry.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def _validate_invariants(self) -> None:
        """Validate domain invariants."""
        if not self._name or not self._name.strip():
            raise ValueError("Company name cannot be empty")

    def __eq__(self, other: object) -> bool:
        """Check equality based on CIK."""
        if not isinstance(other, Company):
            return False
        return self._cik == other._cik

    def __hash__(self) -> int:
        """Hash based on CIK."""
        return hash(self._cik)

    def __str__(self) -> str:
        """String representation."""
        return f"Company: {self._name} [CIK: {self._cik}]"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Company(id={self._id}, cik={self._cik}, name='{self._name}')"
