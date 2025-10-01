"""Authentication session endpoints for FastAPI surface."""

from __future__ import annotations

import base64
import hashlib
import secrets
from enum import Enum
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.application.interfaces.authentication import (
    AuthenticationCredentials,
    AuthenticationError,
    AuthenticationResult,
    IAuthenticationProvider,
)
from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.secret import ISecretManager
from src.presentation.api.dependencies import (
    get_authentication_provider,
    get_config_provider,
    get_secret_manager,
)
from src.shared.config.settings import settings
from src.shared.utils.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_LOGIN_SCOPE = "openid email profile"
STATE_COOKIE = "aperilex_oauth_state"
VERIFIER_COOKIE = "aperilex_pkce_verifier"
REDIRECT_COOKIE = "aperilex_post_auth_redirect"
REFRESH_COOKIE = "aperilex_refresh_token"
STATE_TTL_SECONDS = 600
REDIRECT_TTL_SECONDS = 900

logger = get_logger(__name__)


class OAuthTokenType(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    BEARER = "Bearer"

AuthProviderDep = Annotated[IAuthenticationProvider, Depends(get_authentication_provider)]
ConfigProviderDep = Annotated[IConfigProvider, Depends(get_config_provider)]
SecretManagerDep = Annotated[ISecretManager, Depends(get_secret_manager)]


class AuthenticatedUserPayload(BaseModel):
    """Payload describing the authenticated user."""

    id: str = Field(..., description="User identifier")
    email: str = Field(..., description="Verified email address")
    tier: str | None = Field(
        default=None,
        description="User subscription tier (BASIC, PROFESSIONAL, etc.)",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Granted permission codes",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AuthSessionResponse(BaseModel):
    """Response returned after login/refresh operations."""

    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(OAuthTokenType.BEARER, alias="tokenType")
    expires_in: int | None = Field(None, alias="expiresIn")
    refresh_expires_in: int | None = Field(None, alias="refreshExpiresIn")
    issued_at: str | None = Field(None, alias="issuedAt")
    user: AuthenticatedUserPayload
    redirect_to: str | None = Field(
        default=None,
        alias="redirectTo",
        description="Client redirect hint preserved from login flow",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GoogleCallbackRequest(BaseModel):
    """Request payload for exchanging Google OAuth authorization codes."""

    code: str = Field(..., description="Google OAuth authorization code")
    state: str = Field(..., description="Opaque state returned by Google")
    redirect_uri: str | None = Field(
        default=None,
        alias="redirectUri",
        description="Optional client redirect override",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("code", "state")
    @classmethod
    def _ensure_non_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Value cannot be empty")
        return trimmed

    @field_validator("redirect_uri")
    @classmethod
    def _normalize_redirect(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


def _should_use_secure_cookies() -> bool:
    env = settings.environment.lower()
    return env not in {"development", "local", "test", "testing"}


def _set_cookie(
    response: Response,
    name: str,
    value: str,
    *,
    max_age: int | None = None,
    http_only: bool = True,
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        expires=None if max_age is None else int(max_age),
        path="/api",
        secure=_should_use_secure_cookies(),
        httponly=http_only,
        samesite="lax",
    )


def _clear_cookie(response: Response, name: str) -> None:
    response.delete_cookie(name, path="/api")


def _build_code_verifier() -> str:
    # RFC 7636 mandates verifier length between 43 and 128 chars.
    return secrets.token_urlsafe(64)[:128]


def _build_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


async def _get_google_client_id(secret_manager: ISecretManager) -> str:
    secret = await secret_manager.get_secret("GOOGLE_CLIENT_ID")
    client_id = secret.strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "auth.google.missing_client_id",
                "message": "Google client ID secret is not configured",
            },
        )
    return client_id


def _auth_error_detail(code: str, message: str, *, info: dict[str, str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"code": code, "message": message}
    if info:
        payload.update(info)
    return payload


def _build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str,
    access_type: str = "offline",
    prompt: str = "consent",
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "include_granted_scopes": "true",
        "access_type": access_type,
        "prompt": prompt,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


async def _build_login_redirect(
    *,
    secret_manager: ISecretManager,
    config_provider: IConfigProvider,
    redirect_hint: str | None,
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    verifier = _build_code_verifier()
    code_challenge = _build_code_challenge(verifier)
    client_id = await _get_google_client_id(secret_manager)

    redirect_uri = config_provider.get_string(
        "authentication.google.redirect_uri",
        default="http://localhost:3000/auth/google/callback",
    )
    scope = config_provider.get_string(
        "authentication.google.scope",
        default=DEFAULT_LOGIN_SCOPE,
    )
    access_type = config_provider.get_string(
        "authentication.google.access_type",
        default="offline",
    )
    prompt = config_provider.get_string(
        "authentication.google.prompt",
        default="consent",
    )

    auth_url = _build_authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=code_challenge,
        scope=scope,
        access_type=access_type,
        prompt=prompt,
    )

    response = RedirectResponse(
        url=auth_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    _set_cookie(response, STATE_COOKIE, state, max_age=STATE_TTL_SECONDS, http_only=True)
    _set_cookie(response, VERIFIER_COOKIE, verifier, max_age=STATE_TTL_SECONDS, http_only=True)
    if redirect_hint:
        _set_cookie(
            response,
            REDIRECT_COOKIE,
            redirect_hint,
            max_age=REDIRECT_TTL_SECONDS,
            http_only=False,
        )
    return response


def _resolve_redirect_hint(raw: str | None) -> str | None:
    if not raw:
        return None
    hint = raw.strip()
    if not hint:
        return None
    if len(hint) > 2048:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_auth_error_detail(
                "auth.redirect.too_long",
                "Redirect hint exceeds maximum length",
            ),
        )
    return hint


@router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Initiate Google OAuth login",
)
async def login_with_google(
    secret_manager: SecretManagerDep,
    config_provider: ConfigProviderDep,
    redirect_to: Annotated[str | None, Query(alias="redirectTo")] = None,
) -> RedirectResponse:
    """Begin Google OAuth flow and redirect the user to the consent screen."""

    redirect_hint = _resolve_redirect_hint(redirect_to)
    return await _build_login_redirect(
        secret_manager=secret_manager,
        config_provider=config_provider,
        redirect_hint=redirect_hint,
    )


def _build_user_payload(result: AuthenticationResult) -> AuthenticatedUserPayload:
    if result.user_id is None or result.user_email is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_auth_error_detail(
                "auth.callback.missing_identity",
                "Authentication provider did not return user identity",
            ),
        )

    return AuthenticatedUserPayload(
        id=str(result.user_id),
        email=result.user_email,
        tier=result.user_tier,
        permissions=result.permissions or [],
    )


def _merge_redirect_hint(
    request: Request,
    payload: GoogleCallbackRequest,
) -> str | None:
    if payload.redirect_uri:
        return payload.redirect_uri
    cookie_hint = request.cookies.get(REDIRECT_COOKIE)
    if cookie_hint:
        return cookie_hint
    return None


def _set_refresh_cookie(
    response: Response,
    refresh_token: str,
    refresh_expires_in: int | None,
) -> None:
    max_age = None
    if refresh_expires_in is not None and refresh_expires_in > 0:
        max_age = min(refresh_expires_in, 60 * 60 * 24 * 30)
    _set_cookie(
        response,
        REFRESH_COOKIE,
        refresh_token,
        max_age=max_age,
        http_only=True,
    )


def _extract_refresh_token(request: Request) -> str | None:
    token = request.cookies.get(REFRESH_COOKIE)
    if token is None or not token.strip():
        return None
    return token.strip()


@router.post(
    "/google/callback",
    response_model=AuthSessionResponse,
    summary="Complete Google OAuth flow",
)
async def google_oauth_callback(
    payload: GoogleCallbackRequest,
    request: Request,
    response: Response,
    auth_provider: AuthProviderDep,
    config_provider: ConfigProviderDep,
) -> AuthSessionResponse:
    """Exchange Google authorization code for Aperilex session tokens."""

    state_cookie = request.cookies.get(STATE_COOKIE)
    if state_cookie is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_auth_error_detail(
                "auth.state.missing",
                "OAuth state cookie is missing or expired",
            ),
        )

    if payload.state != state_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_auth_error_detail(
                "auth.state.mismatch",
                "OAuth state does not match login request",
            ),
        )

    verifier = request.cookies.get(VERIFIER_COOKIE)
    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_auth_error_detail(
                "auth.pkce.missing",
                "PKCE code verifier is missing or expired",
            ),
        )

    redirect_uri = config_provider.get_string(
        "authentication.google.redirect_uri",
        default="http://localhost:3000/auth/google/callback",
    )

    credentials = AuthenticationCredentials(
        token=payload.code,
        token_type=OAuthTokenType.AUTHORIZATION_CODE,
        redirect_uri=redirect_uri,
        code_verifier=verifier,
    )

    try:
        result = await auth_provider.authenticate(credentials)
    except AuthenticationError as exc:
        logger.warning(
            "Google OAuth callback failed: code=%s message=%s",
            exc.code or "unknown",
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_auth_error_detail(
                exc.code or "auth.google.exchange_failed",
                str(exc),
            ),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not result.authenticated or result.refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_auth_error_detail(
                "auth.google.incomplete",
                "Authentication provider did not return session tokens",
            ),
        )

    _set_refresh_cookie(response, result.refresh_token, result.refresh_expires_in)
    _clear_cookie(response, STATE_COOKIE)
    _clear_cookie(response, VERIFIER_COOKIE)
    _clear_cookie(response, REDIRECT_COOKIE)

    redirect_hint = _merge_redirect_hint(request, payload)

    return AuthSessionResponse(
        access_token=result.access_token or "",
        token_type=OAuthTokenType.BEARER,
        expires_in=result.expires_in,
        refresh_expires_in=result.refresh_expires_in,
        issued_at=result.issued_at,
        user=_build_user_payload(result),
        redirect_to=redirect_hint,
    )


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    summary="Refresh access token",
)
async def refresh_session(
    request: Request,
    response: Response,
    auth_provider: AuthProviderDep,
) -> AuthSessionResponse:
    """Rotate refresh token and issue a new access token."""

    refresh_token = _extract_refresh_token(request)
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_auth_error_detail(
                "auth.refresh.missing_token",
                "Refresh token cookie is missing",
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        credentials = await auth_provider.refresh_token(refresh_token)
    except AuthenticationError as exc:
        _clear_cookie(response, REFRESH_COOKIE)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_auth_error_detail(
                exc.code or "auth.refresh.failed",
                str(exc),
            ),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not credentials.token or not credentials.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_auth_error_detail(
                "auth.refresh.incomplete",
                "Authentication provider returned incomplete credentials",
            ),
        )

    _set_refresh_cookie(response, credentials.refresh_token, credentials.refresh_expires_in)

    try:
        user_result = await auth_provider.validate_token(credentials.token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_auth_error_detail(
                exc.code or "auth.token.invalid",
                str(exc),
            ),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthSessionResponse(
        access_token=credentials.token,
        token_type=credentials.token_type or "Bearer",
        expires_in=credentials.expires_in,
        refresh_expires_in=credentials.refresh_expires_in,
        issued_at=credentials.issued_at,
        user=_build_user_payload(user_result),
        redirect_to=None,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke session",
    response_class=Response,
    response_model=None,
)
async def logout(
    request: Request,
    response: Response,
    auth_provider: AuthProviderDep,
) -> None:
    """Revoke the current refresh token and clear auth cookies."""

    refresh_token = _extract_refresh_token(request)
    if refresh_token:
        try:
            await auth_provider.revoke_token(refresh_token)
        except AuthenticationError:
            # Revocation failures are logged by the provider; continue clearing cookies.
            pass

    _clear_cookie(response, REFRESH_COOKIE)
    _clear_cookie(response, STATE_COOKIE)
    _clear_cookie(response, VERIFIER_COOKIE)
    _clear_cookie(response, REDIRECT_COOKIE)

    response.status_code = status.HTTP_204_NO_CONTENT
