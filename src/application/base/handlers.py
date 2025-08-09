"""Handler interfaces for CQRS pattern.

Handlers contain the business logic for processing commands and queries.
They follow the single responsibility principle - one handler per command/query.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .command import BaseCommand
from .query import BaseQuery

TCommand = TypeVar("TCommand", bound=BaseCommand)
TQuery = TypeVar("TQuery", bound=BaseQuery)
TResult = TypeVar("TResult")


class CommandHandler(Generic[TCommand, TResult], ABC):
    """Base class for command handlers.

    Command handlers contain the business logic for processing commands.
    They are responsible for:
    - Validating business rules
    - Coordinating with domain services and repositories
    - Managing transactions
    - Returning simple results (IDs, status, etc.)

    Type Parameters:
        TCommand: The command type this handler processes
        TResult: The type of result returned by this handler
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle the command and return result.

        Args:
            command: The command to process

        Returns:
            The result of processing the command

        Raises:
            ValueError: If the command is invalid or cannot be processed
        """
        pass

    @classmethod
    @abstractmethod
    def command_type(cls) -> type[TCommand]:
        """Return the command type this handler processes.

        This is used by the dispatcher to route commands to handlers.
        """
        pass


class QueryHandler(Generic[TQuery, TResult], ABC):
    """Base class for query handlers.

    Query handlers contain the logic for processing queries.
    They are responsible for:
    - Retrieving data from repositories or read models
    - Applying filters and pagination
    - Formatting results for presentation
    - Caching frequently accessed data

    Type Parameters:
        TQuery: The query type this handler processes
        TResult: The type of result returned by this handler
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle the query and return result.

        Args:
            query: The query to process

        Returns:
            The result of processing the query
        """
        pass

    @classmethod
    @abstractmethod
    def query_type(cls) -> type[TQuery]:
        """Return the query type this handler processes.

        This is used by the dispatcher to route queries to handlers.
        """
        pass
