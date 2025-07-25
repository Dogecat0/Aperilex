"""Command and query dispatcher for CQRS pattern.

The dispatcher routes commands and queries to their appropriate handlers
with basic logging support.
"""

import inspect
import logging
from typing import Any

from .command import BaseCommand
from .exceptions import HandlerNotFoundError
from .handlers import CommandHandler, QueryHandler
from .query import BaseQuery

logger = logging.getLogger(__name__)


class Dispatcher:
    """Central dispatcher for routing commands and queries to handlers.

    The dispatcher maintains a registry of handlers and routes incoming
    commands and queries to the appropriate handler. It also manages
    dependency injection for handler construction.

    Example:
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(AnalyzeFilingCommandHandler)

        result = await dispatcher.dispatch_command(
            AnalyzeFilingCommand(filing_id="123"),
            dependencies
        )
    """

    def __init__(self) -> None:
        """Initialize the dispatcher with empty handler registries."""
        self._command_handlers: dict[
            type[BaseCommand], type[CommandHandler[Any, Any]]
        ] = {}
        self._query_handlers: dict[type[BaseQuery], type[QueryHandler[Any, Any]]] = {}
        self._handler_instances: dict[str, Any] = {}

    def _filter_dependencies(
        self, handler_class: type, dependencies: dict[str, Any]
    ) -> dict[str, Any]:
        """Filter dependencies to only include those required by the handler constructor.

        Args:
            handler_class: The handler class to instantiate
            dependencies: Available dependencies

        Returns:
            Dictionary containing only the dependencies required by the handler
        """
        try:
            # Get the constructor signature
            init_signature = inspect.signature(handler_class)

            # Extract parameter names (excluding 'self')
            required_params = [
                param_name
                for param_name in init_signature.parameters.keys()
                if param_name != 'self'
            ]

            # Filter dependencies to only include required ones
            filtered_deps = {
                param: dependencies[param]
                for param in required_params
                if param in dependencies
            }

            logger.debug(
                f"Filtered dependencies for {handler_class.__name__}: {list(filtered_deps.keys())}"
            )

            return filtered_deps

        except Exception as e:
            logger.warning(
                f"Failed to filter dependencies for {handler_class.__name__}: {e}. Using all dependencies."
            )
            return dependencies

    def register_command_handler(
        self, handler_class: type[CommandHandler[Any, Any]]
    ) -> None:
        """Register a command handler.

        Args:
            handler_class: The handler class to register
        """
        command_type = handler_class.command_type()
        self._command_handlers[command_type] = handler_class
        logger.debug(
            f"Registered command handler: {handler_class.__name__} for {command_type.__name__}"
        )

    def register_query_handler(
        self, handler_class: type[QueryHandler[Any, Any]]
    ) -> None:
        """Register a query handler.

        Args:
            handler_class: The handler class to register
        """
        query_type = handler_class.query_type()
        self._query_handlers[query_type] = handler_class
        logger.debug(
            f"Registered query handler: {handler_class.__name__} for {query_type.__name__}"
        )

    async def dispatch_command(
        self, command: BaseCommand, dependencies: dict[str, Any]
    ) -> Any:
        """Dispatch a command to its handler.

        Args:
            command: The command to dispatch
            dependencies: Dictionary of dependencies available for injection

        Returns:
            The result of command processing

        Raises:
            HandlerNotFoundError: If no handler is registered for the command
        """
        handler_class = self._command_handlers.get(type(command))
        if not handler_class:
            raise HandlerNotFoundError(type(command).__name__)

        filtered_deps = self._filter_dependencies(handler_class, dependencies)
        handler = handler_class(**filtered_deps)

        logger.info(
            f"Dispatching command: {type(command).__name__}",
            extra={
                "command_type": type(command).__name__,
                "user_id": command.user_id,
            },
        )

        try:
            result = await handler.handle(command)
            logger.info(f"Command processed successfully: {type(command).__name__}")
            return result
        except Exception as e:
            logger.error(
                f"Command processing failed: {type(command).__name__}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def dispatch_query(
        self, query: BaseQuery, dependencies: dict[str, Any]
    ) -> Any:
        """Dispatch a query to its handler.

        Args:
            query: The query to dispatch
            dependencies: Dictionary of dependencies available for injection

        Returns:
            The result of query processing

        Raises:
            HandlerNotFoundError: If no handler is registered for the query
        """
        handler_class = self._query_handlers.get(type(query))
        if not handler_class:
            raise HandlerNotFoundError(type(query).__name__)

        filtered_deps = self._filter_dependencies(handler_class, dependencies)
        handler = handler_class(**filtered_deps)

        logger.debug(
            f"Dispatching query: {type(query).__name__}",
            extra={
                "query_type": type(query).__name__,
                "user_id": query.user_id,
                "page": query.page,
                "page_size": query.page_size,
            },
        )

        try:
            result = await handler.handle(query)
            logger.debug(f"Query processed successfully: {type(query).__name__}")
            return result
        except Exception as e:
            logger.error(
                f"Query processing failed: {type(query).__name__}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise
