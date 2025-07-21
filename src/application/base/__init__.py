"""Base CQRS infrastructure for the application layer.

This module provides the foundation for implementing Command Query Responsibility
Segregation (CQRS) pattern in the application layer.
"""

from .command import BaseCommand
from .dispatcher import Dispatcher
from .exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    DependencyError,
    HandlerNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from .handlers import CommandHandler, QueryHandler
from .query import BaseQuery

__all__ = [
    # Base classes
    "BaseCommand",
    "BaseQuery",
    "CommandHandler",
    "QueryHandler",
    # Dispatcher
    "Dispatcher",
    # Exceptions
    "ApplicationError",
    "BusinessRuleViolationError",
    "DependencyError",
    "HandlerNotFoundError",
    "ResourceNotFoundError",
    "ValidationError",
]
