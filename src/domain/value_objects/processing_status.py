"""Processing status enumeration for filing workflow."""

from enum import Enum


class ProcessingStatus(str, Enum):
    """Processing status for filing workflow.

    Represents the current state of a filing in the processing pipeline.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def can_transition_to(self, new_status: "ProcessingStatus") -> bool:
        """Check if transition to new status is allowed.

        Args:
            new_status: Target status to transition to

        Returns:
            True if transition is allowed
        """
        # Define allowed transitions
        allowed_transitions = {
            ProcessingStatus.PENDING: {
                ProcessingStatus.PROCESSING,
                ProcessingStatus.CANCELLED,
            },
            ProcessingStatus.PROCESSING: {
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED,
                ProcessingStatus.CANCELLED,
            },
            ProcessingStatus.COMPLETED: {
                ProcessingStatus.PROCESSING,  # Allow reprocessing
            },
            ProcessingStatus.FAILED: {
                ProcessingStatus.PROCESSING,  # Allow retry
                ProcessingStatus.CANCELLED,
            },
            ProcessingStatus.CANCELLED: {
                ProcessingStatus.PENDING,  # Allow restart
            },
        }

        return new_status in allowed_transitions.get(self, set())

    def is_terminal(self) -> bool:
        """Check if this is a terminal status.

        Returns:
            True if status represents a final state
        """
        return self in {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        }

    def is_active(self) -> bool:
        """Check if this status represents active processing.

        Returns:
            True if status represents ongoing work
        """
        return self == ProcessingStatus.PROCESSING

    def is_pending(self) -> bool:
        """Check if this status represents pending work.

        Returns:
            True if status represents queued work
        """
        return self == ProcessingStatus.PENDING

    def is_error_state(self) -> bool:
        """Check if this status represents an error state.

        Returns:
            True if status represents failure or cancellation
        """
        return self in {
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }

    def is_successful(self) -> bool:
        """Check if this status represents successful completion.

        Returns:
            True if status represents successful completion
        """
        return self == ProcessingStatus.COMPLETED

    def can_be_retried(self) -> bool:
        """Check if processing can be retried from this status.

        Returns:
            True if status allows retry
        """
        return self in {
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }

    def can_be_cancelled(self) -> bool:
        """Check if processing can be cancelled from this status.

        Returns:
            True if status allows cancellation
        """
        return self in {
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.FAILED,
        }

    @classmethod
    def get_all_statuses(cls) -> set["ProcessingStatus"]:
        """Get all possible processing statuses.

        Returns:
            Set of all ProcessingStatus values
        """
        return set(cls)

    @classmethod
    def get_active_statuses(cls) -> set["ProcessingStatus"]:
        """Get statuses that represent active/ongoing work.

        Returns:
            Set of active ProcessingStatus values
        """
        return {
            cls.PENDING,
            cls.PROCESSING,
        }

    @classmethod
    def get_terminal_statuses(cls) -> set["ProcessingStatus"]:
        """Get statuses that represent final states.

        Returns:
            Set of terminal ProcessingStatus values
        """
        return {
            cls.COMPLETED,
            cls.CANCELLED,
        }

    @classmethod
    def get_error_statuses(cls) -> set["ProcessingStatus"]:
        """Get statuses that represent error states.

        Returns:
            Set of error ProcessingStatus values
        """
        return {
            cls.FAILED,
            cls.CANCELLED,
        }
