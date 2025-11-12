"""Service layer for learning progress and quiz attempts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from src.application.interfaces.repositories import (
    ILearningProgressRepository,
    IQuizAttemptRepository,
    IRepositoryFactory,
    LearningProgressData,
    QuizAttemptData,
)
from src.shared.models.learning import (
    LearningProgress,
    LearningProgressUpsert,
    QuizAttempt,
    QuizAttemptCreate,
)
from src.shared.types import (
    AnalysisId,
    LearningProgressId,
    QuizAttemptId,
    UserId,
)


class LearningService:
    """Coordinate learning progress and quiz attempt persistence."""

    def __init__(
        self,
        repository_factory: IRepositoryFactory,
    ) -> None:
        self._repository_factory = repository_factory

    async def close(self, *, success: bool = True) -> None:
        """Flush and close repository resources attached to this service."""

        close_callable = getattr(self._repository_factory, "close", None)
        if close_callable is None:
            return

        await close_callable(success=success)

    @staticmethod
    def _to_progress_model(
        data: LearningProgressData,
        *,
        is_unlocked: bool | None = None,
        unlocked_at: datetime | None = None,
    ) -> LearningProgress:
        return LearningProgress(
            progress_id=data.id,
            user_id=data.user_id,
            module_key=data.module_key,
            progress_percent=data.progress_percent,
            last_interaction_at=data.last_interaction_at,
            completed_at=data.completed_at,
            is_unlocked=is_unlocked if is_unlocked is not None else data.is_unlocked,
            unlocked_at=unlocked_at if unlocked_at is not None else data.unlocked_at,
            metadata=data.metadata,
            schema_version=data.schema_version,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    @staticmethod
    def _to_quiz_model(data: QuizAttemptData) -> QuizAttempt:
        return QuizAttempt(
            attempt_id=data.id,
            user_id=data.user_id,
            quiz_id=data.quiz_id,
            question_count=data.question_count,
            correct_count=data.correct_count,
            score_percent=data.score_percent,
            passed=data.passed,
            is_human_reviewed=data.is_human_reviewed,
            attempted_at=data.attempted_at,
            metadata=data.metadata,
            schema_version=data.schema_version,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    async def _refresh_module_progress(
        self,
        progress: LearningProgressData,
        *,
        quiz_id: str | None = None,
        persist: bool,
        quiz_repository: IQuizAttemptRepository | None = None,
        learning_repository: ILearningProgressRepository | None = None,
    ) -> LearningProgress:
        if quiz_repository is None:
            quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        if learning_repository is None:
            learning_repository = (
                await self._repository_factory.get_learning_progress_repository()
            )

        effective_quiz_id = quiz_id or progress.module_key
        best_attempt = await quiz_repository.get_best_attempt(
            progress.user_id, effective_quiz_id
        )

        unlocked_at = progress.unlocked_at
        is_unlocked = progress.is_unlocked

        passing_attempt = False

        if best_attempt is not None:
            passing_attempt = bool(
                best_attempt.passed or best_attempt.score_percent >= 80.0
            )

        walkthrough_complete = (
            progress.progress_percent >= 100 or progress.completed_at is not None
        )
        quiz_passed = (
            best_attempt is not None
            and passing_attempt
        )

        if walkthrough_complete and quiz_passed:
            is_unlocked = True
            if unlocked_at is None and best_attempt is not None:
                unlocked_at = best_attempt.attempted_at

        updates: dict[str, Any] = {}
        if progress.is_unlocked != is_unlocked:
            updates["is_unlocked"] = is_unlocked
        if progress.unlocked_at != unlocked_at:
            updates["unlocked_at"] = unlocked_at

        updated_progress = progress
        if updates:
            updated_progress = progress.model_copy(update=updates)
            if persist:
                updated_progress = await learning_repository.upsert(updated_progress)

        return self._to_progress_model(
            updated_progress,
            is_unlocked=is_unlocked,
            unlocked_at=unlocked_at,
        )

    async def upsert_progress(
        self,
        payload: LearningProgressUpsert,
    ) -> LearningProgress:
        """Create or update a learning progress entry."""

        progress_id = payload.progress_id or LearningProgressId(uuid4())
        data = LearningProgressData(
            id=progress_id,
            user_id=payload.user_id,
            module_key=payload.module_key,
            progress_percent=payload.progress_percent,
            last_interaction_at=payload.last_interaction_at,
            completed_at=payload.completed_at,
            metadata=payload.metadata,
            schema_version=payload.schema_version,
            is_unlocked=payload.is_unlocked or False,
            unlocked_at=payload.unlocked_at,
        )

        learning_repository = (
            await self._repository_factory.get_learning_progress_repository()
        )

        saved = await learning_repository.upsert(data)
        quiz_hint = None
        if payload.metadata:
            quiz_hint = payload.metadata.get("quiz_id")
        return await self._refresh_module_progress(
            saved,
            quiz_id=quiz_hint,
            persist=True,
            learning_repository=learning_repository,
        )

    async def list_user_progress(self, user_id: UserId) -> list[LearningProgress]:
        """Return all learning progress entries for a user."""

        learning_repository = (
            await self._repository_factory.get_learning_progress_repository()
        )
        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        records = await learning_repository.list_for_user(user_id)
        progress_models: list[LearningProgress] = []
        for record in records:
            progress = await self._refresh_module_progress(
                record,
                persist=False,
                quiz_repository=quiz_repository,
                learning_repository=learning_repository,
            )
            progress_models.append(progress)
        return progress_models

    async def record_walkthrough_event(
        self,
        user_id: UserId,
        module_key: str,
        *,
        analysis_id: AnalysisId,
        section_key: str | None,
        progress_percent: int,
        completed_at: datetime,
    ) -> LearningProgress:
        """Record a walkthrough milestone for the learner."""

        learning_repository = (
            await self._repository_factory.get_learning_progress_repository()
        )
        progress = await learning_repository.get_for_user_module(user_id, module_key)
        if progress is None:
            progress = LearningProgressData(
                id=LearningProgressId(uuid4()),
                user_id=user_id,
                module_key=module_key,
                progress_percent=0,
                last_interaction_at=completed_at,
                completed_at=None,
                metadata={
                    "analysis_walkthroughs": {},
                    "sections": {},
                    "section_progress_version": 1,
                },
                schema_version=1,
                is_unlocked=False,
                unlocked_at=None,
        )

        metadata = dict(progress.metadata or {})
        analysis_runs_raw = metadata.get("analysis_walkthroughs", {})
        analysis_runs: dict[str, dict[str, Any]] = {}
        if isinstance(analysis_runs_raw, dict):
            for run_key, run_data in analysis_runs_raw.items():
                if isinstance(run_key, str) and isinstance(run_data, dict):
                    analysis_runs[run_key] = dict(run_data)

        sections_raw = metadata.get("sections", {})
        sections: dict[str, dict[str, Any]] = {}
        if isinstance(sections_raw, dict):
            for section_name, section_data in sections_raw.items():
                if isinstance(section_name, str) and isinstance(section_data, dict):
                    sections[section_name] = dict(section_data)

        run_key = str(analysis_id)
        run_data = analysis_runs.get(run_key, {})
        if not isinstance(run_data, dict):
            run_data = {}

        existing_sections = run_data.get("completed_sections", [])
        completed_sections: set[str] = set()
        if isinstance(existing_sections, list):
            for item in existing_sections:
                if isinstance(item, str):
                    completed_sections.add(item)

        if section_key:
            completed_sections.add(section_key)

        if completed_sections:
            run_data["completed_sections"] = sorted(completed_sections)
        else:
            run_data.pop("completed_sections", None)

        run_data["progress_percent"] = progress_percent
        run_data["last_event_at"] = completed_at.isoformat()
        if progress_percent >= 100:
            run_data["completed_at"] = completed_at.isoformat()

        analysis_runs[run_key] = run_data

        if section_key:
            section_entry = sections.get(section_key, {})
            if not isinstance(section_entry, dict):
                section_entry = {}

            runs_raw = section_entry.get("analysis_runs", {})
            section_runs: dict[str, dict[str, Any]] = {}
            if isinstance(runs_raw, dict):
                for key, value in runs_raw.items():
                    if isinstance(key, str) and isinstance(value, dict):
                        section_runs[key] = dict(value)

            section_run = section_runs.get(run_key, {})
            if not isinstance(section_run, dict):
                section_run = {}

            section_run["progress_percent"] = progress_percent
            section_run["last_event_at"] = completed_at.isoformat()
            if progress_percent >= 100:
                section_run["completed_at"] = completed_at.isoformat()
            else:
                section_run.pop("completed_at", None)

            section_runs[run_key] = section_run

            section_completed_ids = sorted(
                key
                for key, value in section_runs.items()
                if isinstance(value, dict)
                and isinstance(value.get("progress_percent"), int | float)
                and float(value["progress_percent"]) >= 100
            )
            section_progress_percent = max(
                (
                    int(value.get("progress_percent", 0))
                    if isinstance(value, dict)
                    and isinstance(value.get("progress_percent"), int | float)
                    else 0
                )
                for value in section_runs.values()
            )
            section_entry.update(
                {
                    "analysis_runs": section_runs,
                    "latest_analysis_id": run_key,
                    "latest_progress_percent": progress_percent,
                    "last_event_at": completed_at.isoformat(),
                    "progress_percent": section_progress_percent,
                    "completed_analysis_ids": section_completed_ids,
                }
            )
            if section_progress_percent >= 100:
                section_entry["completed_at"] = completed_at.isoformat()
            else:
                section_entry.pop("completed_at", None)

            sections[section_key] = section_entry

        metadata["analysis_walkthroughs"] = analysis_runs
        metadata["last_walkthrough_event_at"] = completed_at.isoformat()
        metadata["last_walkthrough_analysis_id"] = run_key
        metadata["sections"] = sections
        metadata["section_progress_version"] = 1
        if section_key:
            metadata["last_walkthrough_section_key"] = section_key
        metadata.pop("completed_sections", None)

        updated_progress_percent = max(progress.progress_percent, progress_percent)
        completion_timestamp = progress.completed_at
        if progress_percent >= 100:
            completion_timestamp = completed_at

        updated_progress = progress.model_copy(
            update={
                "progress_percent": updated_progress_percent,
                "last_interaction_at": completed_at,
                "completed_at": completion_timestamp,
                "metadata": metadata,
            }
        )

        saved = await learning_repository.upsert(updated_progress)
        return await self._refresh_module_progress(
            saved,
            persist=True,
            learning_repository=learning_repository,
        )

    async def delete_progress(self, progress_id: LearningProgressId) -> bool:
        """Delete a learning progress entry by identifier."""

        learning_repository = (
            await self._repository_factory.get_learning_progress_repository()
        )
        return await learning_repository.delete(progress_id)

    async def record_quiz_attempt(
        self,
        payload: QuizAttemptCreate,
    ) -> QuizAttempt:
        """Persist a quiz attempt for a learner."""

        attempt_id = payload.attempt_id or QuizAttemptId(uuid4())
        passed = bool(payload.passed or payload.score_percent >= 80.0)
        data = QuizAttemptData(
            id=attempt_id,
            user_id=payload.user_id,
            quiz_id=payload.quiz_id,
            question_count=payload.question_count,
            correct_count=payload.correct_count,
            score_percent=payload.score_percent,
            passed=passed,
            is_human_reviewed=payload.is_human_reviewed,
            responses=payload.responses or {},
            metadata=payload.metadata,
            attempted_at=payload.attempted_at,
            schema_version=payload.schema_version,
        )

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        saved = await quiz_repository.record_attempt(data)

        module_key = None
        if payload.metadata:
            module_key = payload.metadata.get("module_key")
        module_key = module_key or payload.quiz_id

        learning_repository = (
            await self._repository_factory.get_learning_progress_repository()
        )
        progress_data = await learning_repository.get_for_user_module(
            payload.user_id, module_key
        )
        if progress_data is not None:
            await self._refresh_module_progress(
                progress_data,
                quiz_id=payload.quiz_id,
                persist=True,
                quiz_repository=quiz_repository,
                learning_repository=learning_repository,
            )

        return self._to_quiz_model(saved)

    async def list_recent_quiz_attempts(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[QuizAttempt]:
        """Return recent quiz attempts for a user."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        attempts = await quiz_repository.list_for_user(user_id, limit=limit)
        return [self._to_quiz_model(attempt) for attempt in attempts]

    async def get_best_quiz_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttempt | None:
        """Return the best scoring attempt for the given quiz."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        attempt = await quiz_repository.get_best_attempt(user_id, quiz_id)
        if attempt is None:
            return None
        return self._to_quiz_model(attempt)

    async def delete_quiz_attempt(self, attempt_id: QuizAttemptId) -> bool:
        """Delete a quiz attempt by identifier."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        return await quiz_repository.delete(attempt_id)
