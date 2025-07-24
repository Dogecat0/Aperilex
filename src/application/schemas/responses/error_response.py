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

    @classmethod
    def validation_error(
        cls, message: str, details: str | None = None
    ) -> "ErrorResponse":
        """Create a validation error response.

        Args:
            message: Error message
            details: Additional error details

        Returns:
            ErrorResponse with validation error type
        """
        return cls(
            error_type=ErrorType.VALIDATION_ERROR.value,
            message=message,
            details=details,
        )

    @classmethod
    def resource_not_found(
        cls, resource_type: str, resource_id: str
    ) -> "ErrorResponse":
        """Create a resource not found error response.

        Args:
            resource_type: Type of resource that was not found
            resource_id: ID of the resource that was not found

        Returns:
            ErrorResponse with not found error type
        """
        return cls(
            error_type=ErrorType.NOT_FOUND.value,
            message=f"{resource_type} not found",
            details=f"No {resource_type.lower()} found with ID: {resource_id}",
        )
