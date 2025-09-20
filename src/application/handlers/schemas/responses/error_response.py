"""Error Response DTO for standardized error information."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel


class ErrorType(str, Enum):
    """Basic error types."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PROCESSING_ERROR = "processing_error"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(SchemaVersionedModel):
    """Simple response DTO for error information.

    Attributes:
        error_type: Classification of the error type
        message: Human-readable error message
        details: Additional error details (optional)
        timestamp: When the error occurred
    """

    error_type: ErrorType = Field(description="Classification of the error type")
    message: str = Field(description="Human-readable error message")
    details: str | None = Field(
        default=None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the error occurred",
    )

    @property
    def is_validation_error(self) -> bool:
        """Check if this is a validation error.

        Returns:
            True if error is validation-related
        """
        return self.error_type is ErrorType.VALIDATION_ERROR

    @property
    def is_not_found_error(self) -> bool:
        """Check if this is a not found error.

        Returns:
            True if error is resource not found
        """
        return self.error_type is ErrorType.NOT_FOUND

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
            error_type=ErrorType.VALIDATION_ERROR,
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
            error_type=ErrorType.NOT_FOUND,
            message=f"{resource_type} not found",
            details=f"No {resource_type.lower()} found with ID: {resource_id}",
        )
