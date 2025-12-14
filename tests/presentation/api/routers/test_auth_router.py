# mypy: ignore-errors
import os
from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import src.presentation.api.routers.auth as auth_router
from src.application.interfaces.authentication import (
    AuthenticationCredentials,
    AuthenticationResult,
    RateLimitInfo,
)
from src.shared.types import UserId

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "Request failed")
        code = detail.get("code")
        extras = {k: v for k, v in detail.items() if k not in {"message", "code"}}
    else:
        message = str(detail) if detail is not None else "Request failed"
        code = None
        extras: dict[str, object] = {}

    payload: dict[str, object] = {
        "message": message,
        "status_code": exc.status_code,
        "path": str(request.url.path),
    }
    if code:
        payload["code"] = code
    if extras:
        payload["details"] = extras

    return JSONResponse(status_code=exc.status_code, content={"error": payload})


class StubAuthProvider:
    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:  # pragma: no cover - not exercised
        raise NotImplementedError

    async def authorize(
        self, user_id, resource: str, action: str
    ) -> bool:  # pragma: no cover - not exercised
        return True

    async def validate_token(
        self, token: str
    ) -> AuthenticationResult:  # pragma: no cover - not exercised
        raise NotImplementedError

    async def refresh_token(self, refresh_token: str) -> AuthenticationCredentials:
        raise AssertionError(
            "refresh_token should not be called when cookie is missing"
        )

    async def revoke_token(
        self, token: str
    ) -> bool:  # pragma: no cover - not exercised
        return True

    async def get_rate_limit(
        self, user_id
    ) -> RateLimitInfo:  # pragma: no cover - not exercised
        return RateLimitInfo(limit=1, remaining=1, reset_at="", window_seconds=1)

    async def check_rate_limit(
        self, user_id, increment: bool = True
    ) -> bool:  # pragma: no cover - not exercised
        return True

    async def health_check(self) -> bool:  # pragma: no cover - not exercised
        return True


@pytest.fixture()
def auth_client_factory() -> Callable[..., tuple[TestClient, StubAuthProvider]]:
    def _factory(
        *,
        auth_provider: StubAuthProvider | None = None,
        config_provider: object | None = None,
        secret_manager: object | None = None,
    ) -> tuple[TestClient, StubAuthProvider]:
        app = FastAPI()
        app.add_exception_handler(HTTPException, http_exception_handler)
        app.include_router(auth_router.router, prefix="/api")
        provider = auth_provider or StubAuthProvider()
        app.dependency_overrides[auth_router.get_authentication_provider] = (
            lambda: provider
        )
        app.dependency_overrides[auth_router.get_config_provider] = (
            lambda: config_provider or StubConfigProvider()
        )
        app.dependency_overrides[auth_router.get_secret_manager] = (
            lambda: secret_manager or StubSecretManager()
        )
        return TestClient(app), provider

    return _factory


class StubConfigProvider:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values or {}

    def get_string(self, key: str, default: str | None = None) -> str:
        if key in self.values:
            return self.values[key]
        if default is not None:
            return default
        raise AssertionError(f"Unexpected config key: {key}")


class StubSecretManager:
    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self.secrets = secrets or {"GOOGLE_CLIENT_ID": "stub-client-id"}
        self.requested: list[str] = []

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        self.requested.append(secret_name)
        try:
            return self.secrets[secret_name]
        except KeyError as exc:
            raise AssertionError(f"Unexpected secret: {secret_name}") from exc


class RecordingAuthProvider(StubAuthProvider):
    def __init__(self, result: AuthenticationResult) -> None:
        self.result = result
        self.authenticate_calls: list[AuthenticationCredentials] = []

    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        self.authenticate_calls.append(credentials)
        return self.result


class UnexpectedAuthCallProvider(StubAuthProvider):
    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        raise AssertionError("authenticate should not be called for this request")


def test_refresh_requires_cookie(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory()
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "auth.refresh.missing_token"
    assert body["error"]["message"] == "Refresh token cookie is missing"


def test_google_login_sets_oauth_cookies(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory()

    response = client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 307
    cookies = response.headers.get_list("set-cookie")
    assert any(header.startswith(f"{auth_router.STATE_COOKIE}=") for header in cookies)
    assert any(
        header.startswith(f"{auth_router.VERIFIER_COOKIE}=") for header in cookies
    )

    state_cookie = next(
        header for header in cookies if header.startswith(f"{auth_router.STATE_COOKIE}=")
    )
    verifier_cookie = next(
        header
        for header in cookies
        if header.startswith(f"{auth_router.VERIFIER_COOKIE}=")
    )

    assert "httponly" in state_cookie.lower()
    assert "path=/api" in state_cookie.lower()
    assert "samesite=lax" in state_cookie.lower()
    assert f"max-age={auth_router.STATE_TTL_SECONDS}" in state_cookie.lower()

    assert "httponly" in verifier_cookie.lower()
    assert "path=/api" in verifier_cookie.lower()
    assert "samesite=lax" in verifier_cookie.lower()
    assert f"max-age={auth_router.STATE_TTL_SECONDS}" in verifier_cookie.lower()


def test_google_login_sets_redirect_hint_cookie_without_httponly(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory()

    response = client.get(
        "/api/auth/google/login",
        params={"redirectTo": "/dashboard"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    cookies = response.headers.get_list("set-cookie")
    redirect_cookie = next(
        header
        for header in cookies
        if header.startswith(f"{auth_router.REDIRECT_COOKIE}=")
    )
    assert "httponly" not in redirect_cookie.lower()
    assert "path=/api" in redirect_cookie.lower()
    assert "samesite=lax" in redirect_cookie.lower()
    assert f"max-age={auth_router.REDIRECT_TTL_SECONDS}" in redirect_cookie.lower()


def test_google_login_uses_secure_cookies_in_production(
    monkeypatch: pytest.MonkeyPatch,
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    monkeypatch.setattr(auth_router.settings, "environment", "production")
    client, _ = auth_client_factory()

    response = client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 307
    cookies = response.headers.get_list("set-cookie")
    state_cookie = next(
        header for header in cookies if header.startswith(f"{auth_router.STATE_COOKIE}=")
    )
    assert "secure" in state_cookie.lower()


def test_google_callback_requires_state_cookie(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory(auth_provider=UnexpectedAuthCallProvider())

    response = client.post(
        "/api/auth/google/callback",
        json={"code": "auth-code", "state": "state-value"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "auth.state.missing"


def test_google_callback_rejects_state_mismatch(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory(auth_provider=UnexpectedAuthCallProvider())

    response = client.post(
        "/api/auth/google/callback",
        json={"code": "auth-code", "state": "wrong-state"},
        cookies={auth_router.STATE_COOKIE: "expected-state"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "auth.state.mismatch"


def test_google_callback_requires_pkce_verifier_cookie(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    client, _ = auth_client_factory(auth_provider=UnexpectedAuthCallProvider())

    response = client.post(
        "/api/auth/google/callback",
        json={"code": "auth-code", "state": "expected-state"},
        cookies={auth_router.STATE_COOKIE: "expected-state"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "auth.pkce.missing"


def test_google_callback_sets_refresh_cookie_and_clears_ephemeral_cookies(
    auth_client_factory: Callable[..., tuple[TestClient, StubAuthProvider]],
) -> None:
    result = AuthenticationResult(
        authenticated=True,
        user_id=UserId(uuid4()),
        user_email="user@example.com",
        user_tier="ESSENTIAL",
        permissions=["filings:read"],
        access_token="access-token",
        refresh_token="refresh-token",
        expires_in=3600,
        refresh_expires_in=7200,
        issued_at="2025-01-01T00:00:00Z",
    )
    provider = RecordingAuthProvider(result)
    client, _ = auth_client_factory(
        auth_provider=provider,
        config_provider=StubConfigProvider(
            {"authentication.google.redirect_uri": "http://localhost:3000/auth/google/callback"}
        ),
    )

    response = client.post(
        "/api/auth/google/callback",
        json={"code": "auth-code", "state": "expected-state"},
        cookies={
            auth_router.STATE_COOKIE: "expected-state",
            auth_router.VERIFIER_COOKIE: "verifier",
            auth_router.REDIRECT_COOKIE: "/dashboard",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accessToken"] == "access-token"
    assert payload["user"]["email"] == "user@example.com"

    assert len(provider.authenticate_calls) == 1
    recorded = provider.authenticate_calls[0]
    assert recorded.token == "auth-code"
    assert recorded.token_type == auth_router.OAuthTokenType.AUTHORIZATION_CODE
    assert recorded.code_verifier == "verifier"

    cookies = response.headers.get_list("set-cookie")
    refresh_cookie = next(
        header
        for header in cookies
        if header.startswith(f"{auth_router.REFRESH_COOKIE}=")
    )
    assert "httponly" in refresh_cookie.lower()
    assert "path=/api" in refresh_cookie.lower()
    assert "samesite=lax" in refresh_cookie.lower()
    assert "max-age=7200" in refresh_cookie.lower()

    cleared_names = {
        auth_router.STATE_COOKIE,
        auth_router.VERIFIER_COOKIE,
        auth_router.REDIRECT_COOKIE,
    }
    for name in cleared_names:
        cleared = next(header for header in cookies if header.startswith(f"{name}="))
        assert "max-age=0" in cleared.lower()
