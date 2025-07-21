"""Base command infrastructure for CQRS pattern.

Commands represent write operations that change system state. They contain
all necessary data to perform an operation and include metadata for tracking
and auditing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class BaseCommand(ABC):
    """Base class for all commands in the system.

    Commands are immutable data structures that represent an intent to change
    system state. They include metadata for correlation, auditing, and tracking.

    Attributes:
        command_id: Unique identifier for this command instance
        timestamp: When the command was created
        correlation_id: Optional ID to group related operations
        user_id: Optional identifier of the user initiating the command
    """

    command_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: UUID | None = None
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
