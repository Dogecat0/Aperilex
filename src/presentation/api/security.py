"""Security helpers for FastAPI presentation layer.

Provides request-scoped authentication utilities that leverage the
application-level authentication provider through dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status

from src.application.interfaces.authentication import (
    AuthenticationError,
    AuthenticationResult,
    IAuthenticationProvider,
)
from src.presentation.api.dependencies import get_authentication_provider

AuthHeader = Annotated[
    str | None, Header(alias="Authorization", convert_underscores=False)
]
if TYPE_CHECKING:
    AuthProviderDep = IAuthenticationProvider
else:
    AuthProviderDep = Annotated[Any, Depends(get_authentication_provider)]


def _auth_exception(code: str, message: str, *, status_code: int = status.HTTP_401_UNAUTHORIZED) -> HTTPException:
    """Build an HTTPException with structured authentication error detail."""

    headers = {"WWW-Authenticate": "Bearer", "X-Error-Code": code}
    return HTTPException(status_code=status_code, detail={"code": code, "message": message}, headers=headers)


async def get_current_user(
    request: Request,
    auth_provider: AuthProviderDep,
    authorization: AuthHeader = None,
) -> AuthenticationResult:
    """Resolve and cache the authenticated user for the current request."""
    cached = getattr(request.state, "auth_result", None)
    if (
        isinstance(cached, AuthenticationResult)
        and cached.authenticated
        and cached.user_id is not None
    ):
        return cached

    if not authorization:
        raise _auth_exception("auth.header.missing", "Missing Authorization header")

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError as exc:
        raise _auth_exception("auth.header.invalid_format", "Invalid Authorization header format") from exc

    if scheme.lower() != "bearer":
        raise _auth_exception("auth.scheme.unsupported", "Unsupported authorization scheme")

    try:
        auth_result = await auth_provider.validate_token(token)
    except AuthenticationError as exc:
        raise _auth_exception(exc.code or "auth.token.invalid", str(exc)) from exc

    if not auth_result.authenticated or auth_result.user_id is None:
        raise _auth_exception("auth.token.unauthorized", "Invalid or unauthorized credentials")

    request.state.auth_result = auth_result
    return auth_result


def user_id_str(auth_result: AuthenticationResult) -> str | None:
    """Extract the user identifier as a string when available."""
    if auth_result.user_id is None:
        return None
    return str(auth_result.user_id)


__all__ = ["AuthHeader", "get_current_user", "user_id_str"]
