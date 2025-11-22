"""Learning progress and quiz attempt API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from src.application.interfaces.authentication import AuthenticationResult
from src.application.services.learning_service import LearningService
from src.presentation.api.dependencies import (
    get_learning_service,
)
from src.presentation.api.security import get_current_user
from src.shared.models.learning import (
    LearningProgress,
    LearningProgressUpsert,
    QuizAttempt,
    QuizAttemptCreate,
)
from src.shared.types import AnalysisId, LearningProgressId, QuizAttemptId, UserId

router = APIRouter(prefix="/learning", tags=["learning"])


def _now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


def _require_user_id(auth_result: AuthenticationResult) -> UserId:
    """Extract a user identifier from an authentication result."""

    if auth_result.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "auth.user.missing",
                "message": "Authenticated request is missing a user identifier",
            },
        )

    if isinstance(auth_result.user_id, UUID):
        return UserId(auth_result.user_id)

    return UserId(UUID(str(auth_result.user_id)))


class LearningProgressResponse(BaseModel):
    """API response envelope for a learning progress record."""

    schema_version: int = Field(..., ge=1)
    progress_id: str = Field(..., description="Learning progress identifier")
    user_id: str = Field(..., description="Owner of the learning progress entry")
    module_key: str = Field(..., description="Stable module key")
    progress_percent: int = Field(..., ge=0, le=100)
    last_interaction_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    is_unlocked: bool = Field(default=False)
    unlocked_at: datetime | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def from_model(cls, progress: LearningProgress) -> LearningProgressResponse:
        return cls(
            schema_version=progress.schema_version,
            progress_id=str(progress.progress_id),
            user_id=str(progress.user_id),
            module_key=progress.module_key,
            progress_percent=progress.progress_percent,
            last_interaction_at=progress.last_interaction_at,
            completed_at=progress.completed_at,
            is_unlocked=progress.is_unlocked,
            unlocked_at=progress.unlocked_at,
            metadata=progress.metadata or {},
            created_at=progress.created_at,
            updated_at=progress.updated_at,
        )


class LearningProgressUpdateRequest(BaseModel):
    """Request payload for creating or updating learning progress."""

    schema_version: int = Field(default=1, ge=1)
    progress_id: str | None = Field(
        default=None,
        description="Existing progress identifier to update",
    )
    progress_percent: int = Field(..., ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_interaction_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class WalkthroughCompletionRequest(BaseModel):
    """Request payload for recording a walkthrough completion event."""

    analysis_id: UUID = Field(
        description="Analysis identifier that emitted the walkthrough event",
    )
    section_key: str | None = Field(
        default=None,
        description="Canonical section key for the walkthrough segment",
    )
    progress_percent: int = Field(..., ge=0, le=100)
    completed_at: datetime | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class QuizAttemptResponse(BaseModel):
    """API response envelope for a quiz attempt."""

    schema_version: int = Field(..., ge=1)
    attempt_id: str = Field(..., description="Quiz attempt identifier")
    user_id: str = Field(..., description="Owner of the quiz attempt")
    quiz_id: str = Field(..., description="Quiz identifier")
    question_count: int = Field(..., ge=0)
    correct_count: int = Field(..., ge=0)
    score_percent: float = Field(..., ge=0.0, le=100.0)
    passed: bool = Field(...)
    is_human_reviewed: bool = Field(default=False)
    attempted_at: datetime = Field(...)
    responses: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def from_model(cls, attempt: QuizAttempt) -> QuizAttemptResponse:
        return cls(
            schema_version=attempt.schema_version,
            attempt_id=str(attempt.attempt_id),
            user_id=str(attempt.user_id),
            quiz_id=attempt.quiz_id,
            question_count=attempt.question_count,
            correct_count=attempt.correct_count,
            score_percent=attempt.score_percent,
            passed=attempt.passed,
            is_human_reviewed=attempt.is_human_reviewed,
            attempted_at=attempt.attempted_at,
            responses=attempt.responses or {},
            metadata=attempt.metadata or {},
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
        )


class QuizAttemptCreateRequest(BaseModel):
    """Request payload for recording a quiz attempt."""

    schema_version: int = Field(default=1, ge=1)
    attempt_id: str | None = Field(
        default=None,
        description="Optional identifier for the attempt",
    )
    quiz_id: str = Field(..., description="Quiz identifier")
    question_count: int = Field(..., ge=0)
    correct_count: int = Field(..., ge=0)
    score_percent: float = Field(..., ge=0.0, le=100.0)
    passed: bool = Field(default=False)
    is_human_reviewed: bool = Field(default=False)
    attempted_at: datetime | None = Field(default=None)
    responses: dict[str, Any] | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def _convert_attempt_id(cls, attempt_id: str | None) -> QuizAttemptId | None:
        if attempt_id is None:
            return None
        return QuizAttemptId(UUID(attempt_id))


@router.get(
    "/progress",
    response_model=list[LearningProgressResponse],
    summary="List learning progress entries for the authenticated user",
)
async def list_learning_progress(
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> list[LearningProgressResponse]:
    """Return all learning progress entries for the current user."""

    user_id = _require_user_id(auth_result)
    progress_entries = await learning_service.list_user_progress(user_id)
    return [LearningProgressResponse.from_model(entry) for entry in progress_entries]


@router.put(
    "/progress/{module_key}",
    response_model=LearningProgressResponse,
    summary="Create or update learning progress for a module",
)
async def upsert_learning_progress(
    module_key: str,
    payload: LearningProgressUpdateRequest,
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningProgressResponse:
    """Create or update progress for the specified learning module."""

    user_id = _require_user_id(auth_result)

    progress_id: LearningProgressId | None = None
    if payload.progress_id:
        progress_id = LearningProgressId(UUID(payload.progress_id))

    interaction_at = payload.last_interaction_at or _now()
    completed_at = payload.completed_at
    if completed_at is None and payload.progress_percent >= 100:
        completed_at = interaction_at

    upsert_payload = LearningProgressUpsert(
        schema_version=payload.schema_version,
        progress_id=progress_id,
        user_id=user_id,
        module_key=module_key,
        progress_percent=payload.progress_percent,
        metadata=payload.metadata,
        last_interaction_at=interaction_at,
        completed_at=completed_at,
    )

    result = await learning_service.upsert_progress(upsert_payload)
    return LearningProgressResponse.from_model(result)


@router.post(
    "/progress/{module_key}/walkthrough-events",
    response_model=LearningProgressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a walkthrough completion event for the authenticated user",
)
async def record_walkthrough_event(
    module_key: str,
    payload: WalkthroughCompletionRequest,
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningProgressResponse:
    """Record a walkthrough completion milestone and return updated progress."""

    user_id = _require_user_id(auth_result)
    event_time = payload.completed_at or _now()
    progress = await learning_service.record_walkthrough_event(
        user_id=user_id,
        module_key=module_key,
        analysis_id=AnalysisId(payload.analysis_id),
        section_key=payload.section_key,
        progress_percent=payload.progress_percent,
        completed_at=event_time,
    )
    return LearningProgressResponse.from_model(progress)


@router.get(
    "/quiz-attempts",
    response_model=list[QuizAttemptResponse],
    summary="List recent quiz attempts for the authenticated user",
)
async def list_quiz_attempts(
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
    limit: int = Query(20, ge=1, le=100),
) -> list[QuizAttemptResponse]:
    """Return recent quiz attempts for the current user."""

    user_id = _require_user_id(auth_result)
    attempts = await learning_service.list_recent_quiz_attempts(user_id, limit=limit)
    return [QuizAttemptResponse.from_model(attempt) for attempt in attempts]


@router.post(
    "/quiz-attempts",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a quiz attempt for the authenticated user",
)
async def record_quiz_attempt(
    payload: QuizAttemptCreateRequest,
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> QuizAttemptResponse:
    """Persist a quiz attempt tied to the current user."""

    user_id = _require_user_id(auth_result)

    derived_passed = payload.score_percent >= 80.0

    attempt_payload = QuizAttemptCreate(
        schema_version=payload.schema_version,
        attempt_id=QuizAttemptCreateRequest._convert_attempt_id(payload.attempt_id),
        user_id=user_id,
        quiz_id=payload.quiz_id,
        question_count=payload.question_count,
        correct_count=payload.correct_count,
        score_percent=payload.score_percent,
        passed=derived_passed,
        is_human_reviewed=payload.is_human_reviewed,
        attempted_at=payload.attempted_at or _now(),
        responses=payload.responses,
        metadata=payload.metadata,
    )

    attempt = await learning_service.record_quiz_attempt(attempt_payload)
    return QuizAttemptResponse.from_model(attempt)


@router.get(
    "/quiz-attempts/{quiz_id}/best",
    response_model=QuizAttemptResponse | None,
    summary="Return the best quiz attempt for the specified quiz",
)
async def get_best_quiz_attempt(
    quiz_id: str,
    auth_result: AuthenticationResult = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> QuizAttemptResponse | None:
    """Return the best scoring attempt for a quiz, if any."""

    user_id = _require_user_id(auth_result)
    attempt = await learning_service.get_best_quiz_attempt(user_id, quiz_id)
    if attempt is None:
        return None
    return QuizAttemptResponse.from_model(attempt)
