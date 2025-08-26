"""Analysis stage value object for tracking analysis progress."""

from enum import Enum


class AnalysisStage(str, Enum):
    """
    Represents the current stage of an analysis process.

    This enum provides a structured way to track analysis progress,
    replacing the need for frontend to parse free-text messages.
    """

    IDLE = "idle"
    INITIATING = "initiating"
    LOADING_FILING = "loading_filing"
    ANALYZING_CONTENT = "analyzing_content"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"
    BACKGROUND = "background"
