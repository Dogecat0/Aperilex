"""Custom exceptions for the application layer.

These exceptions provide clear error semantics for command and query processing.
"""


class ApplicationError(Exception):
    """Base exception for all application layer errors."""

    pass


class HandlerNotFoundError(ApplicationError):
    """Raised when no handler is registered for a command or query."""

    def __init__(self, request_type: str) -> None:
        super().__init__(f"No handler registered for {request_type}")
        self.request_type = request_type


class DependencyError(ApplicationError):
    """Raised when dependency injection fails."""

    def __init__(self, dependency_name: str, message: str | None = None) -> None:
        if message is None:
            message = f"Failed to resolve dependency: {dependency_name}"
        super().__init__(message)
        self.dependency_name = dependency_name


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(f"{resource_type} with identifier '{identifier}' not found")
        self.resource_type = resource_type
        self.identifier = identifier
