"""Shared Pydantic models for learning progress and quiz data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.shared.enums.learning import (
    LearningReviewStatus,
    LearningWalkthroughArtifactType,
)
from src.shared.types import (
    LearningProgressId,
    LearningWalkthroughBindingId,
    QuizAttemptId,
    UserId,
)


class LearningProgress(BaseModel):
    """Serializable learning progress representation."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning progress payloads",
    )
    progress_id: LearningProgressId
    user_id: UserId
    module_key: str = Field(description="Stable identifier for the learning module")
    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Completion percentage for the module",
    )
    last_interaction_at: datetime | None = Field(
        default=None,
        description="Timestamp for the most recent learner interaction",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the module was completed",
    )
    pending_review_count: int = Field(
        default=0,
        ge=0,
        description="Number of lessons pending review for spaced repetition",
    )
    last_reviewed_at: datetime | None = Field(
        default=None,
        description="When the learner last reviewed the module content",
    )
    is_unlocked: bool = Field(
        default=False,
        description="Whether the module has been unlocked for the learner",
    )
    unlocked_at: datetime | None = Field(
        default=None,
        description="Timestamp when the module was unlocked",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental metadata tied to the learner's progress",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"arbitrary_types_allowed": True}


class LearningProgressUpsert(BaseModel):
    """Input payload for creating or updating learning progress."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning progress write payloads",
    )
    progress_id: LearningProgressId | None = Field(
        default=None,
        description="Existing progress identifier to update (optional)",
    )
    user_id: UserId
    module_key: str
    progress_percent: int = Field(
        ge=0,
        le=100,
        description="Updated completion percentage",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_interaction_at: datetime | None = None
    completed_at: datetime | None = None
    pending_review_count: int | None = Field(default=None, ge=0)
    last_reviewed_at: datetime | None = None
    is_unlocked: bool | None = None
    unlocked_at: datetime | None = None


class QuizAttempt(BaseModel):
    """Serializable quiz attempt representation."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for quiz attempt payloads",
    )
    attempt_id: QuizAttemptId
    user_id: UserId
    quiz_id: str = Field(description="Identifier for the quiz or assessment")
    question_count: int = Field(
        ge=0,
        description="Total number of questions for the attempt",
    )
    correct_count: int = Field(
        ge=0,
        description="Number of correctly answered questions",
    )
    score_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="Score represented as a percentage",
    )
    passed: bool = Field(description="Whether the attempt met the passing criteria")
    is_human_reviewed: bool = Field(
        default=False,
        description="Whether the attempt has been human-reviewed and approved",
    )
    attempted_at: datetime = Field(description="Timestamp when the attempt occurred")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"arbitrary_types_allowed": True}


class QuizAttemptCreate(BaseModel):
    """Input payload for recording a quiz attempt."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for quiz attempt write payloads",
    )
    attempt_id: QuizAttemptId | None = Field(
        default=None,
        description="Optional identifier to use for the stored attempt",
    )
    user_id: UserId
    quiz_id: str
    question_count: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    score_percent: float = Field(ge=0.0, le=100.0)
    passed: bool = False
    is_human_reviewed: bool = False
    attempted_at: datetime
    responses: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningWalkthroughBinding(BaseModel):
    """Mapping between walkthrough artifacts and micro-lessons with review status."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning walkthrough binding payloads",
    )
    binding_id: LearningWalkthroughBindingId = Field(
        description="Identifier for the walkthrough binding record"
    )
    walkthrough_section_id: str = Field(
        description="Identifier for the section walkthrough that emitted the artifact"
    )
    artifact_id: str = Field(
        description="Identifier for the highlight or comprehension check artifact"
    )
    artifact_type: LearningWalkthroughArtifactType = Field(
        description="Type of artifact associated with the binding"
    )
    lesson_id: str = Field(description="Identifier for the linked micro-lesson")
    learning_module_key: str = Field(
        description="Module key aligned with the walkthrough artifact"
    )
    module_stage: str = Field(
        description="Module stage (e.g., orientation, fundamentals, mastery)"
    )
    lesson_title: str | None = Field(
        default=None,
        description="Optional curated title for the linked lesson",
    )
    status: LearningReviewStatus = Field(
        default=LearningReviewStatus.PENDING,
        description="Review status for the walkthrough artifact binding",
    )
    last_reviewed_at: datetime | None = Field(
        default=None,
        description="Timestamp for the most recent review decision",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator(
        "walkthrough_section_id",
        "artifact_id",
        "lesson_id",
        "learning_module_key",
        "module_stage",
        mode="before",
    )
    @classmethod
    def _ensure_non_empty(cls, value: Any) -> str:
        """Ensure string fields are populated with non-empty values."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        return value.strip()

    @field_validator("lesson_title", mode="before")
    @classmethod
    def _normalise_optional_title(cls, value: Any) -> str | None:
        """Normalise optional lesson titles to trimmed strings."""

        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("lesson_title must be a string when provided")
        stripped = value.strip()
        return stripped or None


class LearningWalkthroughBindingUpsert(BaseModel):
    """Payload for creating or updating walkthrough bindings."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for learning walkthrough binding write payloads",
    )
    binding_id: LearningWalkthroughBindingId | None = Field(
        default=None,
        description="Optional existing binding identifier to update",
    )
    walkthrough_section_id: str
    artifact_id: str
    artifact_type: LearningWalkthroughArtifactType
    lesson_id: str
    learning_module_key: str
    module_stage: str
    lesson_title: str | None = None
    status: LearningReviewStatus = LearningReviewStatus.PENDING
    last_reviewed_at: datetime | None = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator(
        "walkthrough_section_id",
        "artifact_id",
        "lesson_id",
        "learning_module_key",
        "module_stage",
        mode="before",
    )
    @classmethod
    def _ensure_non_empty(cls, value: Any) -> str:
        """Normalise string fields for write payloads."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("value must be a non-empty string")
        return value.strip()

    @field_validator("lesson_title", mode="before")
    @classmethod
    def _normalise_optional_title(cls, value: Any) -> str | None:
        """Trim optional lesson titles."""

        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("lesson_title must be a string when provided")
        stripped = value.strip()
        return stripped or None
