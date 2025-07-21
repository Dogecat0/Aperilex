"""Base command infrastructure for CQRS pattern.

Commands represent write operations that change system state. They contain
all necessary data to perform an operation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseCommand(ABC):
    """Base class for all commands in the system.

    Commands are immutable data structures that represent an intent to change
    system state.

    Attributes:
        user_id: Optional identifier of the user initiating the command
    """

    user_id: str | None = None

    def __post_init__(self) -> None:
        """Validate command data after initialization."""
        self.validate()

    @abstractmethod
    def validate(self) -> None:
        """Validate command data.

        Raises:
            ValueError: If command data is invalid
        """
        pass
