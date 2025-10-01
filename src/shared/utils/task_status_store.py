"""Lightweight filesystem-backed store for worker task status snapshots."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

from src.application.interfaces.worker import WorkerTaskStatus
from src.shared.types import TaskId

logger = logging.getLogger(__name__)


class TaskStatusStore:
    """Persist and retrieve task status snapshots on the local filesystem."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        raw_path = base_path or os.environ.get("TASK_STATUS_STORE_PATH") or "task-status"

        target = Path(raw_path)
        if not target.is_absolute():
            storage_root = os.environ.get("LOCAL_STORAGE_PATH")
            storage_root_path = (
                Path(storage_root).expanduser()
                if storage_root
                else Path(tempfile.gettempdir()) / "aperilex"
            )
            target = storage_root_path / target

        candidate = target.expanduser()

        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as exc:
            fallback = Path(tempfile.gettempdir()) / "aperilex" / "task-status"
            fallback.mkdir(parents=True, exist_ok=True)
            if base_path is not None:
                logger.warning(
                    "Task status store path '%s' not writable (%s); using fallback '%s'",
                    candidate,
                    exc,
                    fallback,
                )
            candidate = fallback

        self.base_path = candidate

    async def write_status(self, status: WorkerTaskStatus) -> None:
        """Persist the provided status snapshot to disk."""

        payload = status.model_dump(mode="json")
        payload["task_id"] = str(payload.get("task_id"))

        task_id = str(status.task_id)
        final_path = self.base_path / f"{task_id}.json"
        temp_path = final_path.with_suffix(".json.tmp")

        content = json.dumps(payload, separators=(",", ":"))

        def _write() -> None:
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(final_path)

        await asyncio.to_thread(_write)

    async def read_status(self, task_id: TaskId) -> WorkerTaskStatus | None:
        """Load the latest status snapshot for the given task, if it exists."""

        task_identifier = str(task_id)
        status_path = self.base_path / f"{task_identifier}.json"
        if not status_path.exists():
            return None

        try:
            text = await asyncio.to_thread(status_path.read_text, encoding="utf-8")
            data: dict[str, Any] = json.loads(text)
        except (OSError, json.JSONDecodeError):
            return None

        raw_task_id = data.get("task_id") or task_identifier
        try:
            data["task_id"] = TaskId(UUID(str(raw_task_id)))
        except (ValueError, TypeError):
            data["task_id"] = TaskId(UUID(task_identifier))

        return WorkerTaskStatus.model_validate(data)

    async def delete_status(self, task_id: TaskId) -> None:
        """Remove the persisted status snapshot for the given task."""

        task_identifier = str(task_id)
        status_path = self.base_path / f"{task_identifier}.json"
        temp_path = status_path.with_suffix(".json.tmp")

        def _delete() -> None:
            try:
                if status_path.exists():
                    status_path.unlink()
            except OSError:
                pass
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

        await asyncio.to_thread(_delete)
