"""Custom exceptions for the application layer.

These exceptions provide clear error semantics for command and query processing.
They follow the existing codebase pattern of descriptive error messages.
"""


class ApplicationError(Exception):
    """Base exception for all application layer errors."""

    pass


class HandlerNotFoundError(ApplicationError):
    """Raised when no handler is registered for a command or query."""

    def __init__(self, request_type: str) -> None:
        super().__init__(f"No handler registered for {request_type}")
        self.request_type = request_type


class ValidationError(ApplicationError):
    """Raised when command or query validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class BusinessRuleViolationError(ApplicationError):
    """Raised when a business rule is violated during command processing."""

    pass


class ResourceNotFoundError(ApplicationError):
    """Raised when a required resource is not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(f"{resource_type} with ID '{resource_id}' not found")
        self.resource_type = resource_type
        self.resource_id = resource_id


class DependencyError(ApplicationError):
    """Raised when required dependencies cannot be resolved."""

    def __init__(self, dependency_name: str) -> None:
        super().__init__(
            f"Required dependency '{dependency_name}' could not be resolved"
        )
        self.dependency_name = dependency_name
