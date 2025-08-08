"""Tests for Dispatcher infrastructure - simplified version for current implementation."""

import logging
from dataclasses import dataclass
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.application.base.command import BaseCommand
from src.application.base.dispatcher import Dispatcher
from src.application.base.exceptions import HandlerNotFoundError
from src.application.base.handlers import CommandHandler, QueryHandler
from src.application.base.query import BaseQuery


# Test Commands and Queries
@dataclass(frozen=True)
class TestCommand(BaseCommand):
    """Test command for dispatcher testing."""

    data: str = ""
    value: int = 0

    def validate(self) -> None:
        if not self.data:
            raise ValueError("Data is required")


@dataclass(frozen=True)
class AnotherCommand(BaseCommand):
    """Another test command."""

    name: str = ""

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Name is required")


@dataclass(frozen=True)
class TestQuery(BaseQuery):
    """Test query for dispatcher testing."""

    search_term: str = ""


@dataclass(frozen=True)
class AnotherQuery(BaseQuery):
    """Another test query."""

    filter_value: str = ""


# Test Result Types
@dataclass
class TestResult:
    """Test result type."""

    id: str
    processed_data: str
    metadata: dict[str, any] = None


# Test Handler Implementations
class TestCommandHandler(CommandHandler[TestCommand, TestResult]):
    """Test command handler implementation."""

    def __init__(self, repository=None, service=None, logger=None):
        self.repository = repository
        self.service = service
        self.logger = logger or logging.getLogger(__name__)
        self.handled_commands = []

    async def handle(self, command: TestCommand) -> TestResult:
        """Handle the test command."""
        self.logger.info(f"Processing command with data: {command.data}")
        self.handled_commands.append(command)

        if command.data == "error":
            raise ValueError("Simulated processing error")

        return TestResult(
            id=str(uuid4()),
            processed_data=f"processed_{command.data}",
            metadata={"value": command.value},
        )

    @classmethod
    def command_type(cls) -> type[TestCommand]:
        return TestCommand


class AnotherCommandHandler(CommandHandler[AnotherCommand, str]):
    """Another command handler for testing multiple handlers."""

    def __init__(self, config=None):
        self.config = config
        self.processed_names = []

    async def handle(self, command: AnotherCommand) -> str:
        """Handle the another command."""
        self.processed_names.append(command.name)
        return f"processed_{command.name}"

    @classmethod
    def command_type(cls) -> type[AnotherCommand]:
        return AnotherCommand


class TestQueryHandler(QueryHandler[TestQuery, list[str]]):
    """Test query handler implementation."""

    def __init__(self, repository=None, cache=None):
        self.repository = repository
        self.cache = cache
        self.handled_queries = []

    async def handle(self, query: TestQuery) -> list[str]:
        """Handle the test query."""
        self.handled_queries.append(query)

        if query.search_term == "error":
            raise ValueError("Simulated query error")

        return [f"result_for_{query.search_term}"]

    @classmethod
    def query_type(cls) -> type[TestQuery]:
        return TestQuery


class AnotherQueryHandler(QueryHandler[AnotherQuery, dict[str, str]]):
    """Another query handler for testing multiple handlers."""

    def __init__(self, data_source=None):
        self.data_source = data_source

    async def handle(self, query: AnotherQuery) -> dict[str, str]:
        """Handle the another query."""
        return {"filter": query.filter_value, "result": "filtered_data"}

    @classmethod
    def query_type(cls) -> type[AnotherQuery]:
        return AnotherQuery


class TestDispatcher:
    """Test basic dispatcher functionality."""

    def test_dispatcher_initialization(self):
        """Test dispatcher initialization."""
        dispatcher = Dispatcher()

        assert dispatcher._command_handlers == {}
        assert dispatcher._query_handlers == {}
        assert dispatcher._handler_instances == {}

    def test_register_command_handler(self):
        """Test registering command handlers."""
        dispatcher = Dispatcher()

        # Register handler
        dispatcher.register_command_handler(TestCommandHandler)

        # Check registration
        assert TestCommand in dispatcher._command_handlers
        assert dispatcher._command_handlers[TestCommand] == TestCommandHandler

        # Register another handler
        dispatcher.register_command_handler(AnotherCommandHandler)
        assert AnotherCommand in dispatcher._command_handlers
        assert dispatcher._command_handlers[AnotherCommand] == AnotherCommandHandler

        # Should have both handlers
        assert len(dispatcher._command_handlers) == 2

    def test_register_query_handler(self):
        """Test registering query handlers."""
        dispatcher = Dispatcher()

        # Register handler
        dispatcher.register_query_handler(TestQueryHandler)

        # Check registration
        assert TestQuery in dispatcher._query_handlers
        assert dispatcher._query_handlers[TestQuery] == TestQueryHandler

        # Register another handler
        dispatcher.register_query_handler(AnotherQueryHandler)
        assert AnotherQuery in dispatcher._query_handlers
        assert dispatcher._query_handlers[AnotherQuery] == AnotherQueryHandler

        # Should have both handlers
        assert len(dispatcher._query_handlers) == 2

    def test_register_multiple_handlers_same_type(self):
        """Test that registering multiple handlers for same type overwrites."""
        dispatcher = Dispatcher()

        # Register first handler
        dispatcher.register_command_handler(TestCommandHandler)
        assert dispatcher._command_handlers[TestCommand] == TestCommandHandler

        # Register second handler for same command type (should overwrite)
        class SecondTestCommandHandler(CommandHandler[TestCommand, str]):
            async def handle(self, command: TestCommand) -> str:
                return "second_handler"

            @classmethod
            def command_type(cls) -> type[TestCommand]:
                return TestCommand

        dispatcher.register_command_handler(SecondTestCommandHandler)
        assert dispatcher._command_handlers[TestCommand] == SecondTestCommandHandler

    @pytest.mark.asyncio
    async def test_dispatch_command_success(self):
        """Test successful command dispatching."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)

        command = TestCommand(data="test_data", value=42)
        dependencies = {"repository": Mock(), "service": Mock()}

        result = await dispatcher.dispatch_command(command, dependencies)

        assert isinstance(result, TestResult)
        assert result.processed_data == "processed_test_data"
        assert result.metadata["value"] == 42

    @pytest.mark.asyncio
    async def test_dispatch_query_success(self):
        """Test successful query dispatching."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(TestQueryHandler)

        query = TestQuery(search_term="test")
        dependencies = {"repository": Mock(), "cache": Mock()}

        result = await dispatcher.dispatch_query(query, dependencies)

        assert isinstance(result, list)
        assert result == ["result_for_test"]

    @pytest.mark.asyncio
    async def test_dispatch_command_handler_not_found(self):
        """Test command dispatch when no handler is registered."""
        dispatcher = Dispatcher()

        command = TestCommand(data="test")
        dependencies = {}

        with pytest.raises(HandlerNotFoundError) as exc_info:
            await dispatcher.dispatch_command(command, dependencies)

        assert exc_info.value.request_type == "TestCommand"

    @pytest.mark.asyncio
    async def test_dispatch_query_handler_not_found(self):
        """Test query dispatch when no handler is registered."""
        dispatcher = Dispatcher()

        query = TestQuery(search_term="test")
        dependencies = {}

        with pytest.raises(HandlerNotFoundError) as exc_info:
            await dispatcher.dispatch_query(query, dependencies)

        assert exc_info.value.request_type == "TestQuery"

    @pytest.mark.asyncio
    async def test_dispatch_multiple_commands(self):
        """Test dispatching multiple different commands."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)
        dispatcher.register_command_handler(AnotherCommandHandler)

        # Dispatch first command
        command1 = TestCommand(data="first", value=1)
        dependencies1 = {"repository": Mock(), "service": Mock()}
        result1 = await dispatcher.dispatch_command(command1, dependencies1)

        # Dispatch second command
        command2 = AnotherCommand(name="second")
        dependencies2 = {"config": {"debug": True}}
        result2 = await dispatcher.dispatch_command(command2, dependencies2)

        assert isinstance(result1, TestResult)
        assert result1.processed_data == "processed_first"
        assert result2 == "processed_second"

    @pytest.mark.asyncio
    async def test_dispatch_multiple_queries(self):
        """Test dispatching multiple different queries."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(TestQueryHandler)
        dispatcher.register_query_handler(AnotherQueryHandler)

        # Dispatch first query
        query1 = TestQuery(search_term="first")
        dependencies1 = {"repository": Mock(), "cache": Mock()}
        result1 = await dispatcher.dispatch_query(query1, dependencies1)

        # Dispatch second query
        query2 = AnotherQuery(filter_value="second")
        dependencies2 = {"data_source": Mock()}
        result2 = await dispatcher.dispatch_query(query2, dependencies2)

        assert result1 == ["result_for_first"]
        assert result2 == {"filter": "second", "result": "filtered_data"}

    @pytest.mark.asyncio
    async def test_command_processing_error(self):
        """Test error handling during command processing."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)

        # Command that will cause handler to throw error
        command = TestCommand(data="error")
        dependencies = {"repository": Mock(), "service": Mock()}

        with pytest.raises(ValueError, match="Simulated processing error"):
            await dispatcher.dispatch_command(command, dependencies)

    @pytest.mark.asyncio
    async def test_query_processing_error(self):
        """Test error handling during query processing."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(TestQueryHandler)

        # Query that will cause handler to throw error
        query = TestQuery(search_term="error")
        dependencies = {"repository": Mock(), "cache": Mock()}

        with pytest.raises(ValueError, match="Simulated query error"):
            await dispatcher.dispatch_query(query, dependencies)


class TestExceptionHandling:
    """Test cases for exception handling."""

    @pytest.mark.asyncio
    async def test_command_validation_error(self):
        """Test handling of command validation errors."""
        # Command with empty data (should fail validation)
        with pytest.raises(ValueError, match="Data is required"):
            TestCommand(data="")  # Validation happens in __post_init__

    @pytest.mark.asyncio
    async def test_handler_business_logic_error(self):
        """Test propagation of handler business logic errors."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)

        command = TestCommand(data="error")  # Will trigger error in handler
        dependencies = {"repository": Mock(), "service": Mock()}

        with pytest.raises(ValueError, match="Simulated processing error"):
            await dispatcher.dispatch_command(command, dependencies)

    def test_handler_not_found_error_details(self):
        """Test HandlerNotFoundError contains correct details."""
        error = HandlerNotFoundError("TestCommand")

        assert error.request_type == "TestCommand"
        assert str(error) == "No handler registered for TestCommand"


class TestLoggingIntegration:
    """Test cases for logging integration."""

    @pytest.mark.asyncio
    async def test_command_dispatch_logging(self):
        """Test logging during command dispatch."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            dispatcher.register_command_handler(TestCommandHandler)

            command = TestCommand(data="test_data", value=42)
            dependencies = {"repository": Mock(), "service": Mock()}

            await dispatcher.dispatch_command(command, dependencies)

            # Check that info log was called for dispatch
            mock_logger.info.assert_any_call(
                "Dispatching command: TestCommand",
                extra={
                    "command_type": "TestCommand",
                    "user_id": command.user_id,
                },
            )

            # Check that success log was called
            mock_logger.info.assert_any_call(
                "Command processed successfully: TestCommand"
            )

    @pytest.mark.asyncio
    async def test_query_dispatch_logging(self):
        """Test logging during query dispatch."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            dispatcher.register_query_handler(TestQueryHandler)

            query = TestQuery(search_term="test")
            dependencies = {"repository": Mock(), "cache": Mock()}

            await dispatcher.dispatch_query(query, dependencies)

            # Check that debug log was called for dispatch
            mock_logger.debug.assert_any_call(
                "Dispatching query: TestQuery",
                extra={
                    "query_type": "TestQuery",
                    "user_id": query.user_id,
                    "page": query.page,
                    "page_size": query.page_size,
                },
            )

            # Check that success log was called
            mock_logger.debug.assert_any_call("Query processed successfully: TestQuery")

    @pytest.mark.asyncio
    async def test_command_error_logging(self):
        """Test error logging during command processing."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            dispatcher.register_command_handler(TestCommandHandler)

            command = TestCommand(data="error")  # Will cause error
            dependencies = {"repository": Mock(), "service": Mock()}

            with pytest.raises(ValueError):
                await dispatcher.dispatch_command(command, dependencies)

            # Check that error log was called
            mock_logger.error.assert_called_once_with(
                "Command processing failed: TestCommand",
                extra={"error": "Simulated processing error"},
                exc_info=True,
            )

    @pytest.mark.asyncio
    async def test_query_error_logging(self):
        """Test error logging during query processing."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            dispatcher.register_query_handler(TestQueryHandler)

            query = TestQuery(search_term="error")  # Will cause error
            dependencies = {"repository": Mock(), "cache": Mock()}

            with pytest.raises(ValueError):
                await dispatcher.dispatch_query(query, dependencies)

            # Check that error log was called
            mock_logger.error.assert_called_once_with(
                "Query processing failed: TestQuery",
                extra={"error": "Simulated query error"},
                exc_info=True,
            )
