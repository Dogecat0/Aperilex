"""API tests for learning progress and quiz attempt endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from src.application.interfaces.authentication import AuthenticationResult
from src.presentation.api.dependencies import (
    get_learning_service,
)
from src.presentation.api.routers import learning
from src.presentation.api.security import get_current_user
from src.shared.models.learning import LearningProgress, QuizAttempt
from src.shared.types import (
    LearningProgressId,
    QuizAttemptId,
    UserId,
)


class FakeLearningService:
    """In-memory stub of the learning service for API tests."""

    def __init__(self, user_id: UserId) -> None:
        self.user_id = user_id
        self.progress_records: list[LearningProgress] = []
        self.quiz_attempts: list[QuizAttempt] = []
        self.list_calls = 0
        self.upsert_calls = 0
        self.recent_attempt_calls = 0
        self.record_attempt_calls = 0
        self.best_attempt_calls = 0
        self.last_upsert_payload = None
        self.last_attempt_payload = None
        self.walkthrough_event_calls = 0
        self.last_walkthrough_payload = None

    async def list_user_progress(self, user_id: UserId) -> list[LearningProgress]:
        assert user_id == self.user_id
        self.list_calls += 1
        return list(self.progress_records)

    async def upsert_progress(self, payload):  # type: ignore[no-untyped-def]
        self.upsert_calls += 1
        self.last_upsert_payload = payload

        existing = next(
            (record for record in self.progress_records if record.module_key == payload.module_key),
            None,
        )

        progress_id = (
            existing.progress_id if existing else LearningProgressId(uuid4())
        )
        base_created_at = existing.created_at if existing else payload.last_interaction_at

        updated = LearningProgress(
            schema_version=payload.schema_version,
            progress_id=progress_id,
            user_id=payload.user_id,
            module_key=payload.module_key,
            progress_percent=payload.progress_percent,
            last_interaction_at=payload.last_interaction_at,
            completed_at=payload.completed_at,
            metadata=payload.metadata or {},
            created_at=base_created_at,
            updated_at=payload.last_interaction_at,
        )

        if existing is None:
            self.progress_records.append(updated)
        else:
            index = self.progress_records.index(existing)
            self.progress_records[index] = updated

        return updated

    async def list_recent_quiz_attempts(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[QuizAttempt]:
        assert user_id == self.user_id
        self.recent_attempt_calls += 1
        return list(self.quiz_attempts[:limit])

    async def record_quiz_attempt(self, payload):  # type: ignore[no-untyped-def]
        self.record_attempt_calls += 1
        self.last_attempt_payload = payload

        attempt_id = payload.attempt_id or QuizAttemptId(uuid4())
        derived_passed = payload.score_percent >= 80
        attempt = QuizAttempt(
            schema_version=payload.schema_version,
            attempt_id=attempt_id,
            user_id=payload.user_id,
            quiz_id=payload.quiz_id,
            question_count=payload.question_count,
            correct_count=payload.correct_count,
            score_percent=payload.score_percent,
            passed=derived_passed,
            is_human_reviewed=payload.is_human_reviewed,
            responses=payload.responses or {},
            attempted_at=payload.attempted_at,
            metadata=payload.metadata or {},
            created_at=payload.attempted_at,
            updated_at=payload.attempted_at,
        )
        self.quiz_attempts.insert(0, attempt)
        return attempt

    async def record_walkthrough_event(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        self.walkthrough_event_calls += 1
        self.last_walkthrough_payload = (args, kwargs)
        analysis_id = kwargs.get("analysis_id", uuid4())
        section_key = kwargs.get("section_key")
        progress_percent = kwargs.get("progress_percent", 0)
        completed_at = kwargs.get("completed_at")
        completed_iso = completed_at.isoformat() if completed_at else None
        analysis_runs = {
            str(analysis_id): {
                "completed_sections": ([section_key] if section_key else []),
                "progress_percent": progress_percent,
                "last_event_at": completed_iso,
            }
        }
        if progress_percent >= 100 and completed_iso:
            analysis_runs[str(analysis_id)]["completed_at"] = completed_iso

        sections: dict[str, dict[str, object]] = {}
        if section_key:
            section_entry: dict[str, object] = {
                "analysis_runs": {
                    str(analysis_id): {
                        "progress_percent": progress_percent,
                        "last_event_at": completed_iso,
                    }
                },
                "latest_analysis_id": str(analysis_id),
                "latest_progress_percent": progress_percent,
                "last_event_at": completed_iso,
                "progress_percent": progress_percent,
            }
            if progress_percent >= 100 and completed_iso:
                section_entry["analysis_runs"][str(analysis_id)]["completed_at"] = completed_iso
                section_entry["completed_at"] = completed_iso
                section_entry["completed_analysis_ids"] = [str(analysis_id)]
            else:
                section_entry["analysis_runs"][str(analysis_id)].pop("completed_at", None)
                section_entry["completed_analysis_ids"] = []
            sections[section_key] = section_entry

        progress = LearningProgress(
            schema_version=1,
            progress_id=LearningProgressId(uuid4()),
            user_id=kwargs.get("user_id") or self.user_id,
            module_key=kwargs.get("module_key", "module"),
            progress_percent=progress_percent,
            last_interaction_at=completed_at,
            completed_at=completed_at,
            metadata={
                "analysis_walkthroughs": analysis_runs,
                "sections": sections,
                "section_progress_version": 1,
            },
            created_at=completed_at,
            updated_at=completed_at,
        )
        self.progress_records.append(progress)
        return progress

    async def get_best_quiz_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttempt | None:
        assert user_id == self.user_id
        self.best_attempt_calls += 1
        relevant = [attempt for attempt in self.quiz_attempts if attempt.quiz_id == quiz_id]
        if not relevant:
            return None
        return max(relevant, key=lambda attempt: attempt.score_percent)


@pytest.fixture
def user_id() -> UserId:
    return UserId(uuid4())


@pytest.fixture
def fake_learning_service(user_id: UserId) -> FakeLearningService:
    service = FakeLearningService(user_id)
    now = datetime.now(UTC)

    progress = LearningProgress(
        schema_version=1,
        progress_id=LearningProgressId(uuid4()),
        user_id=user_id,
        module_key="mda_foundations",
        progress_percent=40,
        last_interaction_at=now,
        completed_at=None,
        metadata={"section_progress_version": 1},
        created_at=now,
        updated_at=now,
    )

    attempt_one = QuizAttempt(
        schema_version=1,
        attempt_id=QuizAttemptId(uuid4()),
        user_id=user_id,
        quiz_id="quiz-1",
        question_count=3,
        correct_count=2,
        score_percent=66.67,
        passed=False,
        is_human_reviewed=False,
        attempted_at=now,
        metadata={"duration_seconds": 45},
        created_at=now,
        updated_at=now,
    )

    attempt_two = QuizAttempt(
        schema_version=1,
        attempt_id=QuizAttemptId(uuid4()),
        user_id=user_id,
        quiz_id="quiz-1",
        question_count=3,
        correct_count=3,
        score_percent=100.0,
        passed=True,
        is_human_reviewed=True,
        attempted_at=now,
        metadata={"duration_seconds": 30},
        created_at=now,
        updated_at=now,
    )

    service.progress_records.append(progress)
    service.quiz_attempts.extend([attempt_one, attempt_two])
    return service


@pytest.fixture
def learning_app(
    fake_learning_service: FakeLearningService,
    user_id: UserId,
) -> FastAPI:
    app = FastAPI()
    app.include_router(learning.router, prefix="/api")

    async def override_current_user():  # type: ignore[no-untyped-def]
        return AuthenticationResult(
            authenticated=True,
            user_id=user_id,
            user_email="learner@example.com",
            user_tier="BASIC",
            permissions=[],
        )

    async def override_learning_service():  # type: ignore[no-untyped-def]
        return fake_learning_service

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_learning_service] = override_learning_service

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(learning_app: FastAPI):
    transport = ASGITransport(app=learning_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_list_learning_progress_returns_progress_entries(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    response = await api_client.get("/api/learning/progress")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == len(fake_learning_service.progress_records)
    assert payload[0]["module_key"] == fake_learning_service.progress_records[0].module_key
    assert fake_learning_service.list_calls == 1


@pytest.mark.asyncio
async def test_upsert_learning_progress_updates_existing_entry(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    response = await api_client.put(
        "/api/learning/progress/mda_foundations",
        json={"progress_percent": 100, "metadata": {"section_progress_version": 2}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["progress_percent"] == 100
    assert body["completed_at"] is not None
    assert fake_learning_service.upsert_calls == 1
    assert fake_learning_service.last_upsert_payload is not None
    assert fake_learning_service.last_upsert_payload.module_key == "mda_foundations"
    assert fake_learning_service.last_upsert_payload.progress_percent == 100


@pytest.mark.asyncio
async def test_record_walkthrough_event_endpoint(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    analysis_id = str(uuid4())
    response = await api_client.post(
        "/api/learning/progress/module-a/walkthrough-events",
        json={
            "analysis_id": analysis_id,
            "section_key": "section-1",
            "progress_percent": 100,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["progress_percent"] == 100
    section_meta = payload["metadata"].get("sections", {})
    assert section_meta.get("section-1", {}).get("progress_percent") == 100
    assert payload["metadata"].get("section_progress_version") == 1
    assert fake_learning_service.walkthrough_event_calls == 1


@pytest.mark.asyncio
async def test_list_quiz_attempts_respects_limit(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    response = await api_client.get("/api/learning/quiz-attempts", params={"limit": 1})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert fake_learning_service.recent_attempt_calls == 1


@pytest.mark.asyncio
async def test_record_quiz_attempt_creates_entry(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    payload = {
        "quiz_id": "quiz-2",
        "question_count": 4,
        "correct_count": 4,
        "score_percent": 100.0,
        "passed": True,
        "metadata": {"duration_seconds": 25},
    }

    response = await api_client.post("/api/learning/quiz-attempts", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["quiz_id"] == "quiz-2"
    assert body["attempt_id"]
    assert fake_learning_service.record_attempt_calls == 1
    assert fake_learning_service.last_attempt_payload is not None
    assert fake_learning_service.last_attempt_payload.quiz_id == "quiz-2"


@pytest.mark.asyncio
async def test_get_best_quiz_attempt_returns_highest_score(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    response = await api_client.get("/api/learning/quiz-attempts/quiz-1/best")

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["score_percent"] == 100.0
    assert fake_learning_service.best_attempt_calls == 1


@pytest.mark.asyncio
async def test_get_best_quiz_attempt_returns_none_when_missing(
    api_client: AsyncClient,
    fake_learning_service: FakeLearningService,
) -> None:
    response = await api_client.get("/api/learning/quiz-attempts/nonexistent/best")

    assert response.status_code == 200
    assert response.json() is None
