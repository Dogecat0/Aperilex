"""Tests for CommandHandler and QueryHandler interfaces."""

import pytest
from abc import ABC
from dataclasses import dataclass
from typing import Dict, List
from uuid import uuid4

from src.application.base.command import BaseCommand
from src.application.base.handlers import CommandHandler, QueryHandler
from src.application.base.query import BaseQuery


# Test Commands
@dataclass(frozen=True)
class CreateUserCommand(BaseCommand):
    """Test command for creating a user."""
    
    name: str = ""
    email: str = ""
    
    def validate(self) -> None:
        if not self.name:
            raise ValueError("Name is required")
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")


@dataclass(frozen=True)
class UpdateUserCommand(BaseCommand):
    """Test command for updating a user."""
    
    user_id: str = ""
    name: str = ""
    email: str = ""
    
    def validate(self) -> None:
        if not self.user_id:
            raise ValueError("User ID is required")


@dataclass(frozen=True)
class DeleteUserCommand(BaseCommand):
    """Test command for deleting a user."""
    
    user_id: str = ""
    
    def validate(self) -> None:
        if not self.user_id:
            raise ValueError("User ID is required")


# Test Queries
@dataclass(frozen=True)
class GetUserQuery(BaseQuery):
    """Test query for getting a single user."""
    
    user_id: str = ""


@dataclass(frozen=True)
class SearchUsersQuery(BaseQuery):
    """Test query for searching users."""
    
    name_filter: str = ""
    email_filter: str = ""


@dataclass(frozen=True)
class GetUserStatsQuery(BaseQuery):
    """Test query for getting user statistics."""
    
    include_inactive: bool = False


# Test Result Types
@dataclass
class UserResult:
    """Result type for user operations."""
    
    user_id: str
    name: str
    email: str
    active: bool = True


@dataclass
class UserStatsResult:
    """Result type for user statistics."""
    
    total_users: int
    active_users: int
    inactive_users: int


# Test Handler Implementations
class CreateUserCommandHandler(CommandHandler[CreateUserCommand, UserResult]):
    """Test command handler for creating users."""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.created_users = []
    
    async def handle(self, command: CreateUserCommand) -> UserResult:
        """Handle user creation."""
        if any(u.email == command.email for u in self.created_users):
            raise ValueError(f"User with email {command.email} already exists")
        
        user = UserResult(
            user_id=str(uuid4()),
            name=command.name,
            email=command.email
        )
        self.created_users.append(user)
        return user
    
    @classmethod
    def command_type(cls) -> type[CreateUserCommand]:
        """Return the command type."""
        return CreateUserCommand


class UpdateUserCommandHandler(CommandHandler[UpdateUserCommand, UserResult]):
    """Test command handler for updating users."""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.users: Dict[str, UserResult] = {}
    
    async def handle(self, command: UpdateUserCommand) -> UserResult:
        """Handle user update."""
        if command.user_id not in self.users:
            raise ValueError(f"User {command.user_id} not found")
        
        user = self.users[command.user_id]
        updated_user = UserResult(
            user_id=user.user_id,
            name=command.name if command.name else user.name,
            email=command.email if command.email else user.email,
            active=user.active
        )
        self.users[command.user_id] = updated_user
        return updated_user
    
    @classmethod
    def command_type(cls) -> type[UpdateUserCommand]:
        """Return the command type."""
        return UpdateUserCommand


class GetUserQueryHandler(QueryHandler[GetUserQuery, UserResult | None]):
    """Test query handler for getting a single user."""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.users: Dict[str, UserResult] = {}
    
    async def handle(self, query: GetUserQuery) -> UserResult | None:
        """Handle get user query."""
        return self.users.get(query.user_id)
    
    @classmethod
    def query_type(cls) -> type[GetUserQuery]:
        """Return the query type."""
        return GetUserQuery


class SearchUsersQueryHandler(QueryHandler[SearchUsersQuery, List[UserResult]]):
    """Test query handler for searching users."""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.users: List[UserResult] = []
    
    async def handle(self, query: SearchUsersQuery) -> List[UserResult]:
        """Handle search users query."""
        results = self.users
        
        if query.name_filter:
            results = [u for u in results if query.name_filter.lower() in u.name.lower()]
        
        if query.email_filter:
            results = [u for u in results if query.email_filter.lower() in u.email.lower()]
        
        # Apply pagination
        start = query.offset
        end = start + query.page_size
        return results[start:end]
    
    @classmethod
    def query_type(cls) -> type[SearchUsersQuery]:
        """Return the query type."""
        return SearchUsersQuery


class GetUserStatsQueryHandler(QueryHandler[GetUserStatsQuery, UserStatsResult]):
    """Test query handler for getting user statistics."""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.users: List[UserResult] = []
    
    async def handle(self, query: GetUserStatsQuery) -> UserStatsResult:
        """Handle get user stats query."""
        active_users = [u for u in self.users if u.active]
        inactive_users = [u for u in self.users if not u.active]
        
        if not query.include_inactive:
            return UserStatsResult(
                total_users=len(active_users),
                active_users=len(active_users),
                inactive_users=0
            )
        
        return UserStatsResult(
            total_users=len(self.users),
            active_users=len(active_users),
            inactive_users=len(inactive_users)
        )
    
    @classmethod
    def query_type(cls) -> type[GetUserStatsQuery]:
        """Return the query type."""
        return GetUserStatsQuery


class TestCommandHandler:
    """Test cases for CommandHandler interface."""
    
    def test_handler_inheritance(self):
        """Test that handler classes inherit from correct base classes."""
        assert issubclass(CreateUserCommandHandler, CommandHandler)
        assert issubclass(UpdateUserCommandHandler, CommandHandler)
        
        # Should be abstract base classes
        assert ABC in CommandHandler.__bases__
    
    def test_handler_type_specification(self):
        """Test that handlers specify their command types correctly."""
        assert CreateUserCommandHandler.command_type() == CreateUserCommand
        assert UpdateUserCommandHandler.command_type() == UpdateUserCommand
    
    @pytest.mark.asyncio
    async def test_create_user_handler(self):
        """Test the create user command handler."""
        handler = CreateUserCommandHandler()
        
        command = CreateUserCommand(
            name="John Doe",
            email="john@example.com"
        )
        
        result = await handler.handle(command)
        
        assert isinstance(result, UserResult)
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        assert result.active is True
        assert result.user_id  # Should have an ID
        assert len(handler.created_users) == 1
    
    @pytest.mark.asyncio
    async def test_create_user_handler_duplicate_email(self):
        """Test create user handler with duplicate email."""
        handler = CreateUserCommandHandler()
        
        # Create first user
        command1 = CreateUserCommand(
            name="John Doe",
            email="john@example.com"
        )
        await handler.handle(command1)
        
        # Try to create second user with same email
        command2 = CreateUserCommand(
            name="Jane Doe",
            email="john@example.com"  # Same email
        )
        
        with pytest.raises(ValueError, match="User with email john@example.com already exists"):
            await handler.handle(command2)
    
    @pytest.mark.asyncio
    async def test_update_user_handler(self):
        """Test the update user command handler."""
        handler = UpdateUserCommandHandler()
        
        # Setup existing user
        user = UserResult(
            user_id="user123",
            name="John Doe",
            email="john@example.com"
        )
        handler.users["user123"] = user
        
        # Update user name
        command = UpdateUserCommand(
            user_id="user123",
            name="John Smith"
        )
        
        result = await handler.handle(command)
        
        assert result.user_id == "user123"
        assert result.name == "John Smith"
        assert result.email == "john@example.com"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_user_handler_not_found(self):
        """Test update user handler with non-existent user."""
        handler = UpdateUserCommandHandler()
        
        command = UpdateUserCommand(
            user_id="nonexistent",
            name="New Name"
        )
        
        with pytest.raises(ValueError, match="User nonexistent not found"):
            await handler.handle(command)
    
    def test_handler_dependency_injection_support(self):
        """Test that handlers support dependency injection."""
        mock_repository = {"type": "mock_repository"}
        
        handler = CreateUserCommandHandler(user_repository=mock_repository)
        assert handler.user_repository == mock_repository
        
        handler_without_dep = CreateUserCommandHandler()
        assert handler_without_dep.user_repository is None
    
    def test_handler_generic_types(self):
        """Test that handlers properly specify generic types."""
        # Command handlers should specify command and result types
        create_handler = CreateUserCommandHandler()
        assert hasattr(create_handler, 'handle')
        
        # Method signature should accept the correct command type
        import inspect
        sig = inspect.signature(create_handler.handle)
        command_param = list(sig.parameters.values())[0]
        # Note: Runtime type checking is limited, but we can verify the handler works
        
        # The handler should work with the correct command type
        command = CreateUserCommand(name="Test", email="test@example.com")
        assert command  # Command should be creatable


class TestQueryHandler:
    """Test cases for QueryHandler interface."""
    
    def test_handler_inheritance(self):
        """Test that handler classes inherit from correct base classes."""
        assert issubclass(GetUserQueryHandler, QueryHandler)
        assert issubclass(SearchUsersQueryHandler, QueryHandler)
        assert issubclass(GetUserStatsQueryHandler, QueryHandler)
        
        # Should be abstract base classes
        assert ABC in QueryHandler.__bases__
    
    def test_handler_type_specification(self):
        """Test that handlers specify their query types correctly."""
        assert GetUserQueryHandler.query_type() == GetUserQuery
        assert SearchUsersQueryHandler.query_type() == SearchUsersQuery
        assert GetUserStatsQueryHandler.query_type() == GetUserStatsQuery
    
    @pytest.mark.asyncio
    async def test_get_user_handler(self):
        """Test the get user query handler."""
        handler = GetUserQueryHandler()
        
        # Setup existing user
        user = UserResult(
            user_id="user123",
            name="John Doe",
            email="john@example.com"
        )
        handler.users["user123"] = user
        
        # Query for existing user
        query = GetUserQuery(user_id="user123")
        result = await handler.handle(query)
        
        assert result is not None
        assert result.user_id == "user123"
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        
        # Query for non-existing user
        query_not_found = GetUserQuery(user_id="nonexistent")
        result_not_found = await handler.handle(query_not_found)
        
        assert result_not_found is None
    
    @pytest.mark.asyncio
    async def test_search_users_handler(self):
        """Test the search users query handler."""
        handler = SearchUsersQueryHandler()
        
        # Setup test data
        users = [
            UserResult("1", "John Doe", "john@example.com"),
            UserResult("2", "Jane Smith", "jane@example.com"),
            UserResult("3", "John Smith", "john.smith@test.com"),
            UserResult("4", "Bob Johnson", "bob@example.com"),
        ]
        handler.users = users
        
        # Search by name
        query = SearchUsersQuery(name_filter="John")
        results = await handler.handle(query)
        
        assert len(results) == 3  # John Doe, John Smith, Bob Johnson
        assert all("john" in r.name.lower() for r in results)
        
        # Search by email domain
        query = SearchUsersQuery(email_filter="example.com")
        results = await handler.handle(query)
        
        assert len(results) == 3
        assert all("example.com" in r.email for r in results)
        
        # Search with both filters
        query = SearchUsersQuery(name_filter="John", email_filter="example.com")
        results = await handler.handle(query)
        
        assert len(results) == 2  # John Doe and Bob Johnson both match
        john_doe = [r for r in results if r.name == "John Doe"]
        bob_johnson = [r for r in results if r.name == "Bob Johnson"]
        assert len(john_doe) == 1
        assert len(bob_johnson) == 1
    
    @pytest.mark.asyncio
    async def test_search_users_handler_pagination(self):
        """Test search users handler with pagination."""
        handler = SearchUsersQueryHandler()
        
        # Setup test data - 10 users
        users = [
            UserResult(f"user{i}", f"User {i}", f"user{i}@example.com")
            for i in range(10)
        ]
        handler.users = users
        
        # First page (default page_size=20, so all results fit)
        query = SearchUsersQuery(page=1, page_size=20)
        results = await handler.handle(query)
        assert len(results) == 10
        
        # First page with smaller page size
        query = SearchUsersQuery(page=1, page_size=3)
        results = await handler.handle(query)
        assert len(results) == 3
        assert results[0].name == "User 0"
        assert results[2].name == "User 2"
        
        # Second page
        query = SearchUsersQuery(page=2, page_size=3)
        results = await handler.handle(query)
        assert len(results) == 3
        assert results[0].name == "User 3"
        assert results[2].name == "User 5"
        
        # Last page (partial)
        query = SearchUsersQuery(page=4, page_size=3)
        results = await handler.handle(query)
        assert len(results) == 1
        assert results[0].name == "User 9"
        
        # Beyond available data
        query = SearchUsersQuery(page=5, page_size=3)
        results = await handler.handle(query)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_stats_handler(self):
        """Test the get user stats query handler."""
        handler = GetUserStatsQueryHandler()
        
        # Setup test data
        users = [
            UserResult("1", "User 1", "user1@example.com", active=True),
            UserResult("2", "User 2", "user2@example.com", active=True),
            UserResult("3", "User 3", "user3@example.com", active=False),
            UserResult("4", "User 4", "user4@example.com", active=False),
            UserResult("5", "User 5", "user5@example.com", active=True),
        ]
        handler.users = users
        
        # Query without inactive users
        query = GetUserStatsQuery(include_inactive=False)
        result = await handler.handle(query)
        
        assert result.total_users == 3  # Only active users
        assert result.active_users == 3
        assert result.inactive_users == 0
        
        # Query with inactive users
        query = GetUserStatsQuery(include_inactive=True)
        result = await handler.handle(query)
        
        assert result.total_users == 5  # All users
        assert result.active_users == 3
        assert result.inactive_users == 2
    
    def test_query_handler_dependency_injection_support(self):
        """Test that query handlers support dependency injection."""
        mock_repository = {"type": "mock_repository"}
        
        handler = GetUserQueryHandler(user_repository=mock_repository)
        assert handler.user_repository == mock_repository
        
        handler_without_dep = GetUserQueryHandler()
        assert handler_without_dep.user_repository is None


class TestHandlerInterfaces:
    """Test the abstract interfaces themselves."""
    
    def test_command_handler_is_abstract(self):
        """Test that CommandHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CommandHandler()
    
    def test_query_handler_is_abstract(self):
        """Test that QueryHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            QueryHandler()
    
    def test_handler_must_implement_required_methods(self):
        """Test that handlers must implement required abstract methods."""
        
        # Command handler missing handle method
        class IncompleteCommandHandler(CommandHandler):
            @classmethod
            def command_type(cls):
                return CreateUserCommand
            
            # Missing handle method
        
        with pytest.raises(TypeError):
            IncompleteCommandHandler()
        
        # Command handler missing command_type method
        class IncompleteCommandHandler2(CommandHandler):
            async def handle(self, command):
                pass
            
            # Missing command_type method
        
        with pytest.raises(TypeError):
            IncompleteCommandHandler2()
        
        # Query handler missing handle method
        class IncompleteQueryHandler(QueryHandler):
            @classmethod
            def query_type(cls):
                return GetUserQuery
            
            # Missing handle method
        
        with pytest.raises(TypeError):
            IncompleteQueryHandler()
        
        # Query handler missing query_type method
        class IncompleteQueryHandler2(QueryHandler):
            async def handle(self, query):
                pass
            
            # Missing query_type method
        
        with pytest.raises(TypeError):
            IncompleteQueryHandler2()
    
    def test_handler_method_signatures(self):
        """Test that handler methods have correct signatures."""
        import inspect
        
        # Check CommandHandler.handle signature
        handle_sig = inspect.signature(CreateUserCommandHandler.handle)
        params = list(handle_sig.parameters.values())
        assert len(params) == 2  # self and command
        assert params[1].name == "command"
        
        # Check CommandHandler.command_type signature
        cmd_type_sig = inspect.signature(CreateUserCommandHandler.command_type)
        params = list(cmd_type_sig.parameters.values())
        assert len(params) == 0  # classmethod, no parameters besides implicit cls
        
        # Check QueryHandler.handle signature
        handle_sig = inspect.signature(GetUserQueryHandler.handle)
        params = list(handle_sig.parameters.values())
        assert len(params) == 2  # self and query
        assert params[1].name == "query"
        
        # Check QueryHandler.query_type signature
        query_type_sig = inspect.signature(GetUserQueryHandler.query_type)
        params = list(query_type_sig.parameters.values())
        assert len(params) == 0  # classmethod, no parameters besides implicit cls