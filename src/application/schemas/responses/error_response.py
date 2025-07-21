"""Error Response DTO for standardized error information."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ErrorType(str, Enum):
    """Basic error types."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PROCESSING_ERROR = "processing_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ErrorResponse:
    """Simple response DTO for error information.

    Attributes:
        error_type: Classification of the error type
        message: Human-readable error message
        details: Additional error details (optional)
        timestamp: When the error occurred
    """

    error_type: str
    message: str
    details: str | None = None
    timestamp: datetime = datetime.utcnow()

    @property
    def is_validation_error(self) -> bool:
        """Check if this is a validation error.
        
        Returns:
            True if error is validation-related
        """
        return self.error_type == ErrorType.VALIDATION_ERROR.value

    @property
    def is_not_found_error(self) -> bool:
        """Check if this is a not found error.
        
        Returns:
            True if error is resource not found
        """
        return self.error_type == ErrorType.NOT_FOUND.value