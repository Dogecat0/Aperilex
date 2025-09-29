"""Shared Pydantic models for learning progress and quiz data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.shared.types import (
    LearningProgressId,
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
    attempted_at: datetime
    responses: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
