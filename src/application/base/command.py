"""Base command infrastructure for CQRS pattern.

Commands represent write operations that change system state. They use
Pydantic models to enforce validation and schema versioning.
"""

from abc import ABC, abstractmethod

from pydantic import Field, model_validator

from src.application.base.schema import SchemaVersionedModel


class BaseCommand(SchemaVersionedModel, ABC):
    """Base class for all commands in the system.

    Commands are immutable data structures that represent an intent to change
    system state. They include schema version metadata to support
    backwards-compatible evolution.
    """

    user_id: str | None = Field(
        default=None,
        description="Optional identifier of the user initiating the command",
    )

    @model_validator(mode="after")
    def _run_validation(self) -> "BaseCommand":
        """Execute command-specific validation after model creation."""
        self._validate()
        return self

    def ensure_valid(self) -> None:
        """Public hook to rerun command validation when needed."""
        self._validate()

    @abstractmethod
    def _validate(self) -> None:
        """Validate command data.

        Raises:
            ValueError: If command data is invalid
        """
        ...
