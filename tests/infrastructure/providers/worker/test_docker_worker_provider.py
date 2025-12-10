"""Contract tests for the DockerWorkerProvider with stubbed Docker client."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.application.interfaces.worker import WorkerContext, WorkerTaskStatus
from src.infrastructure.providers.worker.docker import DockerWorkerProvider
from src.shared.config.providers import DockerWorkerConfig
from src.shared.enums import TaskPriority, TaskStatus, WorkerProvider
from src.shared.models.queue import TaskMessage
from src.shared.types import CorrelationId, RequestId, TaskId


class FakeDockerError(Exception):
    pass


class StubContainer:
    def __init__(
        self,
        container_id: str,
        config: dict[str, Any],
        wait_result: Any,
        log_lines: list[str],
        state: dict[str, Any],
    ) -> None:
        self.id = container_id
        self.config = config
        self._wait_result = wait_result
        self._log_lines = log_lines
        self._state = state
        self.started = False
        self.killed = False

    async def start(self) -> None:
        self.started = True

    async def wait(self) -> Any:
        return self._wait_result

    async def kill(self) -> None:
        self.killed = True

    async def log(self, stdout: bool = True, stderr: bool = True) -> list[str]:
        _ = stdout
        _ = stderr
        return self._log_lines

    async def show(self) -> dict[str, Any]:
        return {"State": self._state}


class StubContainerManager:
    def __init__(
        self,
        wait_result: Any,
        log_lines: list[str],
        state: dict[str, Any] | None = None,
    ) -> None:
        self.wait_result = wait_result
        self.log_lines = log_lines
        self.state = state or {
            "Status": "exited",
            "ExitCode": 0,
            "StartedAt": "2024-01-01T00:00:00Z",
            "FinishedAt": "2024-01-01T00:01:00Z",
        }
        self.created_configs: list[dict[str, Any]] = []
        self.containers: dict[str, StubContainer] = {}

    async def create(self, **config: Any) -> StubContainer:
        container_id = f"container-{len(self.created_configs) + 1}"
        container = StubContainer(
            container_id,
            config,
            self.wait_result,
            self.log_lines,
            self.state,
        )
        self.created_configs.append(config)
        self.containers[container_id] = container
        return container

    async def get(self, container_id: str) -> StubContainer:
        return self.containers[container_id]


class StubNetworks:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists
        self.created: list[dict[str, Any]] = []
        self.get_calls: list[str] = []

    async def get(self, name: str) -> dict[str, str]:
        self.get_calls.append(name)
        if not self.exists:
            raise FakeDockerError("network missing")
        return {"Name": name}

    async def create(self, config: dict[str, Any]) -> dict[str, Any]:
        self.created.append(config)
        self.exists = True
        return config


class StubImages:
    def __init__(self, image_name: str, present: bool = True) -> None:
        self.image_name = image_name
        self.present = present
        self.list_calls = 0
        self.get_calls: list[str] = []

    async def list(self) -> list[dict[str, Any]]:
        self.list_calls += 1
        if self.present:
            return [{"RepoTags": [self.image_name]}]
        return []

    async def get(self, name: str) -> dict[str, Any]:
        self.get_calls.append(name)
        if self.present and name == self.image_name:
            return {"RepoTags": [name]}
        raise FakeDockerError("image missing")


class StubDockerClient:
    def __init__(
        self,
        *,
        image_name: str,
        image_present: bool = True,
        version_ok: bool = True,
        wait_result: Any = None,
        log_lines: list[str] | None = None,
        network_exists: bool = True,
        container_state: dict[str, Any] | None = None,
    ) -> None:
        self.networks = StubNetworks(exists=network_exists)
        self.images = StubImages(image_name=image_name, present=image_present)
        self.containers = StubContainerManager(
            wait_result or {"StatusCode": 0},
            log_lines or ['{"output_type":"text","output_data":{"ok":true}}'],
            state=container_state,
        )
        self.version_ok = version_ok
        self.closed = False
        self.pull_calls: list[str] = []

    async def version(self) -> dict[str, str]:
        if not self.version_ok:
            raise FakeDockerError("docker unavailable")
        return {"Version": "25.0"}

    async def pull(self, image: str) -> None:
        self.pull_calls.append(image)
        self.images.present = True

    async def close(self) -> None:
        self.closed = True


def _make_task_message(task_id: TaskId | None = None) -> TaskMessage:
    return TaskMessage(
        task_id=task_id or TaskId(uuid4()),
        task_type="analysis",
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        payload={"key": "value"},
        metadata=None,
        correlation_id=CorrelationId(str(uuid4())),
        created_at=datetime.utcnow(),
        scheduled_at=None,
        retry_count=0,
        max_retries=3,
        timeout_seconds=120,
    )


def _make_context(task_id: TaskId) -> WorkerContext:
    return WorkerContext(
        correlation_id=CorrelationId(str(uuid4())),
        task_id=task_id,
        request_id=RequestId(str(uuid4())),
        provider=WorkerProvider.DOCKER,
        start_time=datetime.utcnow(),
        timeout_seconds=60,
        retry_attempt=0,
        max_retries=2,
        log_level="DEBUG",
        metadata=None,
    )


async def _attach_stub_client(
    provider: DockerWorkerProvider, client: StubDockerClient
) -> StubDockerClient:
    async def _get_client() -> StubDockerClient:
        provider.docker_client = client
        return client

    provider._get_client = _get_client  # type: ignore[method-assign]
    return client


async def _drain_status_tasks(provider: DockerWorkerProvider) -> None:
    if provider._status_persist_tasks:
        pending = tuple(provider._status_persist_tasks)
        provider._status_persist_tasks.clear()
        await asyncio.gather(*pending, return_exceptions=True)


@pytest.mark.asyncio
async def test_execute_task_builds_container_config_and_records_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = DockerWorkerConfig(
        image_name="worker:123",
        container_prefix="worker",
        network_name="test-net",
        environment_vars={"BASE": "abc"},
        volume_mounts={str(tmp_path / "host"): "/app/data"},
        enable_gpu=True,
        status_store_path=str(tmp_path / "status"),
    )
    provider = DockerWorkerProvider(config)

    client = StubDockerClient(
        image_name=config.image_name,
        network_exists=False,
        log_lines=[
            '{"output_type":"json","output_data":{"result":"ok"},"processing_steps":["p"]}'
        ],
    )

    monkeypatch.setattr(
        "src.infrastructure.providers.worker.docker.DockerError", FakeDockerError
    )
    await _attach_stub_client(provider, client)

    task_message = _make_task_message()
    context = _make_context(task_message.task_id)

    result = await provider.execute_task(task_message, context)
    await _drain_status_tasks(provider)

    assert result.status is TaskStatus.COMPLETED
    assert result.result_data is not None
    assert result.result_data.output_data == {"result": "ok"}
    assert client.networks.created and client.networks.created[0]["Name"] == "test-net"

    assert len(client.containers.created_configs) == 1
    container_config = client.containers.created_configs[0]
    assert container_config["Image"] == "worker:123"
    assert container_config["name"].startswith("worker-")

    env_items = container_config["Env"]
    assert isinstance(env_items, list)
    env_map = {item.split("=", 1)[0]: item.split("=", 1)[1] for item in env_items}
    assert env_map["TASK_ID"] == str(context.task_id)
    assert env_map["CORRELATION_ID"] == str(context.correlation_id)
    assert env_map["REQUEST_ID"] == str(context.request_id)
    assert env_map["RETRY_ATTEMPT"] == str(context.retry_attempt)
    assert env_map["MAX_RETRIES"] == str(context.max_retries)
    assert env_map["LOG_LEVEL"] == "DEBUG"
    assert env_map["BASE"] == "abc"

    task_data = json.loads(env_map["TASK_DATA"])
    assert task_data["task_id"] == str(task_message.task_id)
    assert task_data["task_type"] == "analysis"

    host_config = container_config["HostConfig"]
    assert "/app/data" in "".join(host_config["Binds"])  # type: ignore[index]
    device_requests = host_config.get("DeviceRequests")
    assert device_requests and device_requests[0]["Capabilities"] == [["gpu"]]

    status_snapshot = provider.task_statuses[context.task_id]
    assert isinstance(status_snapshot, WorkerTaskStatus)
    assert status_snapshot.status is TaskStatus.COMPLETED

    await provider.shutdown(graceful=False)
    assert client.closed is True


@pytest.mark.asyncio
async def test_health_check_reports_degraded_when_image_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = DockerWorkerConfig(status_store_path=str(tmp_path / "status"))
    provider = DockerWorkerProvider(config)
    client = StubDockerClient(
        image_name=config.image_name,
        image_present=False,
        version_ok=True,
    )

    monkeypatch.setattr(
        "src.infrastructure.providers.worker.docker.DockerError", FakeDockerError
    )
    await _attach_stub_client(provider, client)

    health = await provider.health_check()

    assert health.status == "degraded"
    assert health.dependencies["docker"] is True
    assert health.dependencies["worker_image"] is False


@pytest.mark.asyncio
async def test_health_check_unhealthy_when_daemon_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = DockerWorkerConfig(status_store_path=str(tmp_path / "status"))
    provider = DockerWorkerProvider(config)
    client = StubDockerClient(
        image_name=config.image_name,
        image_present=True,
        version_ok=False,
    )

    monkeypatch.setattr(
        "src.infrastructure.providers.worker.docker.DockerError", FakeDockerError
    )
    await _attach_stub_client(provider, client)

    health = await provider.health_check()

    assert health.status == "unhealthy"
    assert health.dependencies["docker"] is False


@pytest.mark.asyncio
async def test_execute_task_failure_updates_status_and_error_counter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = DockerWorkerConfig(
        max_concurrent_tasks=0,
        status_store_path=str(tmp_path / "status"),
    )
    provider = DockerWorkerProvider(config)
    client = StubDockerClient(image_name=config.image_name)

    monkeypatch.setattr(
        "src.infrastructure.providers.worker.docker.DockerError", FakeDockerError
    )
    await _attach_stub_client(provider, client)

    task_message = _make_task_message()
    context = _make_context(task_message.task_id)

    result = await provider.execute_task(task_message, context)
    await _drain_status_tasks(provider)

    assert result.status is TaskStatus.FAILED
    assert "Maximum concurrent tasks" in (result.error_message or "")
    assert provider._error_count == 1
    assert task_message.task_id in provider.task_statuses
    assert provider.task_statuses[task_message.task_id].status is TaskStatus.FAILED
