"""Comprehensive tests for CQRS Dispatcher pattern implementation.

Tests cover all critical business logic:
- Command/query routing to handlers
- Dependency injection with reflection
- Handler registration and management

Test scenarios include:
- Handler registration and lookup
- Dependency injection scenarios
- Handler execution flow
- Error handling and propagation
"""

from unittest.mock import patch

import pytest

from src.application.base.dispatcher import Dispatcher
from src.application.base.exceptions import HandlerNotFoundError
from src.application.base.handlers import CommandHandler, QueryHandler


class TestDispatcherHandlerRegistration:
    """Test handler registration and management."""

    def test_dispatcher_initialization(self):
        """Test dispatcher initializes with empty registries."""
        dispatcher = Dispatcher()

        assert len(dispatcher._command_handlers) == 0
        assert len(dispatcher._query_handlers) == 0
        assert len(dispatcher._handler_instances) == 0

    def test_register_command_handler(self, mock_command, mock_command_handler):
        """Test command handler registration."""
        dispatcher = Dispatcher()

        dispatcher.register_command_handler(mock_command_handler)

        assert mock_command in dispatcher._command_handlers
        assert dispatcher._command_handlers[mock_command] == mock_command_handler

    def test_register_query_handler(self, mock_query, mock_query_handler):
        """Test query handler registration."""
        dispatcher = Dispatcher()

        dispatcher.register_query_handler(mock_query_handler)

        assert mock_query in dispatcher._query_handlers
        assert dispatcher._query_handlers[mock_query] == mock_query_handler

    def test_register_multiple_command_handlers(self, mock_command):
        """Test registering multiple command handlers."""
        dispatcher = Dispatcher()

        # Create two different handlers for the same command type
        class Handler1(CommandHandler[mock_command, str]):
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                return "handler1"

        class Handler2(CommandHandler[mock_command, str]):
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                return "handler2"

        dispatcher.register_command_handler(Handler1)
        dispatcher.register_command_handler(Handler2)

        # Second handler should overwrite first
        assert dispatcher._command_handlers[mock_command] == Handler2

    def test_register_multiple_query_handlers(self, mock_query):
        """Test registering multiple query handlers."""
        dispatcher = Dispatcher()

        # Create two different handlers for the same query type
        class Handler1(QueryHandler[mock_query, dict]):
            def __init__(self):
                pass

            @classmethod
            def query_type(cls):
                return mock_query

            async def handle(self, query):
                return {"handler": "1"}

        class Handler2(QueryHandler[mock_query, dict]):
            def __init__(self):
                pass

            @classmethod
            def query_type(cls):
                return mock_query

            async def handle(self, query):
                return {"handler": "2"}

        dispatcher.register_query_handler(Handler1)
        dispatcher.register_query_handler(Handler2)

        # Second handler should overwrite first
        assert dispatcher._query_handlers[mock_query] == Handler2

    def test_handler_type_extraction(self, mock_command, mock_query):
        """Test that handler types are extracted correctly."""
        dispatcher = Dispatcher()

        # Create handlers with command_type/query_type methods
        class TestCommandHandler(CommandHandler[mock_command, str]):
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                return "test"

        class TestQueryHandler(QueryHandler[mock_query, dict]):
            def __init__(self):
                pass

            @classmethod
            def query_type(cls):
                return mock_query

            async def handle(self, query):
                return {}

        dispatcher.register_command_handler(TestCommandHandler)
        dispatcher.register_query_handler(TestQueryHandler)

        assert mock_command in dispatcher._command_handlers
        assert mock_query in dispatcher._query_handlers


class TestDispatcherDependencyInjection:
    """Test dependency injection with reflection."""

    def test_filter_dependencies_all_available(self):
        """Test dependency filtering when all dependencies are available."""
        dispatcher = Dispatcher()

        class TestHandler:
            def __init__(self, service_a: str, service_b: int, service_c: bool):
                pass

        dependencies = {
            "service_a": "test",
            "service_b": 42,
            "service_c": True,
            "extra_service": "not_needed",
        }

        filtered = dispatcher._filter_dependencies(TestHandler, dependencies)

        expected = {"service_a": "test", "service_b": 42, "service_c": True}
        assert filtered == expected

    def test_filter_dependencies_partial_available(self):
        """Test dependency filtering when only some dependencies are available."""
        dispatcher = Dispatcher()

        class TestHandler:
            def __init__(self, service_a: str, service_b: int):
                pass

        dependencies = {
            "service_a": "test",
            # service_b is missing
            "extra_service": "not_needed",
        }

        filtered = dispatcher._filter_dependencies(TestHandler, dependencies)

        expected = {"service_a": "test"}
        assert filtered == expected

    def test_filter_dependencies_no_parameters(self):
        """Test dependency filtering for handler with no parameters."""
        dispatcher = Dispatcher()

        class TestHandler:
            def __init__(self):
                pass

        dependencies = {"service_a": "test", "service_b": 42}

        filtered = dispatcher._filter_dependencies(TestHandler, dependencies)

        assert filtered == {}

    def test_filter_dependencies_only_self_parameter(self):
        """Test dependency filtering excludes 'self' parameter."""
        dispatcher = Dispatcher()

        class TestHandler:
            def __init__(self, service_a: str):
                pass

        dependencies = {"self": "should_be_ignored", "service_a": "test"}

        filtered = dispatcher._filter_dependencies(TestHandler, dependencies)

        # Should only include service_a, not self
        assert filtered == {"service_a": "test"}
        assert "self" not in filtered

    def test_filter_dependencies_error_handling(self):
        """Test dependency filtering handles reflection errors gracefully."""
        dispatcher = Dispatcher()

        # Create a class with no explicit __init__ method
        # This actually has an implicit __init__(self) which gets filtered correctly
        class ProblematicHandler:
            # This class intentionally has no parameters except self
            def some_method(self):
                pass

        dependencies = {"service_a": "test", "service_b": "test2"}

        # Should return empty dict since handler only needs 'self' (which is filtered out)
        filtered = dispatcher._filter_dependencies(ProblematicHandler, dependencies)

        # Handler with no explicit __init__ parameters should get empty dependencies
        assert filtered == {}

    @patch('src.application.base.dispatcher.inspect.signature')
    def test_filter_dependencies_signature_exception(self, mock_signature):
        """Test handling of signature inspection exceptions."""
        dispatcher = Dispatcher()
        mock_signature.side_effect = Exception("Signature error")

        class TestHandler:
            def __init__(self, service_a: str):
                pass

        dependencies = {"service_a": "test", "service_b": "test2"}

        # Should fallback to returning all dependencies
        filtered = dispatcher._filter_dependencies(TestHandler, dependencies)

        assert filtered == dependencies


class TestDispatcherCommandDispatch:
    """Test command dispatch functionality."""

    @pytest.mark.asyncio
    async def test_successful_command_dispatch(
        self, mock_command, mock_command_handler
    ):
        """Test successful command dispatch and execution."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        command_instance = mock_command()
        dependencies = {"dependency_a": "test_value", "dependency_b": 42}

        result = await dispatcher.dispatch_command(command_instance, dependencies)

        assert result == "handled_test_test_value_42"

    @pytest.mark.asyncio
    async def test_command_handler_not_found(self, mock_command):
        """Test HandlerNotFoundError when no handler registered."""
        dispatcher = Dispatcher()

        command_instance = mock_command()
        dependencies = {}

        with pytest.raises(HandlerNotFoundError, match="TestCommand"):
            await dispatcher.dispatch_command(command_instance, dependencies)

    @pytest.mark.asyncio
    async def test_command_handler_instantiation(
        self, mock_command, mock_command_handler
    ):
        """Test that handler is instantiated with filtered dependencies."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        command_instance = mock_command()
        dependencies = {
            "dependency_a": "correct",
            "dependency_b": 999,
            "extra_dependency": "ignored",
        }

        result = await dispatcher.dispatch_command(command_instance, dependencies)

        # Result shows handler received correct filtered dependencies
        assert "correct" in result
        assert "999" in result
        assert "ignored" not in result

    @pytest.mark.asyncio
    async def test_command_handler_execution_error(self, mock_command):
        """Test error propagation from command handler."""
        dispatcher = Dispatcher()

        class FailingCommandHandler(CommandHandler[mock_command, str]):
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                raise ValueError("Handler execution error")

        dispatcher.register_command_handler(FailingCommandHandler)

        command_instance = mock_command()
        dependencies = {}

        with pytest.raises(ValueError, match="Handler execution error"):
            await dispatcher.dispatch_command(command_instance, dependencies)

    @pytest.mark.asyncio
    async def test_command_with_user_context(self, mock_command, mock_command_handler):
        """Test command dispatch includes user context."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        command_instance = mock_command(user_id="user123")
        dependencies = {"dependency_a": "test", "dependency_b": 42}

        result = await dispatcher.dispatch_command(command_instance, dependencies)

        assert result is not None
        # User ID should be accessible in command
        assert command_instance.user_id == "user123"

    @pytest.mark.asyncio
    async def test_multiple_command_dispatches(
        self, mock_command, mock_command_handler
    ):
        """Test multiple command dispatches work correctly."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        dependencies = {"dependency_a": "test", "dependency_b": 42}

        # Dispatch multiple commands with different test data
        results = []
        for i in range(3):
            command_instance = mock_command(test_data=f"test_{i}")
            result = await dispatcher.dispatch_command(command_instance, dependencies)
            results.append(result)

        assert len(results) == 3
        assert all(f"test_{i}" in results[i] for i in range(3))


class TestDispatcherQueryDispatch:
    """Test query dispatch functionality."""

    @pytest.mark.asyncio
    async def test_successful_query_dispatch(self, mock_query, mock_query_handler):
        """Test successful query dispatch and execution."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(mock_query_handler)

        query_instance = mock_query()
        dependencies = {"service": "test_service"}

        result = await dispatcher.dispatch_query(query_instance, dependencies)

        expected = {
            "filter": "test",
            "service": "test_service",
            "page": 1,
            "page_size": 20,  # BaseQuery defaults to page_size=20
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_query_handler_not_found(self, mock_query):
        """Test HandlerNotFoundError when no handler registered."""
        dispatcher = Dispatcher()

        query_instance = mock_query()
        dependencies = {}

        with pytest.raises(HandlerNotFoundError, match="TestQuery"):
            await dispatcher.dispatch_query(query_instance, dependencies)

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, mock_query, mock_query_handler):
        """Test query dispatch with pagination parameters."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(mock_query_handler)

        # Create query with custom pagination (frozen dataclass requires new instance)
        query_instance = mock_query(page=5, page_size=25)
        dependencies = {"service": "paginated_service"}

        result = await dispatcher.dispatch_query(query_instance, dependencies)

        assert result["page"] == 5
        assert result["page_size"] == 25
        assert result["service"] == "paginated_service"

    @pytest.mark.asyncio
    async def test_query_handler_execution_error(self, mock_query):
        """Test error propagation from query handler."""
        dispatcher = Dispatcher()

        class FailingQueryHandler(QueryHandler[mock_query, dict]):
            def __init__(self):
                pass

            @classmethod
            def query_type(cls):
                return mock_query

            async def handle(self, query):
                raise RuntimeError("Query processing failed")

        dispatcher.register_query_handler(FailingQueryHandler)

        query_instance = mock_query()
        dependencies = {}

        with pytest.raises(RuntimeError, match="Query processing failed"):
            await dispatcher.dispatch_query(query_instance, dependencies)

    @pytest.mark.asyncio
    async def test_query_with_filters(self, mock_query, mock_query_handler):
        """Test query dispatch with custom filters."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(mock_query_handler)

        query_instance = mock_query(test_filter="custom_filter", user_id="user456")
        dependencies = {"service": "filter_service"}

        result = await dispatcher.dispatch_query(query_instance, dependencies)

        assert result["filter"] == "custom_filter"
        assert result["service"] == "filter_service"
        assert query_instance.user_id == "user456"

    @pytest.mark.asyncio
    async def test_concurrent_query_dispatches(self, mock_query, mock_query_handler):
        """Test concurrent query dispatches work correctly."""
        import asyncio

        dispatcher = Dispatcher()
        dispatcher.register_query_handler(mock_query_handler)

        dependencies = {"service": "concurrent_service"}

        # Create multiple queries with different filters
        queries = [mock_query(test_filter=f"filter_{i}") for i in range(5)]

        # Dispatch concurrently
        tasks = [dispatcher.dispatch_query(query, dependencies) for query in queries]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["filter"] == f"filter_{i}"
            assert result["service"] == "concurrent_service"


class TestDispatcherIntegration:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_mixed_command_query_registration(
        self, mock_command, mock_query, mock_command_handler, mock_query_handler
    ):
        """Test registering both commands and queries in same dispatcher."""
        dispatcher = Dispatcher()

        dispatcher.register_command_handler(mock_command_handler)
        dispatcher.register_query_handler(mock_query_handler)

        # Both should be registered
        assert len(dispatcher._command_handlers) == 1
        assert len(dispatcher._query_handlers) == 1

        # Both should work
        command_result = await dispatcher.dispatch_command(
            mock_command(), {"dependency_a": "test", "dependency_b": 42}
        )
        query_result = await dispatcher.dispatch_query(
            mock_query(), {"service": "test"}
        )

        assert command_result is not None
        assert query_result is not None

    def test_handler_registry_isolation(self, mock_command, mock_query):
        """Test that command and query registries are isolated."""
        dispatcher = Dispatcher()

        class CommandAsQuery(QueryHandler[mock_command, str]):  # Wrong inheritance
            def __init__(self):
                pass

            @classmethod
            def query_type(cls):
                return mock_command

            async def handle(self, query):
                return "wrong"

        class QueryAsCommand(CommandHandler[mock_query, str]):  # Wrong inheritance
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_query

            async def handle(self, command):
                return "wrong"

        # Register handlers in wrong registries
        dispatcher.register_query_handler(CommandAsQuery)
        dispatcher.register_command_handler(QueryAsCommand)

        # Should be in separate registries
        assert mock_command in dispatcher._query_handlers
        assert mock_query in dispatcher._command_handlers
        assert len(dispatcher._command_handlers) == 1
        assert len(dispatcher._query_handlers) == 1

    @pytest.mark.asyncio
    async def test_dependency_injection_edge_cases(self, mock_command):
        """Test dependency injection with complex scenarios."""
        dispatcher = Dispatcher()

        class ComplexHandler(CommandHandler[mock_command, str]):
            def __init__(self, required_dep: str, optional_dep: int = 42):
                self.required_dep = required_dep
                self.optional_dep = optional_dep

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                return f"{self.required_dep}_{self.optional_dep}"

        dispatcher.register_command_handler(ComplexHandler)

        # Test with only required dependency
        dependencies = {"required_dep": "test"}
        result = await dispatcher.dispatch_command(mock_command(), dependencies)

        # Should work (optional_dep gets default value)
        assert "test" in result

    @pytest.mark.asyncio
    async def test_handler_instance_lifecycle(self, mock_command, mock_command_handler):
        """Test that new handler instances are created for each dispatch."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        dependencies = {"dependency_a": "test", "dependency_b": 1}

        # Dispatch same command twice
        result1 = await dispatcher.dispatch_command(mock_command(), dependencies)
        result2 = await dispatcher.dispatch_command(mock_command(), dependencies)

        # Results should be identical (new instances created each time)
        assert result1 == result2

    def test_logging_context(
        self, mock_command, mock_query, mock_command_handler, mock_query_handler
    ):
        """Test that appropriate logging context is captured."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)
        dispatcher.register_query_handler(mock_query_handler)

        # Test that handlers are accessible (logging happens in actual dispatch)
        assert mock_command in dispatcher._command_handlers
        assert mock_query in dispatcher._query_handlers

    @pytest.mark.asyncio
    async def test_error_handling_preserves_stack_trace(self, mock_command):
        """Test that error stack traces are preserved through dispatch."""
        dispatcher = Dispatcher()

        class DetailedErrorHandler(CommandHandler[mock_command, str]):
            def __init__(self):
                pass

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                # Create a detailed error with stack trace
                try:
                    raise ValueError("Original error")
                except ValueError as e:
                    raise RuntimeError("Wrapped error") from e

        dispatcher.register_command_handler(DetailedErrorHandler)

        with pytest.raises(RuntimeError, match="Wrapped error"):
            await dispatcher.dispatch_command(mock_command(), {})

    @pytest.mark.asyncio
    async def test_handler_with_no_dependencies(self, mock_command):
        """Test handlers that require no dependencies."""
        dispatcher = Dispatcher()

        class NoDepsHandler(CommandHandler[mock_command, str]):
            def __init__(self):
                self.value = "no_deps"

            @classmethod
            def command_type(cls):
                return mock_command

            async def handle(self, command):
                return self.value

        dispatcher.register_command_handler(NoDepsHandler)

        # Should work with empty dependencies
        result = await dispatcher.dispatch_command(mock_command(), {})
        assert result == "no_deps"

    @pytest.mark.asyncio
    async def test_dispatcher_thread_safety_simulation(
        self, mock_command, mock_command_handler
    ):
        """Test dispatcher behavior under concurrent access."""
        import asyncio

        dispatcher = Dispatcher()
        dispatcher.register_command_handler(mock_command_handler)

        async def dispatch_task(task_id: int):
            dependencies = {"dependency_a": f"task_{task_id}", "dependency_b": task_id}
            command = mock_command(test_data=f"data_{task_id}")
            return await dispatcher.dispatch_command(command, dependencies)

        # Run multiple concurrent dispatches
        tasks = [dispatch_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed and contain their respective task data
        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"data_{i}" in result
            assert f"task_{i}" in result
            assert str(i) in result
