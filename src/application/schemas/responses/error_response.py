"""Error Response DTO for standardized error information."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class ErrorType(str, Enum):
    """Types of errors that can occur in the application."""

    VALIDATION_ERROR = "validation_error"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    PROCESSING_ERROR = "processing_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ErrorResponse:
    """Response DTO for error information.

    This DTO provides standardized error information across the application,
    including error classification, details, and context for debugging.

    Attributes:
        error_id: Unique identifier for this error instance
        error_type: Classification of the error type
        message: Human-readable error message
        details: Additional error details or context
        field_errors: Field-specific validation errors (if applicable)
        timestamp: When the error occurred
        request_id: ID of the request that caused the error (if available)
        resource_id: ID of the resource involved (if applicable)
        retry_after_seconds: Suggested retry delay for retryable errors
        help_url: URL to documentation about this error (if available)
    """

    error_id: UUID
    error_type: str  # ErrorType value as string
    message: str
    details: str | None = None
    field_errors: dict[str, list[str]] | None = None
    timestamp: datetime = datetime.utcnow()
    request_id: str | None = None
    resource_id: str | None = None
    retry_after_seconds: int | None = None
    help_url: str | None = None

    @classmethod
    def validation_error(
        cls,
        message: str,
        field_errors: dict[str, list[str]] | None = None,
        details: str | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for validation failures.

        Args:
            message: Main error message
            field_errors: Field-specific validation errors
            details: Additional error details
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for validation error
        """
        return cls(
            error_id=uuid4(),
            error_type=ErrorType.VALIDATION_ERROR.value,
            message=message,
            field_errors=field_errors,
            details=details,
            request_id=request_id,
        )

    @classmethod
    def business_rule_violation(
        cls,
        message: str,
        details: str | None = None,
        resource_id: str | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for business rule violations.

        Args:
            message: Main error message
            details: Additional error details
            resource_id: ID of the resource involved
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for business rule violation
        """
        return cls(
            error_id=uuid4(),
            error_type=ErrorType.BUSINESS_RULE_VIOLATION.value,
            message=message,
            details=details,
            resource_id=resource_id,
            request_id=request_id,
        )

    @classmethod
    def resource_not_found(
        cls,
        resource_type: str,
        resource_id: str,
        message: str | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for resource not found errors.

        Args:
            resource_type: Type of resource (e.g., "Filing", "Analysis")
            resource_id: ID of the missing resource
            message: Custom error message (optional)
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for resource not found
        """
        default_message = f"{resource_type} with ID '{resource_id}' not found"

        return cls(
            error_id=uuid4(),
            error_type=ErrorType.RESOURCE_NOT_FOUND.value,
            message=message or default_message,
            resource_id=resource_id,
            request_id=request_id,
        )

    @classmethod
    def external_service_error(
        cls,
        service_name: str,
        message: str,
        details: str | None = None,
        retry_after_seconds: int | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for external service failures.

        Args:
            service_name: Name of the external service
            message: Error message
            details: Additional error details
            retry_after_seconds: Suggested retry delay
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for external service error
        """
        return cls(
            error_id=uuid4(),
            error_type=ErrorType.EXTERNAL_SERVICE_ERROR.value,
            message=f"{service_name}: {message}",
            details=details,
            retry_after_seconds=retry_after_seconds,
            request_id=request_id,
        )

    @classmethod
    def processing_error(
        cls,
        message: str,
        details: str | None = None,
        resource_id: str | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for processing failures.

        Args:
            message: Error message
            details: Additional error details
            resource_id: ID of the resource being processed
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for processing error
        """
        return cls(
            error_id=uuid4(),
            error_type=ErrorType.PROCESSING_ERROR.value,
            message=message,
            details=details,
            resource_id=resource_id,
            request_id=request_id,
        )

    @classmethod
    def internal_error(
        cls,
        message: str = "An internal error occurred",
        details: str | None = None,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response for internal/unexpected errors.

        Args:
            message: Error message (should be user-friendly)
            details: Additional error details (for debugging)
            request_id: Request ID that caused the error

        Returns:
            ErrorResponse for internal error
        """
        return cls(
            error_id=uuid4(),
            error_type=ErrorType.INTERNAL_ERROR.value,
            message=message,
            details=details,
            request_id=request_id,
        )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        request_id: str | None = None,
        resource_id: str | None = None,
    ) -> "ErrorResponse":
        """Create an error response from a Python exception.

        Args:
            exception: Python exception to convert
            error_type: Type of error to classify this as
            request_id: Request ID that caused the error
            resource_id: Resource ID involved in the error

        Returns:
            ErrorResponse based on the exception
        """
        return cls(
            error_id=uuid4(),
            error_type=error_type.value,
            message=str(exception),
            details=f"{exception.__class__.__name__}: {str(exception)}",
            request_id=request_id,
            resource_id=resource_id,
        )

    @property
    def is_retryable(self) -> bool:
        """Check if this error indicates a retryable operation.

        Returns:
            True if the operation can be retried
        """
        retryable_types = {
            ErrorType.EXTERNAL_SERVICE_ERROR.value,
            ErrorType.PROCESSING_ERROR.value,
            ErrorType.INTERNAL_ERROR.value,
        }
        return self.error_type in retryable_types

    @property
    def is_client_error(self) -> bool:
        """Check if this is a client-side error (4xx category).

        Returns:
            True if error is due to client request issues
        """
        client_error_types = {
            ErrorType.VALIDATION_ERROR.value,
            ErrorType.BUSINESS_RULE_VIOLATION.value,
            ErrorType.RESOURCE_NOT_FOUND.value,
            ErrorType.PERMISSION_DENIED.value,
        }
        return self.error_type in client_error_types

    @property
    def is_server_error(self) -> bool:
        """Check if this is a server-side error (5xx category).

        Returns:
            True if error is due to server-side issues
        """
        return not self.is_client_error

    def get_http_status_code(self) -> int:
        """Get appropriate HTTP status code for this error.

        Returns:
            HTTP status code
        """
        status_codes = {
            ErrorType.VALIDATION_ERROR.value: 400,
            ErrorType.BUSINESS_RULE_VIOLATION.value: 422,
            ErrorType.RESOURCE_NOT_FOUND.value: 404,
            ErrorType.PERMISSION_DENIED.value: 403,
            ErrorType.EXTERNAL_SERVICE_ERROR.value: 502,
            ErrorType.PROCESSING_ERROR.value: 500,
            ErrorType.INTERNAL_ERROR.value: 500,
        }
        return status_codes.get(self.error_type, 500)

    def get_field_error_count(self) -> int:
        """Get the total number of field errors.

        Returns:
            Total count of field-specific errors
        """
        if not self.field_errors:
            return 0
        return sum(len(errors) for errors in self.field_errors.values())

    def has_field_errors(self) -> bool:
        """Check if this error has field-specific validation errors.

        Returns:
            True if field_errors is not empty
        """
        return self.field_errors is not None and len(self.field_errors) > 0
