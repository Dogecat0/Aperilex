from collections.abc import Mapping
from typing import Any

class JWTError(Exception): ...

class _JWTModule:
    def decode(
        self,
        token: str,
        key: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Mapping[str, Any]: ...

    def encode(
        self,
        claims: Mapping[str, Any],
        key: Any,
        *,
        algorithm: str,
        headers: Mapping[str, Any] | None = ...,
    ) -> str: ...

    def get_unverified_header(self, token: str) -> Mapping[str, Any]: ...

jwt: _JWTModule
