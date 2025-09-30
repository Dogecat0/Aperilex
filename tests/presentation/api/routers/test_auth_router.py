import os

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
def test_client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(auth_router.router, prefix="/api")
    app.dependency_overrides[auth_router.get_authentication_provider] = (
        lambda: StubAuthProvider()
    )
    return TestClient(app)


def test_refresh_requires_cookie(test_client: TestClient) -> None:
    response = test_client.post("/api/auth/refresh")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "auth.refresh.missing_token"
    assert body["error"]["message"] == "Refresh token cookie is missing"
