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


