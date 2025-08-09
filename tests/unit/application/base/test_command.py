"""Tests for BaseCommand infrastructure."""

from dataclasses import dataclass

import pytest

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

        assert command.user_id is None
        assert command.data == "test"

    def test_command_creation_with_explicit_values(self):
        """Test creating a command with explicit values."""
        user_id = "user123"

        command = ValidTestCommand(user_id=user_id, data="custom_data")

        assert command.user_id == user_id
        assert command.data == "custom_data"

    def test_command_immutability(self):
        """Test that commands are immutable (frozen dataclass)."""
        command = ValidTestCommand(data="original")

        # Should not be able to modify command attributes
        with pytest.raises(AttributeError):
            command.data = "modified"

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
            tags: list[str] = None

            def __post_init__(self):
                # Handle mutable default
                if self.tags is None:
                    object.__setattr__(self, 'tags', [])
                super().__post_init__()

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

        # Valid complex command
        command = ComplexCommand(
            email="test@example.com", age=30, tags=["tag1", "tag2"]
        )
        assert command.email == "test@example.com"
        assert command.age == 30
        assert command.tags == ["tag1", "tag2"]

        # Invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            ComplexCommand(email="invalid-email", age=30, tags=["tag1"])

        # Invalid age
        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            ComplexCommand(email="test@example.com", age=-5, tags=["tag1"])

        with pytest.raises(ValueError, match="Age must be between 0 and 150"):
            ComplexCommand(email="test@example.com", age=200, tags=["tag1"])

        # No tags
        with pytest.raises(ValueError, match="At least one tag is required"):
            ComplexCommand(email="test@example.com", age=30, tags=[])

        # Empty tags
        with pytest.raises(ValueError, match="Tags cannot be empty"):
            ComplexCommand(email="test@example.com", age=30, tags=["tag1", "  "])

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
        command1 = ValidTestCommand(user_id="user1", data="test_data")
        command2 = ValidTestCommand(user_id="user1", data="test_data")
        command3 = ValidTestCommand(user_id="user2", data="test_data")

        # Same data should be equal
        assert command1 == command2

        # Different data should not be equal
        assert command1 != command3

        # Same data should have same hash
        assert hash(command1) == hash(command2)

        # Can be used in sets
        command_set = {command1, command2, command3}
        assert len(command_set) == 2  # command1 and command2 are identical

    def test_abstract_base_class(self):
        """Test that BaseCommand cannot be instantiated directly."""
        # This should fail because BaseCommand.validate is abstract
        with pytest.raises(TypeError):
            BaseCommand()

    def test_post_init_validation_timing(self):
        """Test that validation happens during initialization."""
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
