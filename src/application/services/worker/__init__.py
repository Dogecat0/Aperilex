"""
Worker service collaborator package.

Phase 1 introduces incremental collaborators that will eventually replace the
monolithic `WorkerService` helpers. Only the task builder is implemented so
far; additional services will be filled in subsequent commits.
"""

from .analysis_task_builder import AnalysisTaskBuilder

__all__ = ["AnalysisTaskBuilder"]
