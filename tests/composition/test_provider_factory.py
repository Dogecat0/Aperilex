"""Tests for ProviderFactory wiring and error handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.composition.provider_factory import ProviderFactory
from src.shared.config.settings import settings
from src.shared.enums import QueueProvider, WorkerProvider


class _StubConfigProvider:
    def get(self, _key: str, default: object | None = None) -> object | None:
        return default


class _StubSecretManager:
    pass


def test_create_secret_manager_requires_docker_secrets_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "docker_secrets_dir", "")

    with pytest.raises(RuntimeError, match="DOCKER_SECRETS_DIR must be set"):
        ProviderFactory.create_secret_manager("development")


def test_create_secret_manager_development_uses_docker_secret_manager(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from src.infrastructure.secret import DockerSecretManager

    monkeypatch.setattr(settings, "docker_secrets_dir", str(tmp_path))

    secret_manager_provider = ProviderFactory.create_secret_manager("development")

    secret_manager = secret_manager_provider()
    assert isinstance(secret_manager, DockerSecretManager)


def test_create_secret_manager_production_uses_aws_secrets_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.infrastructure.secret import AWSSecretsManager

    monkeypatch.setattr(settings, "aws_region", "us-east-1")

    secret_manager_provider = ProviderFactory.create_secret_manager("production")

    assert secret_manager_provider.provides is AWSSecretsManager
    assert secret_manager_provider.kwargs["region_name"] == "us-east-1"


def test_create_queue_provider_sqs_requires_aioboto3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.infrastructure.providers import queue as queue_module

    def _missing() -> object:
        raise ModuleNotFoundError("aioboto3")

    monkeypatch.setattr(queue_module, "load_sqs_queue_provider", _missing)

    with pytest.raises(RuntimeError, match="aioboto3") as exc:
        ProviderFactory.create_queue_provider(
            QueueProvider.SQS,
            _StubConfigProvider(),
            _StubSecretManager(),
        )

    assert isinstance(exc.value.__cause__, ModuleNotFoundError)


@pytest.mark.asyncio
async def test_create_worker_provider_lambda_requires_aioboto3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.infrastructure.providers import worker as worker_module

    def _missing() -> object:
        raise ModuleNotFoundError("aioboto3")

    monkeypatch.setattr(worker_module, "load_lambda_worker_provider", _missing)

    worker_provider = ProviderFactory.create_worker_provider(
        WorkerProvider.LAMBDA,
        _StubConfigProvider(),
        _StubSecretManager(),
    )

    worker = worker_provider()
    with pytest.raises(RuntimeError, match="optional 'aioboto3' dependency"):
        await worker.health_check()


@pytest.mark.asyncio
async def test_create_worker_provider_docker_requires_aiodocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.infrastructure.providers import worker as worker_module

    def _missing() -> object:
        raise ModuleNotFoundError("aiodocker")

    monkeypatch.setattr(worker_module, "load_docker_worker_provider", _missing)

    worker_provider = ProviderFactory.create_worker_provider(
        WorkerProvider.DOCKER,
        _StubConfigProvider(),
        _StubSecretManager(),
    )

    worker = worker_provider()
    with pytest.raises(RuntimeError, match="optional 'aiodocker' dependency"):
        await worker.health_check()

