"""
Models module for Pydantic models and metadata types.
"""

from .analysis import (
    STRUCTURED_ANALYSIS_SCHEMA_VERSION,
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    ComprehensionCheck,
    HighlightCallout,
    LessonReference,
    ModelTier,
    SectionCostBreakdown,
    SectionWalkthrough,
    StructuredAnalysisData,
    TokenUsage,
    WalkthroughGuidance,
)
from .base import MetadataDict, MetadataValue
from .learning import (
    LearningProgress,
    LearningProgressUpsert,
    QuizAttempt,
    QuizAttemptCreate,
)
from .llm import LLMModelInfo
from .queue import QueueMessage, QueueMessageBody, TaskMessage, TaskQueueMessage
from .records import AnalysisRecord, CompanyRecord, FilingRecord, TaskRecord
from .storage import StorageMetadataFields
from .task import TaskMetadata
from .task_data import TaskData

__all__ = [
    # Base types
    "MetadataValue",
    "MetadataDict",
    # Task models
    "TaskMetadata",
    "TaskMessage",
    # Storage models
    "StorageMetadataFields",
    # Queue models
    "QueueMessageBody",
    "QueueMessage",
    "TaskQueueMessage",
    "TaskMessage",
    # Database records
    "TaskRecord",
    "AnalysisRecord",
    "FilingRecord",
    "CompanyRecord",
    # LLM models
    "LLMModelInfo",
    # Analysis models
    "AnalysisRequest",
    "AnalysisResult",
    "AnalysisType",
    "ComprehensionCheck",
    "HighlightCallout",
    "LessonReference",
    "ModelTier",
    "SectionWalkthrough",
    "StructuredAnalysisData",
    "WalkthroughGuidance",
    "STRUCTURED_ANALYSIS_SCHEMA_VERSION",
    "TokenUsage",
    "SectionCostBreakdown",
    # Task data models
    "TaskData",
    # Learning models
    "LearningProgress",
    "LearningProgressUpsert",
    "QuizAttempt",
    "QuizAttemptCreate",
]
