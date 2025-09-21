"""Legacy processing status value object.

This adapter keeps the original `ProcessingStatus` API alive for components that
still import it directly (domain entities, response models, background
services). Internally we lean on the newer shared enums, but we present the same
interface so Stage 2 dependency-injection work can complete without a broad
refactor.

TODO(feature/di-provider-abstraction-refactor): remove this shim once callers
have migrated to `src.shared.enums.status`.
"""

from __future__ import annotations

from enum import Enum

from src.shared.enums.status import AnalysisStatus, TaskStatus


class ProcessingStatus(str, Enum):
    """Mirror of the historical ProcessingStatus enum with helper methods."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # --- Mapping helpers -----------------------------------------------------

    @classmethod
    def from_task_status(cls, status: TaskStatus) -> ProcessingStatus:
        mapping = {
            TaskStatus.PENDING: cls.PENDING,
            TaskStatus.QUEUED: cls.PENDING,
            TaskStatus.IN_PROGRESS: cls.PROCESSING,
            TaskStatus.RETRY: cls.PROCESSING,
            TaskStatus.COMPLETED: cls.COMPLETED,
            TaskStatus.FAILED: cls.FAILED,
            TaskStatus.CANCELLED: cls.CANCELLED,
        }
        return mapping.get(status, cls.FAILED)

    @classmethod
    def from_analysis_status(cls, status: AnalysisStatus) -> ProcessingStatus:
        mapping = {
            AnalysisStatus.INITIATED: cls.PENDING,
            AnalysisStatus.FETCHING: cls.PROCESSING,
            AnalysisStatus.PARSING: cls.PROCESSING,
            AnalysisStatus.ANALYZING: cls.PROCESSING,
            AnalysisStatus.STORING: cls.PROCESSING,
            AnalysisStatus.COMPLETED: cls.COMPLETED,
            AnalysisStatus.ERROR: cls.FAILED,
            AnalysisStatus.EXPIRED: cls.CANCELLED,
        }
        return mapping.get(status, cls.FAILED)

    # --- Instance helpers ----------------------------------------------------

    def is_pending(self) -> bool:
        return self is self.PENDING

    def is_active(self) -> bool:
        return self is self.PROCESSING

    def is_successful(self) -> bool:
        return self is self.COMPLETED

    def is_error_state(self) -> bool:
        return self in {self.FAILED, self.CANCELLED}

    def is_terminal(self) -> bool:
        return self in {self.COMPLETED, self.CANCELLED}

    def can_be_retried(self) -> bool:
        return self in {self.FAILED, self.CANCELLED}

    def can_be_cancelled(self) -> bool:
        return self in {self.PENDING, self.PROCESSING, self.FAILED}

    def can_transition_to(self, target: ProcessingStatus) -> bool:
        target = (
            target if isinstance(target, ProcessingStatus) else ProcessingStatus(target)
        )
        transitions = {
            self.PENDING: {self.PROCESSING, self.CANCELLED},
            self.PROCESSING: {self.COMPLETED, self.FAILED, self.CANCELLED},
            self.COMPLETED: {self.PROCESSING},
            self.FAILED: {self.PROCESSING, self.CANCELLED},
            self.CANCELLED: {self.PENDING},
        }
        return target in transitions[self]

    # --- Class-level collections ---------------------------------------------

    @classmethod
    def get_all_statuses(cls) -> set[ProcessingStatus]:
        return set(cls)

    @classmethod
    def get_active_statuses(cls) -> set[ProcessingStatus]:
        return {cls.PENDING, cls.PROCESSING}

    @classmethod
    def get_terminal_statuses(cls) -> set[ProcessingStatus]:
        return {cls.COMPLETED, cls.CANCELLED}

    @classmethod
    def get_error_statuses(cls) -> set[ProcessingStatus]:
        return {cls.FAILED, cls.CANCELLED}
