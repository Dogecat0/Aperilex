from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    AuthSessionData,
    LearningProgressData,
    QuizAttemptData,
    UserData,
    UserIdentityData,
    UserProfileData,
)
from src.infrastructure.database.repositories.auth_rate_limit_repository import (
    AuthRateLimitRepository,
)
from src.infrastructure.database.repositories.auth_session_repository import (
    AuthSessionRepository,
)
from src.infrastructure.database.repositories.learning_progress_repository import (
    LearningProgressRepository,
)
from src.infrastructure.database.repositories.quiz_attempt_repository import (
    QuizAttemptRepository,
)
from src.infrastructure.database.repositories.user_identity_repository import (
    UserIdentityRepository,
)
from src.infrastructure.database.repositories.user_profile_repository import (
    UserProfileRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.enums import UserStatus, UserTier
from src.shared.types import (
    AuthSessionId,
    Email,
    LearningProgressId,
    QuizAttemptId,
    UserId,
    UserIdentityId,
    UserProfileId,
)


async def _create_user(db_session: AsyncSession, *, email: str) -> UserData:
    repo = UserRepository(db_session)
    created = await repo.create(
        UserData(
            id=UserId(uuid.uuid4()),
            email=Email(value=email),
            status=UserStatus.ACTIVE,
            tier=UserTier.ESSENTIAL,
        )
    )
    await db_session.commit()
    return created


@pytest.mark.asyncio
async def test_user_repository_cache_invalidation_on_email_update(
    db_session: AsyncSession,
) -> None:
    repo = UserRepository(db_session)
    created = await repo.create(
        UserData(
            id=UserId(uuid.uuid4()),
            email=Email(value="cache-user@example.com"),
            status=UserStatus.ACTIVE,
            tier=UserTier.ESSENTIAL,
        )
    )
    await db_session.commit()

    assert await repo.exists(created.id) is True

    cached_old = await repo.get_by_email(Email(value="cache-user@example.com"))
    assert cached_old is not None
    assert cached_old.id == created.id

    await repo.update(
        created.model_copy(update={"email": Email(value="cache-user+new@example.com")})
    )
    await db_session.commit()

    cached_new = await repo.get_by_email(Email(value="cache-user+new@example.com"))
    assert cached_new is not None
    assert cached_new.id == created.id
    assert cached_new.email.value == "cache-user+new@example.com"

    assert await repo.get_by_email(Email(value="cache-user@example.com")) is None

    _ = await repo.get_by_id(created.id)
    assert await repo.set_status(created.id, UserStatus.SUSPENDED) is True
    await db_session.commit()

    refreshed = await repo.get_by_id(created.id)
    assert refreshed is not None
    assert refreshed.status == UserStatus.SUSPENDED

    assert await repo.delete(created.id) is True
    await db_session.commit()
    assert await repo.get_by_id(created.id) is None
    assert await repo.get_by_email(Email(value="cache-user+new@example.com")) is None
    assert await repo.exists(created.id) is False


@pytest.mark.asyncio
async def test_user_identity_repository_cache_invalidation_on_subject_update(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="identity-user@example.com")
    repo = UserIdentityRepository(db_session)
    identity = await repo.create(
        UserIdentityData(
            id=UserIdentityId(uuid.uuid4()),
            user_id=user.id,
            provider="google",
            provider_subject="subject-1",
            provider_email=Email(value="identity-user@example.com"),
            raw_profile={"sub": "subject-1"},
            verified_at=datetime.now(UTC),
            schema_version=1,
        )
    )
    await db_session.commit()
    assert identity.provider == "GOOGLE"

    cached_old = await repo.get_by_provider_subject("google", "subject-1")
    assert cached_old is not None
    assert cached_old.id == identity.id

    await repo.update(
        identity.model_copy(
            update={
                "provider_subject": "subject-2",
                "raw_profile": {"sub": "subject-2"},
            }
        )
    )
    await db_session.commit()

    cached_new = await repo.get_by_provider_subject("google", "subject-2")
    assert cached_new is not None
    assert cached_new.id == identity.id
    assert cached_new.provider_subject == "subject-2"

    assert await repo.get_by_provider_subject("google", "subject-1") is None

    identities = await repo.list_for_user(user.id)
    assert len(identities) == 1
    assert identities[0].provider_subject == "subject-2"

    assert await repo.delete(identity.id) is True
    await db_session.commit()
    assert await repo.get_by_id(identity.id) is None
    assert await repo.get_by_provider_subject("google", "subject-2") is None


@pytest.mark.asyncio
async def test_user_profile_repository_upsert_and_cache_invalidation(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="profile-user@example.com")
    repo = UserProfileRepository(db_session)

    profile = UserProfileData(
        id=UserProfileId(uuid.uuid4()),
        user_id=user.id,
        display_name="Initial",
        avatar_url=None,
        preferences={"theme": "dark"},
        time_zone="UTC",
        schema_version=1,
    )

    saved = await repo.upsert(profile)
    await db_session.commit()
    assert saved.display_name == "Initial"

    cached = await repo.get_by_user_id(user.id)
    assert cached is not None
    assert cached.id == saved.id
    assert cached.preferences["theme"] == "dark"

    updated = await repo.upsert(
        profile.model_copy(
            update={
                "display_name": "Updated",
                "preferences": {"theme": "light", "density": "compact"},
            }
        )
    )
    await db_session.commit()
    assert updated.display_name == "Updated"

    refreshed = await repo.get_by_user_id(user.id)
    assert refreshed is not None
    assert refreshed.display_name == "Updated"
    assert refreshed.preferences["theme"] == "light"

    assert await repo.delete(profile.id) is True
    await db_session.commit()
    assert await repo.get_by_id(profile.id) is None
    assert await repo.get_by_user_id(user.id) is None


@pytest.mark.asyncio
async def test_auth_session_repository_rotation_revoke_and_expiry(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="session-user@example.com")
    repo = AuthSessionRepository(db_session)

    issued_at = datetime.now(UTC) - timedelta(minutes=1)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    session = await repo.create(
        AuthSessionData(
            id=AuthSessionId(uuid.uuid4()),
            user_id=user.id,
            refresh_token_hash="hash-1",
            previous_refresh_token_hash=None,
            session_key="device-1",
            user_agent="pytest",
            ip_address="127.0.0.1",
            issued_at=issued_at,
            expires_at=expires_at,
            last_refreshed_at=None,
            revoked_at=None,
            revoked_reason=None,
            metadata={"source": "test"},
            schema_version=1,
        )
    )
    await db_session.commit()

    by_hash = await repo.get_by_refresh_token_hash("hash-1")
    assert by_hash is not None
    assert by_hash.id == session.id

    rotated_at = datetime.now(UTC)
    rotated = await repo.rotate_refresh_token(
        session.id,
        refresh_token_hash="hash-2",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
        previous_hash="hash-1",
        rotation_time=rotated_at,
    )
    await db_session.commit()
    assert rotated.refresh_token_hash == "hash-2"
    assert rotated.previous_refresh_token_hash == "hash-1"
    assert rotated.last_refreshed_at == rotated_at
    assert rotated.revoked_at is None

    active = await repo.list_active_for_user(user.id)
    assert [item.id for item in active] == [session.id]

    revoked_at = datetime.now(UTC)
    assert await repo.mark_revoked(session.id, revoked_at, reason="logout") is True
    await db_session.commit()

    assert await repo.list_active_for_user(user.id) == []

    touched_at = datetime.now(UTC)
    assert await repo.update_last_activity(session.id, touched_at) is True
    await db_session.commit()

    refreshed_session = await repo.get_by_id(session.id)
    assert refreshed_session is not None
    assert refreshed_session.last_refreshed_at == touched_at
    assert refreshed_session.revoked_at == revoked_at
    assert refreshed_session.revoked_reason == "logout"

    expired = await repo.create(
        AuthSessionData(
            id=AuthSessionId(uuid.uuid4()),
            user_id=user.id,
            refresh_token_hash="expired-hash",
            previous_refresh_token_hash=None,
            session_key="device-expired",
            user_agent=None,
            ip_address=None,
            issued_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            last_refreshed_at=None,
            revoked_at=None,
            revoked_reason=None,
            metadata={},
            schema_version=1,
        )
    )
    await db_session.commit()

    deleted = await repo.delete_expired(now=datetime.now(UTC), limit=10)
    await db_session.commit()
    assert deleted == 1
    assert await repo.get_by_id(expired.id) is None


@pytest.mark.asyncio
async def test_auth_rate_limit_repository_windowing_and_cleanup(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="ratelimit-user@example.com")
    repo = AuthRateLimitRepository(db_session)

    now = datetime.now(UTC)
    data, allowed = await repo.increment_and_get(
        key="ip:127.0.0.1",
        action="LOGIN",
        user_id=user.id,
        window_seconds=60,
        limit=2,
        now=now,
    )
    await db_session.commit()
    assert data.count == 1
    assert allowed is True

    data, allowed = await repo.increment_and_get(
        key="ip:127.0.0.1",
        action="LOGIN",
        user_id=user.id,
        window_seconds=60,
        limit=2,
        now=now + timedelta(seconds=1),
    )
    await db_session.commit()
    assert data.count == 2
    assert allowed is True

    data, allowed = await repo.increment_and_get(
        key="ip:127.0.0.1",
        action="LOGIN",
        user_id=user.id,
        window_seconds=60,
        limit=2,
        now=now + timedelta(seconds=2),
    )
    await db_session.commit()
    assert data.count == 3
    assert allowed is False

    data, allowed = await repo.increment_and_get(
        key="ip:127.0.0.1",
        action="LOGIN",
        user_id=user.id,
        window_seconds=60,
        limit=2,
        now=now + timedelta(seconds=61),
    )
    await db_session.commit()
    assert data.count == 1
    assert allowed is True

    assert await repo.reset("ip:127.0.0.1", "LOGIN") is True
    await db_session.commit()

    reset_state = await repo.get_current("ip:127.0.0.1", "LOGIN")
    assert reset_state is not None
    assert reset_state.count == 0

    base_time = datetime(2025, 1, 1, tzinfo=UTC)
    _old, _ = await repo.increment_and_get(
        key="cleanup:old",
        action="REFRESH",
        user_id=None,
        window_seconds=60,
        limit=1,
        now=base_time,
    )
    _boundary, _ = await repo.increment_and_get(
        key="cleanup:boundary",
        action="REFRESH",
        user_id=None,
        window_seconds=60,
        limit=1,
        now=base_time + timedelta(seconds=90),
    )
    await db_session.commit()

    deleted = await repo.cleanup(older_than=base_time + timedelta(seconds=120), limit=10)
    await db_session.commit()
    assert deleted == 1
    assert await repo.get_current("cleanup:old", "REFRESH") is None
    assert await repo.get_current("cleanup:boundary", "REFRESH") is not None


@pytest.mark.asyncio
async def test_learning_progress_repository_upsert_and_cache_invalidation(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="learning-user@example.com")
    repo = LearningProgressRepository(db_session)

    now = datetime.now(UTC)
    progress = LearningProgressData(
        id=LearningProgressId(uuid.uuid4()),
        user_id=user.id,
        module_key="orientation",
        progress_percent=10,
        last_interaction_at=now,
        completed_at=None,
        metadata={"source": "test"},
        schema_version=1,
        is_unlocked=True,
        unlocked_at=now,
    )
    saved = await repo.upsert(progress)
    await db_session.commit()
    assert saved.is_unlocked is True
    assert saved.unlocked_at == now

    cached = await repo.get_for_user_module(user.id, "orientation")
    assert cached is not None
    assert cached.progress_percent == 10

    updated = await repo.upsert(
        progress.model_copy(
            update={
                "progress_percent": 100,
                "completed_at": now + timedelta(minutes=5),
            }
        )
    )
    await db_session.commit()
    assert updated.progress_percent == 100
    assert updated.completed_at is not None

    refreshed = await repo.get_for_user_module(user.id, "orientation")
    assert refreshed is not None
    assert refreshed.progress_percent == 100

    assert await repo.delete(progress.id) is True
    await db_session.commit()
    assert await repo.get_by_id(progress.id) is None


@pytest.mark.asyncio
async def test_quiz_attempt_repository_best_latest_and_cache_invalidation(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="quiz-user@example.com")
    repo = QuizAttemptRepository(db_session)

    now = datetime.now(UTC)
    quiz_id = "risk_mastery"

    attempt_1 = await repo.record_attempt(
        QuizAttemptData(
            id=QuizAttemptId(uuid.uuid4()),
            user_id=user.id,
            quiz_id=quiz_id,
            question_count=10,
            correct_count=7,
            score_percent=70.0,
            passed=False,
            is_human_reviewed=False,
            responses={"q1": "a"},
            metadata={"source": "test"},
            attempted_at=now,
            schema_version=1,
        )
    )
    await db_session.commit()

    attempt_2 = await repo.record_attempt(
        QuizAttemptData(
            id=QuizAttemptId(uuid.uuid4()),
            user_id=user.id,
            quiz_id=quiz_id,
            question_count=10,
            correct_count=9,
            score_percent=90.0,
            passed=True,
            is_human_reviewed=False,
            responses={"q1": "b"},
            metadata={},
            attempted_at=now + timedelta(minutes=1),
            schema_version=1,
        )
    )
    await db_session.commit()

    latest = await repo.get_latest_for_quiz(user.id, quiz_id)
    assert latest is not None
    assert latest.id == attempt_2.id

    best = await repo.get_best_attempt(user.id, quiz_id)
    assert best is not None
    assert best.id == attempt_2.id
    assert isinstance(best.score_percent, float)

    _ = await repo.get_best_attempt(user.id, quiz_id)
    attempt_3 = await repo.record_attempt(
        QuizAttemptData(
            id=QuizAttemptId(uuid.uuid4()),
            user_id=user.id,
            quiz_id=quiz_id,
            question_count=10,
            correct_count=10,
            score_percent=95.0,
            passed=True,
            is_human_reviewed=True,
            responses={},
            metadata={},
            attempted_at=now + timedelta(minutes=2),
            schema_version=1,
        )
    )
    await db_session.commit()

    refreshed_best = await repo.get_best_attempt(user.id, quiz_id)
    assert refreshed_best is not None
    assert refreshed_best.id == attempt_3.id
    assert refreshed_best.score_percent == 95.0

    all_attempts = await repo.list_for_user(user.id, limit=10)
    assert [attempt.id for attempt in all_attempts] == [
        attempt_3.id,
        attempt_2.id,
        attempt_1.id,
    ]
