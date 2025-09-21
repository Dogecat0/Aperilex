"""Application service for coordinating command and query processing with DI container integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from dependency_injector.wiring import Provide, inject

from src.application.base.command import BaseCommand
from src.application.base.dispatcher import Dispatcher
from src.application.base.query import BaseQuery

if TYPE_CHECKING:
    from src.application.containers.cqrs import HandlerFactory

logger = logging.getLogger(__name__)


class ApplicationService:
    """Central application service for coordinating CQRS operations with DI container.

    This service acts as the main entry point for the application layer,
    using the DI container to provide dependencies to handlers. It leverages
    the HandlerFactory from CQRSContainer for proper dependency injection
    while exposing a clean interface for command and query processing.
    """

    @inject
    def __init__(
        self,
        dispatcher: Dispatcher = Provide["cqrs.dispatcher"],
        handler_factory: HandlerFactory = Provide["cqrs.handler_factory"],
    ) -> None:
        """Initialize the application service with DI container dependencies.

        Args:
            dispatcher: CQRS dispatcher with registered handlers
            handler_factory: Factory for providing handler dependencies
        """
        self.dispatcher: Dispatcher = dispatcher
        self.handler_factory: HandlerFactory = handler_factory

    async def execute_command(self, command: BaseCommand) -> object:
        """Execute a command using the dispatcher with DI-managed dependencies.

        Args:
            command: The command to execute

        Returns:
            The result of command execution
        """
        dependencies = cast(
            dict[str, object], await self.handler_factory.get_dependencies()
        )
        return await self.dispatcher.dispatch_command(command, dependencies)

    async def execute_query(self, query: BaseQuery) -> object:
        """Execute a query using the dispatcher with DI-managed dependencies.

        Args:
            query: The query to execute

        Returns:
            The result of query execution
        """
        dependencies = cast(
            dict[str, object], await self.handler_factory.get_dependencies()
        )
        return await self.dispatcher.dispatch_query(query, dependencies)
