"""Security helpers for FastAPI presentation layer.

Provides request-scoped authentication utilities that leverage the
application-level authentication provider through dependency injection.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from src.application.interfaces.authentication import (
    AuthenticationResult,
    IAuthenticationProvider,
)
from src.presentation.api.dependencies import get_authentication_provider

AuthHeader = Annotated[
    str | None, Header(alias="Authorization", convert_underscores=False)
]


async def get_current_user(
    request: Request,
    authorization: AuthHeader,
    auth_provider: IAuthenticationProvider = Depends(get_authentication_provider),
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authorization scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_result = await auth_provider.validate_token(token)

    if not auth_result.authenticated or auth_result.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.auth_result = auth_result
    return auth_result


def user_id_str(auth_result: AuthenticationResult) -> str | None:
    """Extract the user identifier as a string when available."""
    if auth_result.user_id is None:
        return None
    return str(auth_result.user_id)


__all__ = ["AuthHeader", "get_current_user", "user_id_str"]
