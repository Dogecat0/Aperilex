from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.routers.tasks as tasks_router
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.authentication import AuthenticationResult
from src.application.interfaces.sse import SSEConnection
from src.shared.enums import TaskStatus
from src.shared.types import UserId

TasksClientFactory = Callable[
    [AuthenticationResult | None],
    tuple[TestClient, "_StubCoordinator", "_StubSSEManager"],
]


def _make_auth_result(**overrides: Any) -> AuthenticationResult:
    base = {
        "authenticated": True,
        "user_id": UserId(uuid4()),
        "user_email": "user@example.com",
        "user_tier": "ESSENTIAL",
        "permissions": ["write:tasks", "read:tasks", "read:tasks"],
    }
    base.update(overrides)
    return AuthenticationResult(**base)


class _StubCoordinator:
    def __init__(self) -> None:
        self.statuses: dict[str, TaskResponse] = {}
        self.retries: dict[str, TaskResponse] = {}
        self.fail_get = False
        self.fail_retry = False
        self.requested_ids: list[str] = []
        self.retry_ids: list[str] = []

    async def get_task_status(self, task_id: str) -> TaskResponse | None:
        self.requested_ids.append(task_id)
        if self.fail_get:
            raise RuntimeError("status failure")
        return self.statuses.get(task_id)

    async def retry_failed_task(self, task_id: str) -> TaskResponse | None:
        self.retry_ids.append(task_id)
        if self.fail_retry:
            raise RuntimeError("retry failure")
        return self.retries.get(task_id)


class _StubSSEManager:
    def __init__(self) -> None:
        self.open_requests: list[dict[str, Any]] = []
        self.close_requests: list[dict[str, Any]] = []
        self.stream_requests: list[str] = []
        self.payloads: list[str] = ["data: task-progress\n\n"]
        self.raise_on_open = False

    async def open_connection(
        self,
        user_id: UserId,
        *,
        event_types: list[str] | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> SSEConnection:
        if self.raise_on_open:
            raise RuntimeError("open failed")
        metadata = metadata or {}
        event_types = event_types or []
        connection_id = f"conn-{len(self.open_requests) + 1}"
        record = {
            "user_id": user_id,
            "event_types": event_types,
            "metadata": metadata,
            "connection_id": connection_id,
        }
        self.open_requests.append(record)
        return SSEConnection(
            connection_id=connection_id,
            user_id=user_id,
            created_at="2024-01-01T00:00:00Z",
            last_heartbeat="2024-01-01T00:00:00Z",
            event_types=event_types,
            metadata=metadata,
        )

    async def close_connection(
        self,
        connection_id: str,
        user_id: UserId | None = None,
    ) -> bool:
        self.close_requests.append(
            {"connection_id": connection_id, "user_id": user_id}
        )
        return True

    def stream_events(self, connection_id: str):
        self.stream_requests.append(connection_id)

        async def _generator():
            for payload in self.payloads:
                yield payload

        return _generator()


@pytest.fixture()
def tasks_client_factory(monkeypatch: pytest.MonkeyPatch) -> TasksClientFactory:
    def _factory(
        auth_result: AuthenticationResult | None = None,
    ) -> tuple[TestClient, _StubCoordinator, _StubSSEManager]:
        coordinator = _StubCoordinator()
        sse_manager = _StubSSEManager()
        app = FastAPI()
        app.include_router(tasks_router.router, prefix="/api")
        app.dependency_overrides[
            tasks_router.get_background_task_coordinator
        ] = lambda: coordinator
        app.dependency_overrides[
            tasks_router.get_sse_connection_manager
        ] = lambda: sse_manager
        app.dependency_overrides[tasks_router.get_current_user] = (
            lambda: auth_result or _make_auth_result()
        )
        return TestClient(app), coordinator, sse_manager

    return _factory


def test_get_task_status_returns_response(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()
    coordinator.statuses["task-1"] = TaskResponse(
        task_id="task-1", status=TaskStatus.PENDING.value
    )

    response = client.get("/api/tasks/task-1/status")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-1"
    assert body["status"] == TaskStatus.PENDING.value
    assert body["schema_version"] == 1
    assert coordinator.requested_ids == ["task-1"]


def test_get_task_status_returns_404_for_missing_task(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()

    response = client.get("/api/tasks/missing/status")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert coordinator.requested_ids == ["missing"]


def test_get_task_status_surfaces_internal_error(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()
    coordinator.fail_get = True

    response = client.get("/api/tasks/failure/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retrieve task status"
    assert coordinator.requested_ids == ["failure"]


def test_retry_failed_task_returns_new_task(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()
    coordinator.retries["task-2"] = TaskResponse(
        task_id="task-2", status=TaskStatus.PENDING.value
    )

    response = client.post("/api/tasks/task-2/retry")

    assert response.status_code == 200
    assert response.json()["task_id"] == "task-2"
    assert coordinator.retry_ids == ["task-2"]


def test_retry_failed_task_returns_404_for_missing(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()

    response = client.post("/api/tasks/missing/retry")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert coordinator.retry_ids == ["missing"]


def test_retry_failed_task_surfaces_internal_error(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, coordinator, _ = tasks_client_factory()
    coordinator.fail_retry = True

    response = client.post("/api/tasks/failure/retry")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retry task"
    assert coordinator.retry_ids == ["failure"]


def test_stream_requires_user_id(
    tasks_client_factory: TasksClientFactory,
) -> None:
    auth_result = _make_auth_result(user_id=None)
    client, _, sse_manager = tasks_client_factory(auth_result)

    response = client.get("/api/tasks/task-3/stream")

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "auth.user.missing_id"
    assert sse_manager.open_requests == []


def test_stream_requires_email(
    tasks_client_factory: TasksClientFactory,
) -> None:
    auth_result = _make_auth_result(user_email=None)
    client, _, sse_manager = tasks_client_factory(auth_result)

    response = client.get("/api/tasks/task-3/stream")

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "auth.user.missing_email"
    assert sse_manager.open_requests == []


def test_stream_rejects_invalid_tier(
    tasks_client_factory: TasksClientFactory,
) -> None:
    auth_result = _make_auth_result(user_tier="INVALID")
    client, _, sse_manager = tasks_client_factory(auth_result)

    response = client.get("/api/tasks/task-3/stream")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "auth.user.invalid_tier"
    assert sse_manager.open_requests == []


def test_stream_opens_and_closes_connection(
    tasks_client_factory: TasksClientFactory,
) -> None:
    auth_result = _make_auth_result(user_tier="PLUS")
    client, _, sse_manager = tasks_client_factory(auth_result)
    sse_manager.payloads = ["data: update-1\n\n", "data: update-2\n\n"]
    auth_result.permissions = ["tasks:read", "tasks:write", "tasks:read"]
    events = ["progress", "status", "progress"]

    with client.stream(
        "GET",
        "/api/tasks/task-3/stream",
        params=[("events", value) for value in events],
    ) as response:
        assert response.status_code == 200
        body = b"".join(response.iter_bytes())

    assert b"update-1" in body
    assert b"update-2" in body

    assert len(sse_manager.open_requests) == 1
    open_call = sse_manager.open_requests[0]
    assert open_call["event_types"] == ["progress", "status"]
    assert open_call["metadata"]["user_email"] == "user@example.com"
    assert open_call["metadata"]["user_tier"] == "PLUS"
    assert open_call["metadata"]["permissions"] == "tasks:read,tasks:write"

    assert sse_manager.stream_requests == [open_call["connection_id"]]
    assert sse_manager.close_requests == [
        {"connection_id": open_call["connection_id"], "user_id": auth_result.user_id}
    ]


def test_stream_surfaces_open_failure(
    tasks_client_factory: TasksClientFactory,
) -> None:
    client, _, sse_manager = tasks_client_factory()
    sse_manager.raise_on_open = True

    response = client.get("/api/tasks/task-3/stream")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to establish SSE stream"
    assert sse_manager.close_requests == []
