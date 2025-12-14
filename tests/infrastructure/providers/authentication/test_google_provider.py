"""Tests for the GoogleOAuthAuthenticationProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from src.application.interfaces.authentication import (
    AuthenticationCredentials,
    AuthenticationError,
)
from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.database import IDatabaseProvider
from src.application.interfaces.repositories import (
    AuthRateLimitData,
    AuthSessionData,
    UserData,
    UserIdentityData,
)
from src.application.interfaces.secret import ISecretManager
from src.infrastructure.providers.authentication.google_oauth_provider import (
    GoogleOAuthAuthenticationProvider,
)
from src.shared.enums import UserTier
from src.shared.types import AuthRateLimitId, AuthSessionId, UserId


class StubConfigProvider:
    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._overrides = overrides or {}

    def get_string(self, key: str, default: str | None = None) -> str:
        value = self._overrides.get(key, default)
        if value is None:
            raise KeyError(key)
        return str(value)

    def get_int(self, key: str, default: int | None = None) -> int:
        value = self._overrides.get(key, default)
        if value is None:
            raise KeyError(key)
        return int(value)

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        value = self._overrides.get(key, default)
        if value is None:
            raise KeyError(key)
        return bool(value)

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        value = self._overrides.get(key, default)
        if value is None:
            raise KeyError(key)
        return list(value)

    def get_dict(self, key: str, default: dict[str, str] | None = None) -> dict[str, str]:
        value = self._overrides.get(key, default)
        if value is None:
            raise KeyError(key)
        return dict(value)


class StubSecretManager:
    def __init__(self, secrets: dict[str, str]) -> None:
        self._secrets = secrets

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        if secret_name not in self._secrets:
            raise KeyError(secret_name)
        return self._secrets[secret_name]


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UserId, UserData] = {}

    async def get_by_id(self, user_id: UserId) -> UserData | None:
        return self.users.get(user_id)

    async def create(self, user: UserData) -> UserData:
        self.users[user.id] = user
        return user

    async def update(self, user: UserData) -> UserData:
        self.users[user.id] = user
        return user


class InMemoryUserIdentityRepository:
    def __init__(self) -> None:
        self.identities: dict[tuple[str, str], UserIdentityData] = {}

    async def get_by_provider_subject(
        self, provider: str, provider_subject: str
    ) -> UserIdentityData | None:
        return self.identities.get((provider, provider_subject))

    async def create(self, identity: UserIdentityData) -> UserIdentityData:
        self.identities[(identity.provider, identity.provider_subject)] = identity
        return identity


class InMemoryAuthSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[AuthSessionId, AuthSessionData] = {}
        self.hash_index: dict[str, AuthSessionId] = {}

    async def create(self, session: AuthSessionData) -> AuthSessionData:
        self.sessions[session.id] = session
        self.hash_index[session.refresh_token_hash] = session.id
        return session

    async def get_by_id(self, session_id: AuthSessionId) -> AuthSessionData | None:
        return self.sessions.get(session_id)

    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> AuthSessionData | None:
        session_id = self.hash_index.get(refresh_token_hash)
        if session_id is None:
            return next(
                (
                    session
                    for session in self.sessions.values()
                    if session.previous_refresh_token_hash == refresh_token_hash
                ),
                None,
            )
        return self.sessions.get(session_id)

    async def list_active_for_user(
        self, user_id: UserId, *, limit: int = 20
    ) -> list[AuthSessionData]:
        return [
            session
            for session in self.sessions.values()
            if session.user_id == user_id and session.revoked_at is None
        ][:limit]

    async def rotate_refresh_token(
        self,
        session_id: AuthSessionId,
        refresh_token_hash: str,
        expires_at: datetime,
        *,
        previous_hash: str | None,
        rotation_time: datetime,
    ) -> AuthSessionData:
        session = self.sessions[session_id]
        self.hash_index.pop(session.refresh_token_hash, None)
        session = session.model_copy(
            update={
                "previous_refresh_token_hash": previous_hash,
                "refresh_token_hash": refresh_token_hash,
                "expires_at": expires_at,
                "last_refreshed_at": rotation_time,
                "revoked_at": None,
                "revoked_reason": None,
            }
        )
        self.sessions[session_id] = session
        self.hash_index[refresh_token_hash] = session_id
        return session

    async def mark_revoked(
        self,
        session_id: AuthSessionId,
        revoked_at: datetime,
        reason: str | None = None,
    ) -> bool:
        session = self.sessions.get(session_id)
        if session is None:
            return False
        session = session.model_copy(
            update={"revoked_at": revoked_at, "revoked_reason": reason}
        )
        self.sessions[session_id] = session
        return True

    async def update_last_activity(
        self, session_id: AuthSessionId, timestamp: datetime
    ) -> bool:
        session = self.sessions.get(session_id)
        if session is None:
            return False
        session = session.model_copy(update={"last_refreshed_at": timestamp})
        self.sessions[session_id] = session
        return True

    async def delete_expired(self, *, now: datetime, limit: int = 100) -> int:
        expired = [
            session_id
            for session_id, session in self.sessions.items()
            if session.expires_at < now
        ][:limit]
        for session_id in expired:
            session = self.sessions.pop(session_id)
            self.hash_index.pop(session.refresh_token_hash, None)
        return len(expired)


class InMemoryAuthRateLimitRepository:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], AuthRateLimitData] = {}

    async def get_current(
        self, key: str, action: str
    ) -> AuthRateLimitData | None:
        return self.entries.get((key, action))

    async def increment_and_get(
        self,
        key: str,
        action: str,
        *,
        user_id: UserId | None,
        window_seconds: int,
        limit: int,
        now: datetime,
    ) -> tuple[AuthRateLimitData, bool]:
        entry = self.entries.get((key, action))
        if entry is None:
            entry = self._new_entry(key, action, user_id, window_seconds, limit, now)
            entry = entry.model_copy(update={"count": 1, "last_updated_at": now})
        else:
            window_end = entry.window_start + timedelta(seconds=entry.window_seconds)
            if window_end <= now or entry.window_seconds != window_seconds:
                entry = entry.model_copy(
                    update={
                        "window_start": self._window_floor(now, window_seconds),
                        "window_seconds": window_seconds,
                        "count": 0,
                    }
                )
            entry = entry.model_copy(
                update={
                    "count": entry.count + 1,
                    "limit": limit,
                    "user_id": user_id,
                    "last_updated_at": now,
                }
            )
        allowed = entry.count <= limit
        self.entries[(key, action)] = entry
        return entry, allowed

    async def reset(self, key: str, action: str) -> bool:
        entry = self.entries.get((key, action))
        if entry is None:
            return False
        entry = entry.model_copy(
            update={
                "window_start": self._window_floor(datetime.now(UTC), entry.window_seconds),
                "count": 0,
                "last_updated_at": datetime.now(UTC),
            }
        )
        self.entries[(key, action)] = entry
        return True

    async def cleanup(
        self,
        *,
        older_than: datetime,
        limit: int = 500,
    ) -> int:
        expired_keys = []
        for key, entry in list(self.entries.items())[:limit]:
            window_end = entry.window_start + timedelta(seconds=entry.window_seconds)
            if window_end < older_than:
                expired_keys.append(key)
        for key in expired_keys:
            self.entries.pop(key, None)
        return len(expired_keys)

    def _new_entry(
        self,
        key: str,
        action: str,
        user_id: UserId | None,
        window_seconds: int,
        limit: int,
        now: datetime,
    ) -> AuthRateLimitData:
        return AuthRateLimitData(
            id=AuthRateLimitId(uuid4()),
            key=key,
            action=action,
            user_id=user_id,
            window_start=self._window_floor(now, window_seconds),
            window_seconds=window_seconds,
            count=0,
            limit=limit,
            last_updated_at=now,
            metadata={},
        )

    @staticmethod
    def _window_floor(moment: datetime, window_seconds: int) -> datetime:
        epoch_seconds = int(moment.timestamp())
        floored = epoch_seconds - (epoch_seconds % window_seconds)
        return datetime.fromtimestamp(floored, tz=UTC)


class InMemoryRepositoryFactory:
    def __init__(self) -> None:
        self.user_repository = InMemoryUserRepository()
        self.identity_repository = InMemoryUserIdentityRepository()
        self.auth_session_repository = InMemoryAuthSessionRepository()
        self.auth_rate_limit_repository = InMemoryAuthRateLimitRepository()

    async def get_user_repository(self) -> InMemoryUserRepository:
        return self.user_repository

    async def get_user_identity_repository(
        self,
    ) -> InMemoryUserIdentityRepository:
        return self.identity_repository

    async def get_auth_session_repository(
        self,
    ) -> InMemoryAuthSessionRepository:
        return self.auth_session_repository

    async def get_auth_rate_limit_repository(
        self,
    ) -> InMemoryAuthRateLimitRepository:
        return self.auth_rate_limit_repository

    async def begin_transaction(self) -> None:  # pragma: no cover - no-op
        return None

    async def commit_transaction(self) -> None:  # pragma: no cover - no-op
        return None

    async def rollback_transaction(self) -> None:  # pragma: no cover - no-op
        return None

    async def close(self, success: bool = True) -> None:  # pragma: no cover - no-op
        return None


class StubDatabaseProvider:
    def __init__(self, factory: InMemoryRepositoryFactory) -> None:
        self.factory = factory

    def get_repository_factory(self) -> InMemoryRepositoryFactory:
        return self.factory


@pytest.fixture()
def provider(monkeypatch: pytest.MonkeyPatch) -> GoogleOAuthAuthenticationProvider:
    factory = InMemoryRepositoryFactory()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    config = StubConfigProvider(
        {
            "authentication.access_token_ttl_seconds": 3600,
            "authentication.refresh_token_ttl_seconds": 7200,
            "authentication.rate_limits.login.limit": 5,
            "authentication.rate_limits.login.window_seconds": 60,
            "authentication.rate_limits.refresh.limit": 5,
            "authentication.rate_limits.refresh.window_seconds": 60,
            "authentication.rate_limits.request.limit": 3,
            "authentication.rate_limits.request.window_seconds": 30,
            "authentication.default_user_tier": UserTier.ESSENTIAL.value,
            "authentication.jwt_issuer": "https://test-issuer",
            "authentication.jwt_audience": "test-audience",
            "authentication.jwt_key_id": "test-key",
        }
    )
    secret_manager = StubSecretManager(
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "JWT_PRIVATE_KEY": private_pem,
            "JWT_PUBLIC_KEY": public_pem,
        }
    )
    provider = GoogleOAuthAuthenticationProvider(
        config_provider=cast(IConfigProvider, config),
        secret_manager=cast(ISecretManager, secret_manager),
        database_provider=cast(IDatabaseProvider, StubDatabaseProvider(factory)),
    )

    async def fake_exchange(**_: Any) -> dict[str, Any]:
        return {"id_token": "fake-id-token"}

    async def fake_validate(_: str, *, access_token: str | None = None) -> dict[str, Any]:
        assert access_token is None or access_token == "access-token"
        return {
            "email": "user@example.com",
            "email_verified": True,
            "sub": "subject-123",
        }

    monkeypatch.setattr(provider, "_exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(provider, "_validate_google_id_token", fake_validate)

    return provider


@pytest.mark.asyncio
async def test_authenticate_creates_user_and_session(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    result = await provider.authenticate(
        AuthenticationCredentials(
            token="auth-code",
            token_type="authorization_code",
            redirect_uri="https://app.example.com/auth/callback",
            code_verifier="code-verifier",
        )
    )

    assert result.authenticated is True
    assert result.user_id is not None
    assert result.access_token
    assert result.refresh_token

    factory = cast(InMemoryRepositoryFactory, provider._repository_factory)
    session = next(iter(factory.auth_session_repository.sessions.values()))
    expected_hash = provider._hash_refresh_token(result.refresh_token or "")
    assert session.refresh_token_hash == expected_hash
    assert session.user_id == result.user_id

    assert len(factory.user_repository.users) == 1
    rate_key = (f"user:{result.user_id}:LOGIN", "LOGIN")
    assert rate_key in factory.auth_rate_limit_repository.entries


@pytest.mark.asyncio
async def test_refresh_rotates_token(provider: GoogleOAuthAuthenticationProvider) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )
    refreshed = await provider.refresh_token(auth.refresh_token or "")

    assert refreshed.token != auth.access_token
    assert refreshed.refresh_token != auth.refresh_token

    factory = cast(InMemoryRepositoryFactory, provider._repository_factory)
    session = next(iter(factory.auth_session_repository.sessions.values()))
    old_hash = provider._hash_refresh_token(auth.refresh_token or "")
    new_hash = provider._hash_refresh_token(refreshed.refresh_token or "")
    assert session.previous_refresh_token_hash == old_hash
    assert session.refresh_token_hash == new_hash


@pytest.mark.asyncio
async def test_refresh_token_requires_value(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token("")

    assert exc_info.value.code == "refresh.missing"


@pytest.mark.asyncio
async def test_refresh_token_unknown_token_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token("unknown-token")

    assert exc_info.value.code == "refresh.unknown"


@pytest.mark.asyncio
async def test_refresh_token_revoked_token_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )

    assert await provider.revoke_token(auth.refresh_token or "") is True

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token(auth.refresh_token or "")

    assert exc_info.value.code == "refresh.revoked"


@pytest.mark.asyncio
async def test_refresh_token_expired_token_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )

    factory = cast(InMemoryRepositoryFactory, provider._repository_factory)
    session_repo = factory.auth_session_repository
    session = next(iter(session_repo.sessions.values()))
    session_repo.sessions[session.id] = session.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token(auth.refresh_token or "")

    assert exc_info.value.code == "refresh.expired"


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_session(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )
    refreshed = await provider.refresh_token(auth.refresh_token or "")

    factory = cast(InMemoryRepositoryFactory, provider._repository_factory)
    session_repo = factory.auth_session_repository
    session = next(iter(session_repo.sessions.values()))
    assert session.previous_refresh_token_hash == provider._hash_refresh_token(
        auth.refresh_token or ""
    )
    assert session.refresh_token_hash == provider._hash_refresh_token(
        refreshed.refresh_token or ""
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token(auth.refresh_token or "")

    assert exc_info.value.code == "refresh.reused"
    revoked_session = session_repo.sessions[session.id]
    assert revoked_session.revoked_at is not None
    assert revoked_session.revoked_reason == "ROTATED_TOKEN_REUSE"


@pytest.mark.asyncio
async def test_refresh_token_enforces_rate_limit(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )
    current_refresh_token = auth.refresh_token or ""

    for _ in range(5):
        refreshed = await provider.refresh_token(current_refresh_token)
        current_refresh_token = refreshed.refresh_token or ""

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.refresh_token(current_refresh_token)

    assert exc_info.value.code == "rate_limit.refresh"


@pytest.mark.asyncio
async def test_authenticate_enforces_login_rate_limit(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    for _ in range(5):
        result = await provider.authenticate(
            AuthenticationCredentials(token="auth-code", token_type="authorization_code")
        )
        assert result.authenticated is True

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.authenticate(
            AuthenticationCredentials(token="auth-code", token_type="authorization_code")
        )

    assert exc_info.value.code == "rate_limit.login"


@pytest.mark.asyncio
async def test_validate_token_rejects_invalid_signature(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token("not-a-jwt-token")

    assert exc_info.value.code == "token.invalid"


@pytest.mark.asyncio
async def test_validate_token_missing_subject_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    await provider._ensure_jwt_keys()
    assert provider._jwt_private_key is not None

    issued_at = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": provider._jwt_issuer,
            "aud": provider._jwt_audience,
            "token_type": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(hours=1)).timestamp()),
        },
        provider._jwt_private_key,
        algorithm=provider._jwt_algorithm,
        headers={"kid": provider._jwt_key_id},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token(token)

    assert exc_info.value.code == "token.subject.missing"


@pytest.mark.asyncio
async def test_validate_token_invalid_subject_uuid_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    await provider._ensure_jwt_keys()
    assert provider._jwt_private_key is not None

    issued_at = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": provider._jwt_issuer,
            "aud": provider._jwt_audience,
            "sub": "not-a-uuid",
            "token_type": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(hours=1)).timestamp()),
        },
        provider._jwt_private_key,
        algorithm=provider._jwt_algorithm,
        headers={"kid": provider._jwt_key_id},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token(token)

    assert exc_info.value.code == "token.subject.invalid"


@pytest.mark.asyncio
async def test_validate_token_wrong_type_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    await provider._ensure_jwt_keys()
    assert provider._jwt_private_key is not None

    user_id = uuid4()
    issued_at = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": provider._jwt_issuer,
            "aud": provider._jwt_audience,
            "sub": str(user_id),
            "token_type": "refresh",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(hours=1)).timestamp()),
        },
        provider._jwt_private_key,
        algorithm=provider._jwt_algorithm,
        headers={"kid": provider._jwt_key_id},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token(token)

    assert exc_info.value.code == "token.type.invalid"


@pytest.mark.asyncio
async def test_validate_token_missing_user_raises(
    provider: GoogleOAuthAuthenticationProvider,
) -> None:
    await provider._ensure_jwt_keys()
    assert provider._jwt_private_key is not None

    issued_at = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": provider._jwt_issuer,
            "aud": provider._jwt_audience,
            "sub": str(uuid4()),
            "token_type": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(hours=1)).timestamp()),
        },
        provider._jwt_private_key,
        algorithm=provider._jwt_algorithm,
        headers={"kid": provider._jwt_key_id},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token(token)

    assert exc_info.value.code == "user.missing"


@pytest.mark.asyncio
async def test_request_rate_limit(provider: GoogleOAuthAuthenticationProvider) -> None:
    auth = await provider.authenticate(
        AuthenticationCredentials(token="auth-code", token_type="authorization_code")
    )
    user_id = auth.user_id
    assert user_id is not None

    assert await provider.check_rate_limit(user_id, increment=True) is True
    assert await provider.check_rate_limit(user_id, increment=True) is True

    info = await provider.get_rate_limit(user_id)
    assert info.limit == 3
    assert info.remaining == 1

    assert await provider.check_rate_limit(user_id, increment=True) is True
    info_after = await provider.get_rate_limit(user_id)
    assert info_after.remaining == 0
