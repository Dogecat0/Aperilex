"""Google OAuth authentication provider implementation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import httpx
from jose import JWTError, jwt

from src.application.interfaces.authentication import (
    AuthenticationCredentials,
    AuthenticationError,
    AuthenticationResult,
    AuthorizationError,
    IAuthenticationProvider,
    RateLimitInfo,
)
from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.database import IDatabaseProvider
from src.application.interfaces.repositories import (
    AuthRateLimitData,
    AuthSessionData,
    IRepositoryFactory,
    UserData,
    UserIdentityData,
)
from src.application.interfaces.secret import ISecretManager
from src.shared.enums import UserStatus, UserTier
from src.shared.types import AuthSessionId, Email, UserId, UserIdentityId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from src.application.interfaces.repositories import (
        IAuthRateLimitRepository,
    )


@dataclass(slots=True)
class RateLimitSetting:
    """Configuration for a rate limited action."""

    action: str
    limit: int
    window_seconds: int


class GoogleJWKSCache:
    """Simple JWKS cache for Google public keys."""

    def __init__(self, jwks_uri: str, *, ttl_seconds: int = 3600) -> None:
        self._jwks_uri = jwks_uri
        self._ttl = ttl_seconds
        self._jwks: dict[str, Any] | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> dict[str, Any]:
        jwks = await self._get_keys()
        keys = jwks.get("keys", [])
        if not isinstance(keys, list):
            raise AuthenticationError(
                "Invalid JWKS payload received from Google",
                code="google.jwks.invalid",
            )
        for key in keys:
            if isinstance(key, dict) and key.get("kid") == kid:
                return cast(dict[str, Any], key)
        raise AuthenticationError(
            f"Unable to locate Google signing key with kid '{kid}'",
            code="google.jwks.missing",
        )

    async def _get_keys(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        if self._jwks is not None and self._expires_at and self._expires_at > now:
            return self._jwks

        async with self._lock:
            if self._jwks is not None and self._expires_at and self._expires_at > now:
                return self._jwks

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self._jwks_uri)
                response.raise_for_status()
                jwks_raw = response.json()
            if not isinstance(jwks_raw, dict):
                raise AuthenticationError(
                    "Invalid JWKS payload received from Google",
                    code="google.jwks.invalid",
                )
            jwks = cast(dict[str, Any], jwks_raw)

            cache_seconds = self._ttl
            control_header = response.headers.get("Cache-Control")
            if control_header:
                for part in control_header.split(","):
                    part = part.strip()
                    if part.startswith("max-age="):
                        try:
                            cache_seconds = int(part.split("=", 1)[1])
                        except ValueError:
                            cache_seconds = self._ttl
                        break

            self._jwks = jwks
            self._expires_at = now + timedelta(seconds=cache_seconds)
            return jwks


class GoogleOAuthAuthenticationProvider(IAuthenticationProvider):
    """Authentication provider backed by Google OAuth."""

    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"  # nosec B105
    JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
    GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

    def __init__(
        self,
        *,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
        database_provider: IDatabaseProvider,
    ) -> None:
        self._config_provider = config_provider
        self._secret_manager = secret_manager
        self._repository_factory: IRepositoryFactory = (
            database_provider.get_repository_factory()
        )

        self._access_token_ttl_seconds = self._config_provider.get_int(
            "authentication.access_token_ttl_seconds", 900
        )
        self._refresh_token_ttl_seconds = self._config_provider.get_int(
            "authentication.refresh_token_ttl_seconds", 1209600
        )
        self._jwt_algorithm = self._config_provider.get_string(
            "authentication.jwt_algorithm", "RS256"
        )
        self._jwt_issuer = self._config_provider.get_string(
            "authentication.jwt_issuer", "https://api.aperilex.local"
        )
        self._jwt_audience = self._config_provider.get_string(
            "authentication.jwt_audience", "aperilex"
        )
        default_tier = self._config_provider.get_string(
            "authentication.default_user_tier", UserTier.ESSENTIAL.value
        )
        self._default_user_tier = UserTier(default_tier)

        self._login_rate_limit = RateLimitSetting(
            action="LOGIN",
            limit=self._config_provider.get_int(
                "authentication.rate_limits.login.limit", 8
            ),
            window_seconds=self._config_provider.get_int(
                "authentication.rate_limits.login.window_seconds", 300
            ),
        )
        self._refresh_rate_limit = RateLimitSetting(
            action="REFRESH",
            limit=self._config_provider.get_int(
                "authentication.rate_limits.refresh.limit", 30
            ),
            window_seconds=self._config_provider.get_int(
                "authentication.rate_limits.refresh.window_seconds", 120
            ),
        )
        self._request_rate_limit = RateLimitSetting(
            action="REQUEST",
            limit=self._config_provider.get_int(
                "authentication.rate_limits.request.limit", 600
            ),
            window_seconds=self._config_provider.get_int(
                "authentication.rate_limits.request.window_seconds", 300
            ),
        )

        redirect_default = "http://localhost:3000/auth/google/callback"
        self._default_redirect_uri = self._config_provider.get_string(
            "authentication.google.redirect_uri", redirect_default
        )

        self._jwks_cache = GoogleJWKSCache(self.JWKS_URI)

        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._jwt_private_key: str | None = None
        self._jwt_public_key: str | None = None
        self._jwt_key_id = self._config_provider.get_string(
            "authentication.jwt_key_id", "aperilex-default"
        )

        self._client_lock = asyncio.Lock()
        self._jwt_key_lock = asyncio.Lock()

    async def authenticate(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """Exchange an authorization code for Aperilex tokens."""
        if not credentials.token:
            raise AuthenticationError(
                "Authorization code is required",
                code="auth.code.missing",
            )

        redirect_uri = credentials.redirect_uri or self._default_redirect_uri
        token_response = await self._exchange_code_for_tokens(
            code=credentials.token,
            redirect_uri=redirect_uri,
            code_verifier=credentials.code_verifier,
        )

        id_token = token_response.get("id_token")
        google_access_token = token_response.get("access_token")
        if not id_token:
            raise AuthenticationError(
                "Google token response missing id_token",
                code="google.idtoken.missing",
            )

        id_payload = await self._validate_google_id_token(
            id_token, access_token=google_access_token
        )
        email = id_payload.get("email")
        email_verified = id_payload.get("email_verified", False)
        subject = id_payload.get("sub")

        if not email or not isinstance(email, str):
            raise AuthenticationError(
                "Google account did not return an email address",
                code="google.email.missing",
            )
        if not email_verified:
            raise AuthenticationError(
                "Google account email is not verified",
                code="google.email.unverified",
            )
        if not subject or not isinstance(subject, str):
            raise AuthenticationError(
                "Google account is missing a stable subject identifier",
                code="google.subject.missing",
            )

        user, identity = await self._ensure_user(subject, email, id_payload)

        await self._enforce_rate_limit(user.id, self._login_rate_limit)

        issued_at = datetime.now(UTC)
        access_token = await self._issue_access_token(
            user_id=user.id,
            email=user.email,
            tier=user.tier,
            permissions=self._permissions_for_tier(user.tier),
            issued_at=issued_at,
        )
        refresh_token, refresh_hash = self._generate_refresh_token()

        await self._persist_auth_session(
            user=user,
            refresh_hash=refresh_hash,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=self._refresh_token_ttl_seconds),
            metadata={
                "google_sub": subject,
                "google_iss": id_payload.get("iss"),
            },
        )

        return AuthenticationResult(
            authenticated=True,
            user_id=user.id,
            user_email=str(user.email),
            user_tier=user.tier.value,
            permissions=self._permissions_for_tier(user.tier),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_token_ttl_seconds,
            refresh_expires_in=self._refresh_token_ttl_seconds,
            issued_at=issued_at.isoformat(),
            error_message=None,
        )

    async def authorize(self, user_id: UserId, resource: str, action: str) -> bool:
        permissions = set(await self._permissions_for_user(user_id))
        if not permissions:
            return False
        target = f"{resource}:{action}"
        return (
            target in permissions
            or f"{resource}:*" in permissions
            or "*:*" in permissions
        )

    async def validate_token(self, token: str) -> AuthenticationResult:
        payload = await self._decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError(
                "Access token missing subject",
                code="token.subject.missing",
            )

        try:
            user_id = UserId(UUID(user_id_str))
        except ValueError as exc:
            raise AuthenticationError(
                "Access token subject is not a valid UUID",
                code="token.subject.invalid",
            ) from exc

        user = await self._get_user(user_id)
        permissions = self._permissions_for_tier(user.tier)

        issued_at_raw = payload.get("iat")
        if isinstance(issued_at_raw, (int | float)):
            issued_at_value = datetime.fromtimestamp(issued_at_raw, tz=UTC).isoformat()
        elif isinstance(issued_at_raw, str):
            issued_at_value = issued_at_raw
        else:
            issued_at_value = None

        return AuthenticationResult(
            authenticated=True,
            user_id=user.id,
            user_email=str(user.email),
            user_tier=user.tier.value,
            permissions=permissions,
            access_token=None,
            refresh_token=None,
            expires_in=None,
            refresh_expires_in=None,
            issued_at=issued_at_value,
            error_message=None,
        )

    async def refresh_token(self, refresh_token: str) -> AuthenticationCredentials:
        if not refresh_token:
            raise AuthenticationError(
                "Refresh token is required",
                code="refresh.missing",
            )

        hashed = self._hash_refresh_token(refresh_token)
        factory = self._repository_factory
        session_repo = await factory.get_auth_session_repository()
        session = await session_repo.get_by_refresh_token_hash(hashed)
        await factory.close(success=True)

        if session is None:
            raise AuthenticationError(
                "Refresh token not recognized",
                code="refresh.unknown",
            )

        if session.revoked_at is not None:
            raise AuthenticationError(
                "Refresh token has been revoked",
                code="refresh.revoked",
            )

        now = datetime.now(UTC)
        if session.expires_at <= now:
            raise AuthenticationError(
                "Refresh token has expired",
                code="refresh.expired",
            )

        if (
            session.previous_refresh_token_hash is not None
            and session.previous_refresh_token_hash == hashed
        ):
            await self._revoke_session(session.id, reason="ROTATED_TOKEN_REUSE")
            raise AuthenticationError(
                "Refresh token reuse detected; session revoked",
                code="refresh.reused",
            )

        await self._enforce_rate_limit(session.user_id, self._refresh_rate_limit)

        user = await self._get_user(session.user_id)
        issued_at = datetime.now(UTC)
        access_token = await self._issue_access_token(
            user_id=user.id,
            email=user.email,
            tier=user.tier,
            permissions=self._permissions_for_tier(user.tier),
            issued_at=issued_at,
        )
        new_refresh_token, new_hash = self._generate_refresh_token()

        factory = self._repository_factory
        session_repo = await factory.get_auth_session_repository()
        await session_repo.rotate_refresh_token(
            session_id=session.id,
            refresh_token_hash=new_hash,
            expires_at=issued_at + timedelta(seconds=self._refresh_token_ttl_seconds),
            previous_hash=hashed,
            rotation_time=issued_at,
        )
        await factory.close(success=True)

        return AuthenticationCredentials(
            token=access_token,
            token_type="Bearer",  # nosec B106 - OAuth bearer token type constant
            refresh_token=new_refresh_token,
            expires_in=self._access_token_ttl_seconds,
            refresh_expires_in=self._refresh_token_ttl_seconds,
            issued_at=issued_at.isoformat(),
        )

    async def revoke_token(self, token: str) -> bool:
        if not token:
            return False
        hashed = self._hash_refresh_token(token)
        factory = self._repository_factory
        session_repo = await factory.get_auth_session_repository()
        session = await session_repo.get_by_refresh_token_hash(hashed)
        if session is None:
            await factory.close(success=True)
            return False

        now = datetime.now(UTC)
        result = await session_repo.mark_revoked(
            session.id, revoked_at=now, reason=None
        )
        await factory.close(success=True)
        return result

    async def get_rate_limit(self, user_id: UserId) -> RateLimitInfo:
        entry = await self._get_rate_limit_entry(user_id, self._request_rate_limit)
        limit = self._request_rate_limit.limit
        window_seconds = self._request_rate_limit.window_seconds
        if entry is None:
            now = datetime.now(UTC)
            reset_at = (now + timedelta(seconds=window_seconds)).isoformat()
            return RateLimitInfo(
                limit=limit,
                remaining=limit,
                reset_at=reset_at,
                window_seconds=window_seconds,
            )

        remaining = max(0, limit - entry.count)
        reset_at = (
            entry.window_start + timedelta(seconds=entry.window_seconds)
        ).isoformat()
        return RateLimitInfo(
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            window_seconds=entry.window_seconds,
        )

    async def check_rate_limit(self, user_id: UserId, increment: bool = True) -> bool:
        if increment:
            _, allowed = await self._update_rate_limit(
                user_id, self._request_rate_limit, increment=True
            )
            return allowed

        entry = await self._get_rate_limit_entry(user_id, self._request_rate_limit)
        if entry is None:
            return True
        return entry.count < self._request_rate_limit.limit

    async def health_check(self) -> bool:
        # Basic health check ensures secrets are present and JWT keys loadable
        await self._ensure_google_client()
        await self._ensure_jwt_keys()
        return True

    async def _exchange_code_for_tokens(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str | None,
    ) -> dict[str, Any]:
        payload = {
            "code": code,
            "client_id": await self._ensure_google_client(),
            "client_secret": await self._ensure_google_secret(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.TOKEN_ENDPOINT,
                    data=payload,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_detail: str | None = None
            try:
                body = exc.response.json()
                error_reason = body.get("error_description") or body.get("error")
                if error_reason:
                    error_detail = str(error_reason)
                else:
                    error_detail = json.dumps(body)
            except Exception:  # noqa: BLE001 - best effort logging only
                error_detail = exc.response.text

            logger.error(
                "Google token exchange failed (status %s): %s",
                exc.response.status_code,
                error_detail,
            )

            message = "Failed to exchange authorization code with Google"
            if error_detail:
                message = f"{message}: {error_detail}"

            raise AuthenticationError(message, code="google.exchange.failed") from exc
        except httpx.HTTPError as exc:
            logger.error("Google token exchange failed: %s", exc)
            raise AuthenticationError(
                "Failed to exchange authorization code with Google",
                code="google.exchange.failed",
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise AuthenticationError(
                "Unexpected response from Google token endpoint",
                code="google.exchange.invalid_response",
            )
        return cast(dict[str, Any], payload)

    async def _validate_google_id_token(
        self, token: str, *, access_token: str | None = None
    ) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthenticationError(
                "Unable to parse Google ID token header",
                code="google.idtoken.header",
            ) from exc

        kid = header.get("kid")
        if not kid:
            raise AuthenticationError(
                "Google ID token missing key identifier",
                code="google.idtoken.kid",
            )

        key = await self._jwks_cache.get_key(kid)
        audience = await self._ensure_google_client()

        decode_kwargs: dict[str, Any] = {
            "audience": audience,
            "issuer": self.GOOGLE_ISSUERS,
            "algorithms": ["RS256"],
        }
        if access_token:
            decode_kwargs["access_token"] = access_token

        try:
            payload_mapping = jwt.decode(
                token,
                key,
                **decode_kwargs,
            )
        except JWTError as exc:
            logger.warning("Google ID token validation failed: %s", exc)
            raise AuthenticationError(
                "Google ID token validation failed",
                code="google.idtoken.invalid",
            ) from exc

        return dict(payload_mapping)

    async def _ensure_user(
        self,
        provider_subject: str,
        email: str,
        payload: dict[str, Any],
    ) -> tuple[UserData, UserIdentityData]:
        factory = self._repository_factory
        await factory.begin_transaction()
        committed = False
        try:
            user_repo = await factory.get_user_repository()
            identity_repo = await factory.get_user_identity_repository()

            identity = await identity_repo.get_by_provider_subject(
                "GOOGLE", provider_subject
            )

            if identity:
                user = await user_repo.get_by_id(identity.user_id)
                if not user:
                    raise AuthenticationError(
                        "User record missing for Google identity",
                        code="user.missing",
                    )
                if str(user.email).lower() != email.lower():
                    user.email = Email(value=email)
                    user = await user_repo.update(user)
                profile = identity
            else:
                user = await user_repo.create(
                    UserData(
                        id=UserId(uuid4()),
                        email=Email(value=email),
                        status=UserStatus.ACTIVE,
                        tier=self._default_user_tier,
                    )
                )
                profile = await identity_repo.create(
                    UserIdentityData(
                        id=UserIdentityId(uuid4()),
                        user_id=user.id,
                        provider="GOOGLE",
                        provider_subject=provider_subject,
                        provider_email=Email(value=email),
                        raw_profile=payload,
                        verified_at=datetime.now(UTC),
                    )
                )

            await factory.commit_transaction()
            committed = True
            return user, profile
        except Exception:
            if not committed:
                try:
                    await factory.rollback_transaction()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Failed to rollback user provisioning: %s", exc)
            raise
        finally:
            await factory.close(success=committed)

    async def _persist_auth_session(
        self,
        *,
        user: UserData,
        refresh_hash: str,
        issued_at: datetime,
        expires_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        factory = self._repository_factory
        session_repo = await factory.get_auth_session_repository()
        await session_repo.create(
            AuthSessionData(
                id=AuthSessionId(uuid4()),
                user_id=user.id,
                refresh_token_hash=refresh_hash,
                previous_refresh_token_hash=None,
                session_key=None,
                user_agent=None,
                ip_address=None,
                issued_at=issued_at,
                expires_at=expires_at,
                last_refreshed_at=None,
                revoked_at=None,
                revoked_reason=None,
                metadata=metadata,
            )
        )
        await factory.close(success=True)

    async def _revoke_session(
        self,
        session_id: AuthSessionId,
        *,
        reason: str | None,
    ) -> None:
        factory = self._repository_factory
        session_repo = await factory.get_auth_session_repository()
        await session_repo.mark_revoked(
            session_id=session_id,
            revoked_at=datetime.now(UTC),
            reason=reason,
        )
        await factory.close(success=True)

    async def _issue_access_token(
        self,
        *,
        user_id: UserId,
        email: Email,
        tier: UserTier,
        permissions: list[str],
        issued_at: datetime,
    ) -> str:
        await self._ensure_jwt_keys()
        assert self._jwt_private_key is not None  # nosec - ensured above

        payload = {
            "iss": self._jwt_issuer,
            "aud": self._jwt_audience,
            "sub": str(user_id),
            "email": str(email),
            "tier": tier.value,
            "permissions": permissions,
            "iat": int(issued_at.timestamp()),
            "exp": int(
                (
                    issued_at + timedelta(seconds=self._access_token_ttl_seconds)
                ).timestamp()
            ),
            "token_type": "access",
            "jti": str(uuid4()),
        }

        headers = {"kid": self._jwt_key_id}
        try:
            encoded = jwt.encode(
                payload,
                self._jwt_private_key,
                algorithm=self._jwt_algorithm,
                headers=headers,
            )
        except JWTError as exc:
            raise AuthenticationError(
                "Failed to sign access token",
                code="token.issue.failed",
            ) from exc

        return encoded

    async def _decode_access_token(self, token: str) -> dict[str, Any]:
        await self._ensure_jwt_keys()
        assert self._jwt_public_key is not None  # nosec - ensured above

        try:
            payload_mapping = jwt.decode(
                token,
                self._jwt_public_key,
                algorithms=[self._jwt_algorithm],
                audience=self._jwt_audience,
                issuer=self._jwt_issuer,
            )
        except JWTError as exc:
            raise AuthenticationError(
                "Access token validation failed",
                code="token.invalid",
            ) from exc

        payload = dict(payload_mapping)

        if payload.get("token_type") != "access":
            raise AuthenticationError(
                "Token type is not access",
                code="token.type.invalid",
            )

        return payload

    async def _permissions_for_user(self, user_id: UserId) -> list[str]:
        user = await self._get_user(user_id)
        return self._permissions_for_tier(user.tier)

    def _permissions_for_tier(self, tier: UserTier) -> list[str]:
        mapping: dict[UserTier, list[str]] = {
            UserTier.ESSENTIAL: ["analysis:read", "analysis:submit"],
            UserTier.PLUS: ["analysis:read", "analysis:submit", "queue:priority"],
        }
        try:
            base = mapping[tier]
        except KeyError as exc:
            raise AuthenticationError(
                f"Unknown user tier '{tier}'",
                code="auth.tier.invalid",
            ) from exc
        return list(base)

    async def _ensure_google_client(self) -> str:
        if self._client_id is not None:
            return self._client_id
        async with self._client_lock:
            if self._client_id is None:
                secret = await self._secret_manager.get_secret("GOOGLE_CLIENT_ID")
                self._client_id = secret.strip()
        return self._client_id

    async def _ensure_google_secret(self) -> str:
        if self._client_secret is not None:
            return self._client_secret
        async with self._client_lock:
            if self._client_secret is None:
                secret = await self._secret_manager.get_secret("GOOGLE_CLIENT_SECRET")
                self._client_secret = secret.strip()
        return self._client_secret

    async def _ensure_jwt_keys(self) -> None:
        if self._jwt_private_key and self._jwt_public_key:
            return
        async with self._jwt_key_lock:
            if self._jwt_private_key and self._jwt_public_key:
                return
            private_key = await self._secret_manager.get_secret("JWT_PRIVATE_KEY")
            public_key = await self._secret_manager.get_secret("JWT_PUBLIC_KEY")
            self._jwt_private_key = private_key.strip()
            self._jwt_public_key = public_key.strip()

    async def _get_user(self, user_id: UserId) -> UserData:
        factory = self._repository_factory
        user_repo = await factory.get_user_repository()
        user = await user_repo.get_by_id(user_id)
        await factory.close(success=True)
        if user is None:
            raise AuthenticationError(
                "User record not found",
                code="user.missing",
            )
        if user.status != UserStatus.ACTIVE:
            raise AuthorizationError(
                "User account is not active",
                resource="user",
                action="access",
            )
        return user

    async def _enforce_rate_limit(
        self, user_id: UserId, setting: RateLimitSetting
    ) -> None:
        _, allowed = await self._update_rate_limit(user_id, setting, increment=True)
        if not allowed:
            raise AuthenticationError(
                "Rate limit exceeded",
                code=f"rate_limit.{setting.action.lower()}",
            )

    async def _get_rate_limit_entry(
        self, user_id: UserId, setting: RateLimitSetting
    ) -> AuthRateLimitData | None:
        factory = self._repository_factory
        repo = await factory.get_auth_rate_limit_repository()
        entry = await repo.get_current(
            self._rate_limit_key(user_id, setting.action),
            setting.action,
        )
        await factory.close(success=True)
        return entry

    async def _update_rate_limit(
        self,
        user_id: UserId,
        setting: RateLimitSetting,
        *,
        increment: bool,
    ) -> tuple[AuthRateLimitData | None, bool]:
        factory = self._repository_factory
        repo: IAuthRateLimitRepository = await factory.get_auth_rate_limit_repository()
        entry: AuthRateLimitData | None
        if increment:
            entry, allowed = await repo.increment_and_get(
                key=self._rate_limit_key(user_id, setting.action),
                action=setting.action,
                user_id=user_id,
                window_seconds=setting.window_seconds,
                limit=setting.limit,
                now=datetime.now(UTC),
            )
        else:
            entry = await repo.get_current(
                self._rate_limit_key(user_id, setting.action),
                setting.action,
            )
            allowed = True if entry is None else entry.count < setting.limit
        await factory.close(success=True)
        return entry, allowed

    def _rate_limit_key(self, user_id: UserId, action: str) -> str:
        return f"user:{user_id}:{action}"

    def _generate_refresh_token(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(64)
        return token, self._hash_refresh_token(token)

    @staticmethod
    def _hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
