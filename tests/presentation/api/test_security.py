"""Unit tests for the FastAPI security helpers."""
# mypy: ignore-errors

from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.infrastructure.providers.authentication import MockAuthenticationProvider
from src.presentation.api.security import get_current_user


def _make_request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    """Utility to construct a minimal ASGI request for testing."""

    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": headers or [],
    }

    async def receive() -> dict[str, Any]:  # pragma: no cover - protocol shim
        return {"type": "http.request", "body": b""}

    return Request(scope, receive)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_requires_authorization_header() -> None:
    """Missing Authorization header should raise a 401 error."""

    request = _make_request()
    provider = MockAuthenticationProvider()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(request, provider)

    assert exc.value.status_code == 401
    assert exc.value.detail == {"code": "auth.header.missing", "message": "Missing Authorization header"}


@pytest.mark.asyncio
async def test_get_current_user_returns_authenticated_result() -> None:
    """Valid bearer tokens should be delegated to the provider."""

    request = _make_request(
        headers=[(b"authorization", b"Bearer mock-token")]
    )
    provider = MockAuthenticationProvider()

    result = await get_current_user(
        request,
        provider,
        authorization="Bearer mock-token",
    )

    assert result.authenticated is True
    assert result.user_id is not None
