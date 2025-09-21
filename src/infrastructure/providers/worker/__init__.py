"""Worker provider implementations."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from .lambda_provider import LambdaWorkerProvider
except ModuleNotFoundError:
    LambdaWorkerProvider = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from .docker import DockerWorkerProvider
except ModuleNotFoundError:
    DockerWorkerProvider = None  # type: ignore[assignment]

__all__ = [
    "DockerWorkerProvider",
    "LambdaWorkerProvider",
]
