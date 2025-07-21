"""Tests for Dispatcher infrastructure."""

import logging
import pytest
from dataclasses import dataclass
from typing import Dict, List, Optional
from unittest.mock import Mock, patch
from uuid import uuid4

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
    metadata: Dict[str, any] = None


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
            metadata={"value": command.value, "timestamp": str(command.timestamp)}
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
        """Handle another command."""
        self.processed_names.append(command.name)
        return f"handled_{command.name}"
    
    @classmethod
    def command_type(cls) -> type[AnotherCommand]:
        return AnotherCommand


class TestQueryHandler(QueryHandler[TestQuery, List[TestResult]]):
    """Test query handler implementation."""
    
    def __init__(self, repository=None, cache=None):
        self.repository = repository
        self.cache = cache
        self.handled_queries = []
    
    async def handle(self, query: TestQuery) -> List[TestResult]:
        """Handle the test query."""
        self.handled_queries.append(query)
        
        if query.search_term == "error":
            raise ValueError("Simulated query error")
        
        # Simulate filtered results
        results = []
        if query.search_term:
            results.append(TestResult(
                id="result_1",
                processed_data=f"found_{query.search_term}",
                metadata={"search": query.search_term}
            ))
        
        return results
    
    @classmethod
    def query_type(cls) -> type[TestQuery]:
        return TestQuery


class AnotherQueryHandler(QueryHandler[AnotherQuery, Dict[str, str]]):
    """Another query handler for testing multiple handlers."""
    
    async def handle(self, query: AnotherQuery) -> Dict[str, str]:
        """Handle another query."""
        return {"filter": query.filter_value, "result": "success"}
    
    @classmethod
    def query_type(cls) -> type[AnotherQuery]:
        return AnotherQuery


# Handlers with complex dependencies
class ComplexCommandHandler(CommandHandler[TestCommand, TestResult]):
    """Handler with multiple dependencies."""
    
    def __init__(self, repository, service, logger, config=None, metrics=None):
        self.repository = repository
        self.service = service
        self.logger = logger
        self.config = config
        self.metrics = metrics
    
    async def handle(self, command: TestCommand) -> TestResult:
        """Handle with all dependencies."""
        return TestResult(
            id="complex",
            processed_data="complex_result",
            metadata={"dependencies": "injected"}
        )
    
    @classmethod
    def command_type(cls) -> type[TestCommand]:
        return TestCommand


class StrictDependencyHandler(CommandHandler[TestCommand, TestResult]):
    """Handler with required dependencies (no defaults)."""
    
    def __init__(self, repository, service):
        self.repository = repository
        self.service = service
    
    async def handle(self, command: TestCommand) -> TestResult:
        """Handle with strict dependencies."""
        return TestResult(
            id="strict",
            processed_data="strict_result",
            metadata={"dependencies": "required"}
        )
    
    @classmethod
    def command_type(cls) -> type[TestCommand]:
        return TestCommand


class TestDispatcher:
    """Test cases for Dispatcher functionality."""
    
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
        dispatcher.register_command_handler(AnotherCommandHandler)
        # Note: This would cause an error in real usage since AnotherCommandHandler
        # doesn't handle TestCommand, but for testing the registration logic:
        # We need a handler that actually handles TestCommand
        
        # Let's test with a proper second handler
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
        assert len(result) == 1
        assert result[0].processed_data == "found_test"
    
    @pytest.mark.asyncio
    async def test_dispatch_command_handler_not_found(self):
        """Test dispatching command with no registered handler."""
        dispatcher = Dispatcher()
        
        command = TestCommand(data="test")
        dependencies = {}
        
        with pytest.raises(HandlerNotFoundError) as exc_info:
            await dispatcher.dispatch_command(command, dependencies)
        
        assert exc_info.value.request_type == "TestCommand"
        assert "No handler registered for TestCommand" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_dispatch_query_handler_not_found(self):
        """Test dispatching query with no registered handler."""
        dispatcher = Dispatcher()
        
        query = TestQuery(search_term="test")
        dependencies = {}
        
        with pytest.raises(HandlerNotFoundError) as exc_info:
            await dispatcher.dispatch_query(query, dependencies)
        
        assert exc_info.value.request_type == "TestQuery"
        assert "No handler registered for TestQuery" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_dispatch_command_handler_error(self):
        """Test command handler throwing an error."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)
        
        # Command that will cause handler to throw error
        command = TestCommand(data="error")
        dependencies = {"repository": Mock(), "service": Mock()}
        
        with pytest.raises(ValueError, match="Simulated processing error"):
            await dispatcher.dispatch_command(command, dependencies)
    
    @pytest.mark.asyncio
    async def test_dispatch_query_handler_error(self):
        """Test query handler throwing an error."""
        dispatcher = Dispatcher()
        dispatcher.register_query_handler(TestQueryHandler)
        
        # Query that will cause handler to throw error
        query = TestQuery(search_term="error")
        dependencies = {"repository": Mock(), "cache": Mock()}
        
        with pytest.raises(ValueError, match="Simulated query error"):
            await dispatcher.dispatch_query(query, dependencies)


class TestDependencyInjection:
    """Test cases for dependency injection functionality."""
    
    def test_dependency_injection_by_name(self):
        """Test dependency injection by parameter name."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)
        
        mock_repo = Mock()
        mock_service = Mock()
        mock_logger = Mock()
        
        dependencies = {
            "repository": mock_repo,
            "service": mock_service,
            "logger": mock_logger
        }
        
        handler = dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
        
        assert handler.repository is mock_repo
        assert handler.service is mock_service
        assert handler.logger is mock_logger
    
    def test_dependency_injection_by_type(self):
        """Test dependency injection by type annotation."""
        class Repository:
            pass
        
        class Service:
            pass
        
        class TypedHandler(CommandHandler[TestCommand, str]):
            def __init__(self, repo: Repository, svc: Service):
                self.repo = repo
                self.svc = svc
            
            async def handle(self, command: TestCommand) -> str:
                return "typed"
            
            @classmethod
            def command_type(cls) -> type[TestCommand]:
                return TestCommand
        
        dispatcher = Dispatcher()
        
        repo_instance = Repository()
        service_instance = Service()
        
        dependencies = {
            "repository": repo_instance,  # Will match by type
            "service": service_instance   # Will match by type
        }
        
        handler = dispatcher._get_or_create_handler(TypedHandler, dependencies)
        
        assert handler.repo is repo_instance
        assert handler.svc is service_instance
    
    def test_dependency_injection_missing_required_dependency(self):
        """Test error when required dependency is missing."""
        dispatcher = Dispatcher()
        
        # Handler requires both repository and service but we only provide service
        dependencies = {"service": Mock()}
        
        with pytest.raises(DependencyError) as exc_info:
            dispatcher._get_or_create_handler(StrictDependencyHandler, dependencies)
        
        assert exc_info.value.dependency_name == "repository"
        assert "Required dependency 'repository' could not be resolved" in str(exc_info.value)
    
    def test_dependency_injection_with_optional_dependencies(self):
        """Test dependency injection with optional parameters."""
        class OptionalHandler(CommandHandler[TestCommand, str]):
            def __init__(self, repository, service=None, config=None):
                self.repository = repository
                self.service = service
                self.config = config
            
            async def handle(self, command: TestCommand) -> str:
                return "optional"
            
            @classmethod
            def command_type(cls) -> type[TestCommand]:
                return TestCommand
        
        dispatcher = Dispatcher()
        
        # Provide only required dependency
        dependencies = {"repository": Mock()}
        
        handler = dispatcher._get_or_create_handler(OptionalHandler, dependencies)
        
        assert handler.repository is not None
        assert handler.service is None
        assert handler.config is None
    
    def test_dependency_injection_caching(self):
        """Test that handler instances are cached."""
        dispatcher = Dispatcher()
        
        dependencies = {"repository": Mock(), "service": Mock()}
        
        # Get handler instance twice
        handler1 = dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
        handler2 = dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
        
        # Should be the same instance
        assert handler1 is handler2
        
        # Should be cached
        assert TestCommandHandler in dispatcher._handler_instances
    
    def test_clear_cache(self):
        """Test clearing the handler instance cache."""
        dispatcher = Dispatcher()
        
        dependencies = {"repository": Mock(), "service": Mock()}
        
        # Create handler instance
        handler = dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
        assert TestCommandHandler in dispatcher._handler_instances
        
        # Clear cache
        dispatcher.clear_cache()
        assert len(dispatcher._handler_instances) == 0
        
        # Next call should create new instance
        handler2 = dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
        assert handler is not handler2
    
    def test_complex_dependency_injection(self):
        """Test dependency injection with complex handler."""
        dispatcher = Dispatcher()
        
        mock_repo = Mock()
        mock_service = Mock()
        mock_logger = Mock()
        mock_config = {"setting": "value"}
        
        # Provide all dependencies
        dependencies = {
            "repository": mock_repo,
            "service": mock_service,
            "logger": mock_logger,
            "config": mock_config,
            # metrics is optional and not provided
        }
        
        handler = dispatcher._get_or_create_handler(ComplexCommandHandler, dependencies)
        
        assert handler.repository is mock_repo
        assert handler.service is mock_service
        assert handler.logger is mock_logger
        assert handler.config is mock_config
        assert handler.metrics is None  # Optional, not provided
    
    def test_dependency_injection_no_annotation_no_default(self):
        """Test dependency injection failure for parameter without annotation or default."""
        class NoAnnotationHandler(CommandHandler[TestCommand, str]):
            def __init__(self, repository, mystery_param):  # mystery_param has no annotation, no default
                self.repository = repository
                self.mystery_param = mystery_param
            
            async def handle(self, command: TestCommand) -> str:
                return "handled"
            
            @classmethod
            def command_type(cls) -> type[TestCommand]:
                return TestCommand
        
        dispatcher = Dispatcher()
        dependencies = {"repository": Mock()}  # missing mystery_param
        
        with pytest.raises(DependencyError) as exc_info:
            dispatcher._get_or_create_handler(NoAnnotationHandler, dependencies)
        
        assert exc_info.value.dependency_name == "mystery_param"
        assert "Required dependency 'mystery_param' could not be resolved" in str(exc_info.value)
    
    def test_dependency_injection_typed_param_no_match_no_default(self):
        """Test dependency injection failure for typed parameter that can't be matched."""
        class CustomType:
            pass
        
        class TypedHandler(CommandHandler[TestCommand, str]):
            def __init__(self, repository, custom_service: CustomType):  # typed but no matching dependency
                self.repository = repository
                self.custom_service = custom_service
            
            async def handle(self, command: TestCommand) -> str:
                return "handled"
            
            @classmethod
            def command_type(cls) -> type[TestCommand]:
                return TestCommand
        
        dispatcher = Dispatcher()
        dependencies = {"repository": Mock(), "wrong_type": "not_a_CustomType"}
        
        with pytest.raises(DependencyError) as exc_info:
            dispatcher._get_or_create_handler(TypedHandler, dependencies)
        
        assert exc_info.value.dependency_name == "custom_service"
        assert "Required dependency 'custom_service' could not be resolved" in str(exc_info.value)


class TestExceptionHandling:
    """Test cases for exception handling."""
    
    @pytest.mark.asyncio
    async def test_command_validation_error(self):
        """Test handling of command validation errors."""
        dispatcher = Dispatcher()
        dispatcher.register_command_handler(TestCommandHandler)
        
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
    
    def test_dependency_resolution_error(self):
        """Test dependency resolution errors."""
        dispatcher = Dispatcher()
        
        # Missing required dependencies
        dependencies = {}  # Empty dependencies
        
        with pytest.raises(DependencyError, match="Required dependency 'repository' could not be resolved"):
            dispatcher._get_or_create_handler(StrictDependencyHandler, dependencies)
    
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
                    "command_id": str(command.command_id),
                    "command_type": "TestCommand",
                    "user_id": command.user_id,
                    "correlation_id": None
                }
            )
            
            # Check that success log was called
            mock_logger.info.assert_any_call("Command processed successfully: TestCommand")
    
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
                    "query_id": str(query.query_id),
                    "query_type": "TestQuery",
                    "user_id": query.user_id,
                    "page": query.page,
                    "page_size": query.page_size
                }
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
                exc_info=True
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
                exc_info=True
            )
    
    def test_handler_registration_logging(self):
        """Test logging during handler registration."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            
            dispatcher.register_command_handler(TestCommandHandler)
            
            mock_logger.debug.assert_called_with(
                "Registered command handler: TestCommandHandler for TestCommand"
            )
            
            dispatcher.register_query_handler(TestQueryHandler)
            
            mock_logger.debug.assert_called_with(
                "Registered query handler: TestQueryHandler for TestQuery"
            )
    
    def test_handler_creation_logging(self):
        """Test logging during handler instance creation."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            
            dependencies = {"repository": Mock(), "service": Mock()}
            
            dispatcher._get_or_create_handler(TestCommandHandler, dependencies)
            
            mock_logger.debug.assert_any_call("Created handler instance: TestCommandHandler")
    
    def test_cache_clear_logging(self):
        """Test logging when cache is cleared."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            
            dispatcher.clear_cache()
            
            mock_logger.debug.assert_called_with("Cleared handler instance cache")
    
    @pytest.mark.asyncio
    async def test_logging_with_correlation_id(self):
        """Test logging includes correlation ID when present."""
        with patch('src.application.base.dispatcher.logger') as mock_logger:
            dispatcher = Dispatcher()
            dispatcher.register_command_handler(TestCommandHandler)
            
            correlation_id = uuid4()
            command = TestCommand(
                data="test_data",
                correlation_id=correlation_id,
                user_id="user123"
            )
            dependencies = {"repository": Mock(), "service": Mock()}
            
            await dispatcher.dispatch_command(command, dependencies)
            
            # Check that correlation_id and user_id are logged
            mock_logger.info.assert_any_call(
                "Dispatching command: TestCommand",
                extra={
                    "command_id": str(command.command_id),
                    "command_type": "TestCommand",
                    "user_id": "user123",
                    "correlation_id": str(correlation_id)
                }
            )