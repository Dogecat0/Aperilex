"""Worker provider implementations and optional loaders."""

from __future__ import annotations

from src.application.interfaces.worker import IWorkerProvider


def load_lambda_worker_provider() -> type[IWorkerProvider]:
    """Load the Lambda worker provider implementation if available."""

    from .lambda_provider import LambdaWorkerProvider

    return LambdaWorkerProvider


def load_docker_worker_provider() -> type[IWorkerProvider]:
    """Load the Docker worker provider implementation if available."""

    from .docker import DockerWorkerProvider

    return DockerWorkerProvider


__all__ = [
    "load_docker_worker_provider",
    "load_lambda_worker_provider",
]
