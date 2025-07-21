"""Tests for BaseCommand infrastructure."""

import pytest
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from unittest.mock import patch

from src.application.base.command import BaseCommand


@dataclass(frozen=True)
class TestCommand(BaseCommand):
    """Test command implementation for testing."""
    
    name: str = ""
    value: int = 0
    
    def validate(self) -> None:
        """Validate test command data."""
        if not self.name:
            raise ValueError("Name cannot be empty")
        if self.value < 0:
            raise ValueError("Value must be non-negative")


@dataclass(frozen=True)
class ValidTestCommand(BaseCommand):
    """Always valid test command."""
    
    data: str = "test"
    
    def validate(self) -> None:
        """Always passes validation."""
        pass


class TestBaseCommand:
    """Test cases for BaseCommand infrastructure."""
    
    def test_command_creation_with_defaults(self):
        """Test creating a command with default values."""
        command = ValidTestCommand()
        
        assert isinstance(command.command_id, UUID)
        assert isinstance(command.timestamp, datetime)
        assert command.correlation_id is None
        assert command.user_id is None
        assert command.data == "test"
    
    def test_command_creation_with_explicit_values(self):
        """Test creating a command with explicit values."""
        command_id = uuid4()
        correlation_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        user_id = "user123"
        
        command = ValidTestCommand(
            command_id=command_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            user_id=user_id,
            data="custom_data"
        )
        
        assert command.command_id == command_id
        assert command.timestamp == timestamp
        assert command.correlation_id == correlation_id
        assert command.user_id == user_id
        assert command.data == "custom_data"
    
    def test_command_immutability(self):
        """Test that commands are immutable (frozen dataclass)."""
        command = ValidTestCommand(data="original")
        
        # Should not be able to modify command attributes
        with pytest.raises(AttributeError):
            command.data = "modified"
        
        with pytest.raises(AttributeError):
            command.command_id = uuid4()
        
        with pytest.raises(AttributeError):
            command.user_id = "new_user"
    
    def test_validation_called_on_init(self):
        """Test that validation is called during initialization."""
        # Valid command should succeed
        command = TestCommand(name="test", value=10)
        assert command.name == "test"
        assert command.value == 10
        
        # Invalid command should raise ValueError
        with pytest.raises(ValueError, match="Name cannot be empty"):
            TestCommand(name="", value=10)
        
        with pytest.raises(ValueError, match="Value must be non-negative"):
            TestCommand(name="test", value=-1)
    
    def test_validation_with_complex_data(self):
        """Test validation with more complex data structures."""
        @dataclass(frozen=True)
        class ComplexCommand(BaseCommand):
            """Command with complex validation rules."""
            
            email: str = ""
            age: int = 0
            tags: list[str] = field(default_factory=list)
            
            def validate(self) -> None:
                """Validate complex command data."""
                if not self.email or "@" not in self.email:
                    raise ValueError("Invalid email format")
                if self.age < 0 or self.age > 150:
                    raise ValueError("Age must be between 0 and 150")
                if not self.tags:
                    raise ValueError("At least one tag is required")
                if any(not tag.strip() for tag in self.tags):
                    raise ValueError("Tags cannot be empty")
        
        # Valid command
        command = ComplexCommand(
            email="user@example.com",
            age=25,
            tags=["important", "urgent"]
        )
        assert command.email == "user@example.com"
        assert command.age == 25
        assert command.tags == ["important", "urgent"]
        
        # Invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            ComplexCommand(email="invalid", age=25, tags=["tag1"])
        
        # Invalid age
        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            ComplexCommand(email="user@example.com", age=-1, tags=["tag1"])
        
        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            ComplexCommand(email="user@example.com", age=200, tags=["tag1"])
        
        # Invalid tags
        with pytest.raises(ValueError, match="At least one tag is required"):
            ComplexCommand(email="user@example.com", age=25, tags=[])
        
        with pytest.raises(ValueError, match="Tags cannot be empty"):
            ComplexCommand(email="user@example.com", age=25, tags=["", "valid"])
    
    def test_timestamp_generation(self):
        """Test that timestamps are automatically generated."""
        before = datetime.utcnow()
        command = ValidTestCommand()
        after = datetime.utcnow()
        
        assert isinstance(command.timestamp, datetime)
        assert before <= command.timestamp <= after
    
    def test_command_id_uniqueness(self):
        """Test that each command gets a unique ID."""
        command1 = ValidTestCommand()
        command2 = ValidTestCommand()
        
        assert command1.command_id != command2.command_id
        assert isinstance(command1.command_id, UUID)
        assert isinstance(command2.command_id, UUID)
    
    def test_correlation_id_propagation(self):
        """Test correlation ID for request tracking."""
        correlation_id = uuid4()
        
        command1 = ValidTestCommand(correlation_id=correlation_id)
        command2 = ValidTestCommand(correlation_id=correlation_id)
        
        # Both commands share the same correlation ID
        assert command1.correlation_id == correlation_id
        assert command2.correlation_id == correlation_id
        assert command1.correlation_id == command2.correlation_id
        
        # But have different command IDs
        assert command1.command_id != command2.command_id
    
    def test_user_id_tracking(self):
        """Test user ID for auditing purposes."""
        user_id = "user123"
        
        command = ValidTestCommand(user_id=user_id)
        assert command.user_id == user_id
        
        # Default should be None
        command_no_user = ValidTestCommand()
        assert command_no_user.user_id is None
    
    def test_command_equality_and_hashing(self):
        """Test command equality and hash behavior."""
        command_id = uuid4()
        timestamp = datetime.now()
        correlation_id = uuid4()
        
        command1 = ValidTestCommand(
            command_id=command_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            user_id="user1",
            data="test_data"
        )
        
        command2 = ValidTestCommand(
            command_id=command_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            user_id="user1",
            data="test_data"
        )
        
        command3 = ValidTestCommand(
            command_id=uuid4(),  # Different ID
            timestamp=timestamp,
            correlation_id=correlation_id,
            user_id="user1",
            data="test_data"
        )
        
        # Same data should be equal
        assert command1 == command2
        
        # Different data should not be equal
        assert command1 != command3
        
        # Same data should have same hash
        assert hash(command1) == hash(command2)
        
        # Can be used in sets
        command_set = {command1, command2, command3}
        assert len(command_set) == 2  # command1 and command2 are identical
    
    def test_command_with_optional_fields(self):
        """Test commands with optional fields."""
        @dataclass(frozen=True)
        class OptionalCommand(BaseCommand):
            """Command with optional fields."""
            
            required_field: str = ""
            optional_field: str = None
            optional_number: int = 0
            
            def validate(self) -> None:
                """Validate required field only."""
                if not self.required_field:
                    raise ValueError("Required field cannot be empty")
        
        # With required field set to non-empty
        command1 = OptionalCommand(required_field="test")
        assert command1.required_field == "test"
        assert command1.optional_field is None
        assert command1.optional_number == 0
        
        # With all fields
        command2 = OptionalCommand(
            required_field="test",
            optional_field="optional",
            optional_number=42
        )
        assert command2.required_field == "test"
        assert command2.optional_field == "optional"
        assert command2.optional_number == 42
        
        # Invalid required field - explicitly pass empty string
        with pytest.raises(ValueError, match="Required field cannot be empty"):
            OptionalCommand(required_field="")
    
    def test_command_with_complex_types(self):
        """Test commands with complex field types."""
        
        @dataclass(frozen=True)
        class ComplexTypeCommand(BaseCommand):
            """Command with complex field types."""
            
            metadata: Dict[str, any] = field(default_factory=dict)
            tags: List[str] = field(default_factory=list)
            config: Optional[Dict[str, str]] = None
            
            def validate(self) -> None:
                """Validate complex types."""
                if not isinstance(self.metadata, dict):
                    raise ValueError("Metadata must be a dictionary")
                if not isinstance(self.tags, list):
                    raise ValueError("Tags must be a list")
                if self.config is not None and not isinstance(self.config, dict):
                    raise ValueError("Config must be a dictionary or None")
        
        metadata = {"key1": "value1", "key2": 42}
        tags = ["tag1", "tag2", "tag3"]
        config = {"setting1": "value1", "setting2": "value2"}
        
        command = ComplexTypeCommand(
            metadata=metadata,
            tags=tags,
            config=config
        )
        
        assert command.metadata == metadata
        assert command.tags == tags
        assert command.config == config
        
        # Test without optional config
        command_no_config = ComplexTypeCommand(
            metadata=metadata,
            tags=tags
        )
        assert command_no_config.config is None
    
    def test_post_init_validation_timing(self):
        """Test that __post_init__ is called and validation happens at the right time."""
        validation_calls = []
        
        @dataclass(frozen=True)
        class TrackingCommand(BaseCommand):
            """Command that tracks validation calls."""
            
            value: int = 0
            
            def validate(self) -> None:
                """Track when validation is called."""
                validation_calls.append(f"Validating with value: {self.value}")
                if self.value < 0:
                    raise ValueError("Value must be non-negative")
        
        # Clear previous calls
        validation_calls.clear()
        
        # Create valid command
        command = TrackingCommand(value=10)
        assert len(validation_calls) == 1
        assert validation_calls[0] == "Validating with value: 10"
        assert command.value == 10
        
        # Create invalid command
        validation_calls.clear()
        with pytest.raises(ValueError, match="Value must be non-negative"):
            TrackingCommand(value=-5)
        
        assert len(validation_calls) == 1
        assert validation_calls[0] == "Validating with value: -5"