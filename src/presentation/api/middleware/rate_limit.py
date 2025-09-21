"""Rate limiting middleware that integrates with the DI-backed providers."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.application.containers.orchestrator import ApiRateLimiter
from src.application.interfaces.authentication import (
    AuthenticationResult,
    IAuthenticationProvider,
)
from src.shared.config.settings import settings
from src.shared.types import UserId

from ..dependencies import get_authentication_provider, get_rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for enforcing rate limits using DI providers."""

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: ApiRateLimiter | None = None,
        auth_provider: IAuthenticationProvider | None = None,
        excluded_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter
        self._auth_provider = auth_provider
        self.excluded_paths = (
            excluded_paths
            if excluded_paths is not None
            else settings.rate_limit_excluded_paths
        )

        logger.info(
            "RateLimitMiddleware initialized",
            extra={
                "enabled": settings.rate_limiting_enabled,
                "excluded_paths": self.excluded_paths,
            },
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not settings.rate_limiting_enabled:
            return await call_next(request)

        if self._is_path_excluded(request.url.path):
            return await call_next(request)

        rate_limiter = await self._resolve_rate_limiter()
        if rate_limiter is None or rate_limiter.provider is None:
            return await call_next(request)

        client_id = self._extract_client_id(request)
        user_id = await self._resolve_user_id(request)
        resource = request.url.path

        try:
            result = await rate_limiter.check_rate_limit(
                client_id=client_id,
                resource=resource,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001 - continue processing on failure
            logger.error(
                "Rate limit evaluation failed; continuing without enforcement",
                exc_info=True,
                extra={"client_id": client_id, "resource": resource, "error": str(exc)},
            )
            return await call_next(request)

        headers = await rate_limiter.get_rate_limit_headers(result)

        if result is not None and not result.allowed:
            error_payload = {
                "error": {
                    "message": "Rate limit exceeded",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "path": resource,
                    "details": {
                        "limit_type": result.limit_type,
                        "hourly_limit": result.hourly_limit,
                        "daily_limit": result.daily_limit,
                        "current_hourly_count": result.current_hourly_count,
                        "current_daily_count": result.current_daily_count,
                        "retry_after_seconds": result.retry_after_seconds,
                    },
                }
            }

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_payload,
                headers=headers,
            )

        response = await call_next(request)
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        return response

    def _is_path_excluded(self, path: str | None) -> bool:
        if path is None or not self.excluded_paths:
            return False

        normalized_path = path.rstrip("/")
        for excluded in self.excluded_paths:
            normalized_excluded = excluded.rstrip("/")
            if normalized_path == normalized_excluded or path.startswith(
                normalized_excluded + "/"
            ):
                return True
        return False

    async def _resolve_rate_limiter(self) -> ApiRateLimiter | None:
        if self._rate_limiter is not None:
            return self._rate_limiter

        try:
            self._rate_limiter = await get_rate_limiter()
        except Exception as exc:  # noqa: BLE001 - log and disable rate limiting
            logger.error("Unable to resolve rate limiter from DI", exc_info=True)
            logger.debug("Rate limiter resolution failure: %s", exc)
            self._rate_limiter = None
        return self._rate_limiter

    async def _resolve_auth_provider(self) -> IAuthenticationProvider | None:
        if self._auth_provider is not None:
            return self._auth_provider

        try:
            self._auth_provider = await get_authentication_provider()
        except Exception:
            logger.debug("Authentication provider not available for rate limiting", exc_info=True)
            self._auth_provider = None
        return self._auth_provider

    async def _resolve_user_id(self, request: Request) -> UserId | None:
        cached = getattr(request.state, "auth_result", None)
        if self._is_authenticated_result(cached):
            return cached.user_id

        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        try:
            scheme, token = authorization.split(" ", 1)
        except ValueError:
            return None

        if scheme.lower() != "bearer":
            return None

        auth_provider = await self._resolve_auth_provider()
        if auth_provider is None:
            return None

        try:
            auth_result = await auth_provider.validate_token(token)
        except Exception:
            logger.debug("Token validation failed during rate limiting", exc_info=True)
            return None

        if self._is_authenticated_result(auth_result):
            request.state.auth_result = auth_result
            return auth_result.user_id

        return None

    @staticmethod
    def _is_authenticated_result(result: Any) -> bool:
        return (
            isinstance(result, AuthenticationResult)
            and result.authenticated
            and result.user_id is not None
        )

    @staticmethod
    def _extract_client_id(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        if request.client and request.client.host:
            return request.client.host

        return "unknown-client"

    async def cleanup_expired_clients(self, max_idle_time: int = 86400) -> int:
        rate_limiter = await self._resolve_rate_limiter()
        if rate_limiter is None:
            return 0
        return await rate_limiter.cleanup_expired_clients(max_idle_time)

    async def get_rate_limiter_stats(self) -> dict[str, int]:
        rate_limiter = await self._resolve_rate_limiter()
        if rate_limiter is None:
            return {}
        return await rate_limiter.get_stats()
