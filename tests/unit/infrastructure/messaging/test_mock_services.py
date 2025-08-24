"""Unit tests for mock messaging service implementations."""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.infrastructure.messaging.implementations.mock_services import (
    MockQueueService,
    MockStorageService,
    MockWorkerService,
    create_mock_queue_service,
    create_mock_storage_service,
    create_mock_worker_service,
    create_test_task_message,
)
from src.infrastructure.messaging.interfaces import (
    IQueueService,
    IStorageService,
    IWorkerService,
    TaskMessage,
    TaskPriority,
    TaskResult,
    TaskStatus,
)


class TestMockQueueService:
    """Test MockQueueService implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.queue_service = MockQueueService()

    def test_initialization(self):
        """Test MockQueueService initialization."""
        assert isinstance(self.queue_service, IQueueService)
        assert self.queue_service.queues == {}
        assert self.queue_service.task_statuses == {}
        assert not self.queue_service.connected
        assert self.queue_service.call_log == []

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """Test connection lifecycle."""
        assert not self.queue_service.connected

        # Test connect
        await self.queue_service.connect()
        assert self.queue_service.connected
        assert ("connect", None) in self.queue_service.call_log

        # Test disconnect
        await self.queue_service.disconnect()
        assert not self.queue_service.connected
        assert ("disconnect", None) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_send_task_requires_connection(self):
        """Test that send_task requires connection."""
        task_message = await create_test_task_message()

        # Should fail when not connected
        with pytest.raises(RuntimeError, match="Not connected"):
            await self.queue_service.send_task(task_message)

    @pytest.mark.asyncio
    async def test_send_task_success(self):
        """Test successful task sending."""
        await self.queue_service.connect()

        task_message = await create_test_task_message(
            task_name="test_task",
            args=[1, 2, 3],
            kwargs={"key": "value"},
            queue="analysis_queue",
        )

        # Send task
        returned_id = await self.queue_service.send_task(task_message)

        # Verify task was queued
        assert returned_id == task_message.task_id
        assert "analysis_queue" in self.queue_service.queues
        assert task_message in self.queue_service.queues["analysis_queue"]
        assert (
            self.queue_service.task_statuses[task_message.task_id] == TaskStatus.PENDING
        )
        assert ("send_task", task_message) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_send_multiple_tasks_to_same_queue(self):
        """Test sending multiple tasks to the same queue."""
        await self.queue_service.connect()

        task1 = await create_test_task_message(task_name="task1")
        task2 = await create_test_task_message(task_name="task2")

        await self.queue_service.send_task(task1)
        await self.queue_service.send_task(task2)

        assert len(self.queue_service.queues["default"]) == 2
        assert task1 in self.queue_service.queues["default"]
        assert task2 in self.queue_service.queues["default"]

    @pytest.mark.asyncio
    async def test_send_tasks_to_different_queues(self):
        """Test sending tasks to different queues."""
        await self.queue_service.connect()

        task1 = await create_test_task_message(task_name="task1", queue="queue1")
        task2 = await create_test_task_message(task_name="task2", queue="queue2")

        await self.queue_service.send_task(task1)
        await self.queue_service.send_task(task2)

        assert "queue1" in self.queue_service.queues
        assert "queue2" in self.queue_service.queues
        assert task1 in self.queue_service.queues["queue1"]
        assert task2 in self.queue_service.queues["queue2"]

    @pytest.mark.asyncio
    async def test_receive_task_requires_connection(self):
        """Test that receive_task requires connection."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await self.queue_service.receive_task()

    @pytest.mark.asyncio
    async def test_receive_task_from_empty_queue(self):
        """Test receiving from empty queue."""
        await self.queue_service.connect()

        result = await self.queue_service.receive_task("empty_queue")

        assert result is None
        assert (
            "receive_task",
            {"queue": "empty_queue", "timeout": None},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_receive_task_success(self):
        """Test successful task receiving."""
        await self.queue_service.connect()

        # Send task first
        task_message = await create_test_task_message(task_name="test_task")
        await self.queue_service.send_task(task_message)

        # Receive task
        received_task = await self.queue_service.receive_task()

        assert received_task == task_message
        assert len(self.queue_service.queues["default"]) == 0  # Task removed from queue
        assert (
            self.queue_service.task_statuses[task_message.task_id] == TaskStatus.RUNNING
        )

    @pytest.mark.asyncio
    async def test_receive_task_fifo_order(self):
        """Test that tasks are received in FIFO order."""
        await self.queue_service.connect()

        task1 = await create_test_task_message(task_name="task1")
        task2 = await create_test_task_message(task_name="task2")
        task3 = await create_test_task_message(task_name="task3")

        # Send tasks
        await self.queue_service.send_task(task1)
        await self.queue_service.send_task(task2)
        await self.queue_service.send_task(task3)

        # Receive tasks - should be in FIFO order
        received1 = await self.queue_service.receive_task()
        received2 = await self.queue_service.receive_task()
        received3 = await self.queue_service.receive_task()

        assert received1 == task1
        assert received2 == task2
        assert received3 == task3

    @pytest.mark.asyncio
    async def test_receive_task_with_timeout_parameter(self):
        """Test receive_task with timeout parameter."""
        await self.queue_service.connect()

        await self.queue_service.receive_task("test_queue", timeout=30)

        assert (
            "receive_task",
            {"queue": "test_queue", "timeout": 30},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_ack_task(self):
        """Test task acknowledgment."""
        task_id = uuid4()
        self.queue_service.task_statuses[task_id] = TaskStatus.RUNNING

        result = await self.queue_service.ack_task(task_id)

        assert result is True
        assert self.queue_service.task_statuses[task_id] == TaskStatus.SUCCESS
        assert ("ack_task", task_id) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_nack_task_with_requeue(self):
        """Test task negative acknowledgment with requeue."""
        task_id = uuid4()
        self.queue_service.task_statuses[task_id] = TaskStatus.RUNNING

        result = await self.queue_service.nack_task(task_id, requeue=True)

        assert result is True
        assert self.queue_service.task_statuses[task_id] == TaskStatus.RETRY
        assert (
            "nack_task",
            {"task_id": task_id, "requeue": True},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_nack_task_without_requeue(self):
        """Test task negative acknowledgment without requeue."""
        task_id = uuid4()
        self.queue_service.task_statuses[task_id] = TaskStatus.RUNNING

        result = await self.queue_service.nack_task(task_id, requeue=False)

        assert result is True
        assert self.queue_service.task_statuses[task_id] == TaskStatus.FAILURE
        assert (
            "nack_task",
            {"task_id": task_id, "requeue": False},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """Test getting task status."""
        task_id = uuid4()
        self.queue_service.task_statuses[task_id] = TaskStatus.SUCCESS

        status = await self.queue_service.get_task_status(task_id)

        assert status == TaskStatus.SUCCESS
        assert ("get_task_status", task_id) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """Test getting status for non-existent task."""
        task_id = uuid4()

        status = await self.queue_service.get_task_status(task_id)

        assert status is None
        assert ("get_task_status", task_id) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        """Test successful task cancellation."""
        task_id = uuid4()
        self.queue_service.task_statuses[task_id] = TaskStatus.PENDING

        result = await self.queue_service.cancel_task(task_id)

        assert result is True
        assert self.queue_service.task_statuses[task_id] == TaskStatus.REVOKED
        assert ("cancel_task", task_id) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test cancelling non-existent task."""
        task_id = uuid4()

        result = await self.queue_service.cancel_task(task_id)

        assert result is False
        # Task ID should not be in call_log since task wasn't found
        cancel_calls = [
            call for call in self.queue_service.call_log if call[0] == "cancel_task"
        ]
        assert len(cancel_calls) == 0

    @pytest.mark.asyncio
    async def test_purge_queue(self):
        """Test purging queue."""
        await self.queue_service.connect()

        # Add tasks to queue
        task1 = await create_test_task_message(task_name="task1")
        task2 = await create_test_task_message(task_name="task2")
        await self.queue_service.send_task(task1)
        await self.queue_service.send_task(task2)

        assert len(self.queue_service.queues["default"]) == 2

        # Purge queue
        purged_count = await self.queue_service.purge_queue("default")

        assert purged_count == 2
        assert len(self.queue_service.queues["default"]) == 0
        assert (
            "purge_queue",
            {"queue": "default", "count": 2},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_purge_nonexistent_queue(self):
        """Test purging non-existent queue."""
        purged_count = await self.queue_service.purge_queue("nonexistent")

        assert purged_count == 0

    @pytest.mark.asyncio
    async def test_get_queue_size(self):
        """Test getting queue size."""
        await self.queue_service.connect()

        # Add tasks to queue
        task1 = await create_test_task_message(task_name="task1")
        task2 = await create_test_task_message(task_name="task2")
        await self.queue_service.send_task(task1)
        await self.queue_service.send_task(task2)

        size = await self.queue_service.get_queue_size("default")

        assert size == 2
        assert (
            "get_queue_size",
            {"queue": "default", "size": 2},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_get_queue_size_empty_queue(self):
        """Test getting size of empty/nonexistent queue."""
        size = await self.queue_service.get_queue_size("empty")

        assert size == 0
        assert (
            "get_queue_size",
            {"queue": "empty", "size": 0},
        ) in self.queue_service.call_log

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        # Not connected
        health = await self.queue_service.health_check()
        assert health is False
        assert ("health_check", False) in self.queue_service.call_log

        # Connected
        await self.queue_service.connect()
        health = await self.queue_service.health_check()
        assert health is True
        assert ("health_check", True) in self.queue_service.call_log


class TestMockWorkerService:
    """Test MockWorkerService implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worker_service = MockWorkerService()

    def test_initialization(self):
        """Test MockWorkerService initialization."""
        assert isinstance(self.worker_service, IWorkerService)
        assert self.worker_service.task_handlers == {}
        assert not self.worker_service.running
        assert self.worker_service.results == []
        assert self.worker_service.call_log == []
        assert self.worker_service.stats["tasks_processed"] == 0
        assert self.worker_service.stats["tasks_succeeded"] == 0
        assert self.worker_service.stats["tasks_failed"] == 0

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test worker start and stop lifecycle."""
        assert not self.worker_service.running

        # Start worker
        await self.worker_service.start(["queue1", "queue2"])
        assert self.worker_service.running
        assert ("start", ["queue1", "queue2"]) in self.worker_service.call_log

        # Stop worker
        await self.worker_service.stop()
        assert not self.worker_service.running
        assert ("stop", None) in self.worker_service.call_log

    def test_register_task(self):
        """Test task handler registration."""

        def test_handler(x, y):
            return x + y

        self.worker_service.register_task("add_task", test_handler)

        assert "add_task" in self.worker_service.task_handlers
        assert self.worker_service.task_handlers["add_task"] == test_handler
        assert (
            "register_task",
            {"name": "add_task", "handler": test_handler},
        ) in self.worker_service.call_log

    def test_unregister_task(self):
        """Test task handler unregistration."""

        def test_handler():
            pass

        # Register first
        self.worker_service.register_task("test_task", test_handler)
        assert "test_task" in self.worker_service.task_handlers

        # Unregister
        self.worker_service.unregister_task("test_task")
        assert "test_task" not in self.worker_service.task_handlers
        assert ("unregister_task", "test_task") in self.worker_service.call_log

    def test_unregister_nonexistent_task(self):
        """Test unregistering non-existent task."""
        self.worker_service.unregister_task("nonexistent")
        # Should not raise error
        assert ("unregister_task", "nonexistent") in self.worker_service.call_log

    @pytest.mark.asyncio
    async def test_submit_task_result_success(self):
        """Test submitting successful task result."""
        task_result = TaskResult(
            task_id=uuid4(), status=TaskStatus.SUCCESS, result={"data": "test"}
        )

        await self.worker_service.submit_task_result(task_result)

        assert task_result in self.worker_service.results
        assert self.worker_service.stats["tasks_processed"] == 1
        assert self.worker_service.stats["tasks_succeeded"] == 1
        assert self.worker_service.stats["tasks_failed"] == 0
        assert ("submit_task_result", task_result) in self.worker_service.call_log

    @pytest.mark.asyncio
    async def test_submit_task_result_failure(self):
        """Test submitting failed task result."""
        task_result = TaskResult(
            task_id=uuid4(), status=TaskStatus.FAILURE, error="Task failed"
        )

        await self.worker_service.submit_task_result(task_result)

        assert task_result in self.worker_service.results
        assert self.worker_service.stats["tasks_processed"] == 1
        assert self.worker_service.stats["tasks_succeeded"] == 0
        assert self.worker_service.stats["tasks_failed"] == 1

    @pytest.mark.asyncio
    async def test_get_worker_stats(self):
        """Test getting worker statistics."""
        # Register some tasks
        self.worker_service.register_task("task1", lambda: None)
        self.worker_service.register_task("task2", lambda: None)

        # Start worker
        await self.worker_service.start()

        stats = await self.worker_service.get_worker_stats()

        expected_stats = {
            "running": True,
            "registered_tasks": ["task1", "task2"],
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
        }

        assert stats == expected_stats
        assert ("get_worker_stats", expected_stats) in self.worker_service.call_log

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test worker health check."""
        health = await self.worker_service.health_check()

        # Mock service always returns True for health check
        assert health is True
        assert ("health_check", True) in self.worker_service.call_log

    @pytest.mark.asyncio
    async def test_process_task_mock_with_sync_handler(self):
        """Test mock task processing with synchronous handler."""

        def sync_handler(x, y):
            return x * y

        self.worker_service.register_task("multiply", sync_handler)

        task_message = await create_test_task_message(task_name="multiply", args=[3, 4])

        result = await self.worker_service.process_task_mock(task_message)

        assert result.status == TaskStatus.SUCCESS
        assert result.result == 12
        assert result.task_id == task_message.task_id

    @pytest.mark.asyncio
    async def test_process_task_mock_with_async_handler(self):
        """Test mock task processing with asynchronous handler."""

        async def async_handler(x, y):
            await asyncio.sleep(0.001)  # Simulate async work
            return x + y

        self.worker_service.register_task("add_async", async_handler)

        task_message = await create_test_task_message(
            task_name="add_async", args=[5, 7]
        )

        result = await self.worker_service.process_task_mock(task_message)

        assert result.status == TaskStatus.SUCCESS
        assert result.result == 12
        assert result.task_id == task_message.task_id

    @pytest.mark.asyncio
    async def test_process_task_mock_handler_not_found(self):
        """Test mock task processing with missing handler."""
        task_message = await create_test_task_message(task_name="nonexistent_task")

        result = await self.worker_service.process_task_mock(task_message)

        assert result.status == TaskStatus.FAILURE
        assert "No handler for task: nonexistent_task" in result.error
        assert result.task_id == task_message.task_id

    @pytest.mark.asyncio
    async def test_process_task_mock_handler_exception(self):
        """Test mock task processing when handler raises exception."""

        def failing_handler():
            raise ValueError("Handler failed")

        self.worker_service.register_task("failing_task", failing_handler)

        task_message = await create_test_task_message(task_name="failing_task")

        result = await self.worker_service.process_task_mock(task_message)

        assert result.status == TaskStatus.FAILURE
        assert "Handler failed" in result.error
        assert result.task_id == task_message.task_id

    @pytest.mark.asyncio
    async def test_process_task_mock_with_kwargs(self):
        """Test mock task processing with keyword arguments."""

        def handler_with_kwargs(x, y, multiplier=1):
            return (x + y) * multiplier

        self.worker_service.register_task("complex_math", handler_with_kwargs)

        task_message = await create_test_task_message(
            task_name="complex_math", args=[2, 3], kwargs={"multiplier": 5}
        )

        result = await self.worker_service.process_task_mock(task_message)

        assert result.status == TaskStatus.SUCCESS
        assert result.result == 25  # (2 + 3) * 5


class TestMockStorageService:
    """Test MockStorageService implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage_service = MockStorageService()

    def test_initialization(self):
        """Test MockStorageService initialization."""
        assert isinstance(self.storage_service, IStorageService)
        assert self.storage_service.data == {}
        assert self.storage_service.ttl == {}
        assert not self.storage_service.connected
        assert self.storage_service.call_log == []

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """Test connection lifecycle."""
        assert not self.storage_service.connected

        # Test connect
        await self.storage_service.connect()
        assert self.storage_service.connected
        assert ("connect", None) in self.storage_service.call_log

        # Test disconnect
        await self.storage_service.disconnect()
        assert not self.storage_service.connected
        assert ("disconnect", None) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_set_and_get_basic(self):
        """Test basic set and get operations."""
        key = "test_key"
        value = "test_value"

        # Set value
        result = await self.storage_service.set(key, value)
        assert result is True
        assert (
            "set",
            {"key": key, "value": value, "ttl": None},
        ) in self.storage_service.call_log

        # Get value
        retrieved_value = await self.storage_service.get(key)
        assert retrieved_value == value
        assert ("get", key) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        value = await self.storage_service.get("nonexistent")

        assert value is None
        assert ("get", "nonexistent") in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Test setting value with TTL."""
        key = "ttl_key"
        value = "ttl_value"
        ttl = timedelta(seconds=1)

        result = await self.storage_service.set(key, value, ttl)
        assert result is True

        # Value should be retrievable immediately
        retrieved_value = await self.storage_service.get(key)
        assert retrieved_value == value

        # Manually expire the key by setting TTL to past
        self.storage_service.ttl[key] = datetime.utcnow() - timedelta(seconds=1)

        # Value should be None after expiration
        expired_value = await self.storage_service.get(key)
        assert expired_value is None
        assert key not in self.storage_service.data  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_set_updates_ttl(self):
        """Test that setting a key updates/removes TTL."""
        key = "test_key"

        # Set with TTL
        await self.storage_service.set(key, "value1", timedelta(seconds=10))
        assert key in self.storage_service.ttl

        # Set again without TTL
        await self.storage_service.set(key, "value2")
        assert key not in self.storage_service.ttl
        assert self.storage_service.data[key] == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """Test deleting existing key."""
        key = "delete_me"
        value = "to_be_deleted"

        # Set key first
        await self.storage_service.set(key, value)
        assert key in self.storage_service.data

        # Delete key
        result = await self.storage_service.delete(key)
        assert result is True
        assert key not in self.storage_service.data
        assert (
            "delete",
            {"key": key, "existed": True},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Test deleting non-existent key."""
        result = await self.storage_service.delete("nonexistent")

        assert result is False
        assert (
            "delete",
            {"key": "nonexistent", "existed": False},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_delete_removes_ttl(self):
        """Test that delete also removes TTL."""
        key = "key_with_ttl"

        # Set with TTL
        await self.storage_service.set(key, "value", timedelta(seconds=10))
        assert key in self.storage_service.ttl

        # Delete key
        await self.storage_service.delete(key)
        assert key not in self.storage_service.ttl

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists returns True for existing key."""
        key = "exists_key"
        await self.storage_service.set(key, "value")

        exists = await self.storage_service.exists(key)

        assert exists is True
        assert ("exists", {"key": key, "exists": True}) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists returns False for non-existent key."""
        exists = await self.storage_service.exists("nonexistent")

        assert exists is False
        assert (
            "exists",
            {"key": "nonexistent", "exists": False},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_exists_expired_key(self):
        """Test exists returns False for expired key."""
        key = "expired_key"

        # Set with past TTL
        await self.storage_service.set(key, "value")
        self.storage_service.ttl[key] = datetime.utcnow() - timedelta(seconds=1)

        exists = await self.storage_service.exists(key)

        assert exists is False

    @pytest.mark.asyncio
    async def test_increment_new_key(self):
        """Test incrementing non-existent key."""
        key = "counter"

        result = await self.storage_service.increment(key, 5)

        assert result == 5
        assert self.storage_service.data[key] == 5
        assert (
            "increment",
            {"key": key, "amount": 5, "new_value": 5},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_increment_existing_key(self):
        """Test incrementing existing numeric key."""
        key = "counter"
        await self.storage_service.set(key, 10)

        result = await self.storage_service.increment(key, 3)

        assert result == 13
        assert self.storage_service.data[key] == 13

    @pytest.mark.asyncio
    async def test_increment_non_numeric_key(self):
        """Test incrementing key with non-numeric value."""
        key = "not_number"
        await self.storage_service.set(key, "string_value")

        result = await self.storage_service.increment(key, 1)

        assert result == 1  # Should reset to 0 + increment
        assert self.storage_service.data[key] == 1

    @pytest.mark.asyncio
    async def test_increment_default_amount(self):
        """Test increment with default amount of 1."""
        key = "counter"
        await self.storage_service.set(key, 5)

        result = await self.storage_service.increment(key)  # Default amount = 1

        assert result == 6
        assert self.storage_service.data[key] == 6

    @pytest.mark.asyncio
    async def test_set_hash(self):
        """Test setting hash data."""
        key = "hash_key"
        mapping = {"field1": "value1", "field2": "value2", "field3": 123}

        result = await self.storage_service.set_hash(key, mapping)

        assert result is True
        assert self.storage_service.data[key] == mapping
        assert (
            "set_hash",
            {"key": key, "mapping": mapping},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_get_hash_existing(self):
        """Test getting existing hash data."""
        key = "hash_key"
        mapping = {"field1": "value1", "field2": "value2"}
        await self.storage_service.set_hash(key, mapping)

        retrieved_hash = await self.storage_service.get_hash(key)

        assert retrieved_hash == mapping
        assert (
            "get_hash",
            {"key": key, "value": mapping},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_get_hash_nonexistent(self):
        """Test getting non-existent hash."""
        retrieved_hash = await self.storage_service.get_hash("nonexistent")

        assert retrieved_hash is None

    @pytest.mark.asyncio
    async def test_get_hash_non_dict_value(self):
        """Test getting hash when value is not a dictionary."""
        key = "not_hash"
        await self.storage_service.set(key, "string_value")

        retrieved_hash = await self.storage_service.get_hash(key)

        assert retrieved_hash is None

    @pytest.mark.asyncio
    async def test_get_hash_expired_key(self):
        """Test getting hash for expired key."""
        key = "expired_hash"
        mapping = {"field": "value"}

        await self.storage_service.set_hash(key, mapping)
        self.storage_service.ttl[key] = datetime.utcnow() - timedelta(seconds=1)

        retrieved_hash = await self.storage_service.get_hash(key)

        assert retrieved_hash is None
        assert key not in self.storage_service.data  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_clear_pattern_with_matches(self):
        """Test clearing keys matching pattern."""
        # Set up test data
        await self.storage_service.set("user:1:name", "Alice")
        await self.storage_service.set("user:2:name", "Bob")
        await self.storage_service.set("user:1:email", "alice@example.com")
        await self.storage_service.set("product:1:name", "Widget")

        # Clear user keys
        cleared_count = await self.storage_service.clear_pattern("user:*")

        assert cleared_count == 3
        assert "product:1:name" in self.storage_service.data  # Should remain
        assert "user:1:name" not in self.storage_service.data
        assert "user:2:name" not in self.storage_service.data
        assert "user:1:email" not in self.storage_service.data
        assert (
            "clear_pattern",
            {"pattern": "user:*", "count": 3},
        ) in self.storage_service.call_log

    @pytest.mark.asyncio
    async def test_clear_pattern_no_matches(self):
        """Test clearing with pattern that matches no keys."""
        await self.storage_service.set("test_key", "value")

        cleared_count = await self.storage_service.clear_pattern("nomatch:*")

        assert cleared_count == 0
        assert "test_key" in self.storage_service.data  # Should remain

    @pytest.mark.asyncio
    async def test_clear_pattern_removes_ttl(self):
        """Test that clear_pattern also removes TTL entries."""
        key = "temp:key"
        await self.storage_service.set(key, "value", timedelta(seconds=10))
        assert key in self.storage_service.ttl

        await self.storage_service.clear_pattern("temp:*")

        assert key not in self.storage_service.ttl

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test storage health check."""
        # Not connected
        health = await self.storage_service.health_check()
        assert health is False
        assert ("health_check", False) in self.storage_service.call_log

        # Connected
        await self.storage_service.connect()
        health = await self.storage_service.health_check()
        assert health is True
        assert ("health_check", True) in self.storage_service.call_log

    def test_is_expired_helper(self):
        """Test the private _is_expired helper method."""
        key = "test_key"

        # Key with no TTL should not be expired
        assert not self.storage_service._is_expired(key)

        # Key with future TTL should not be expired
        self.storage_service.ttl[key] = datetime.utcnow() + timedelta(seconds=10)
        assert not self.storage_service._is_expired(key)

        # Key with past TTL should be expired
        self.storage_service.ttl[key] = datetime.utcnow() - timedelta(seconds=10)
        assert self.storage_service._is_expired(key)


class TestMockServiceFactories:
    """Test factory functions for mock services."""

    def test_create_mock_queue_service(self):
        """Test queue service factory function."""
        service = create_mock_queue_service()

        assert isinstance(service, MockQueueService)
        assert isinstance(service, IQueueService)

    def test_create_mock_worker_service(self):
        """Test worker service factory function."""
        service = create_mock_worker_service()

        assert isinstance(service, MockWorkerService)
        assert isinstance(service, IWorkerService)

    def test_create_mock_storage_service(self):
        """Test storage service factory function."""
        service = create_mock_storage_service()

        assert isinstance(service, MockStorageService)
        assert isinstance(service, IStorageService)

    @pytest.mark.asyncio
    async def test_create_test_task_message_defaults(self):
        """Test creating test task message with defaults."""
        task_message = await create_test_task_message()

        assert isinstance(task_message, TaskMessage)
        assert task_message.task_name == "test_task"
        assert task_message.args == []
        assert task_message.kwargs == {}
        assert task_message.queue == "default"
        assert task_message.priority == TaskPriority.NORMAL

    @pytest.mark.asyncio
    async def test_create_test_task_message_custom(self):
        """Test creating test task message with custom values."""
        args = [1, 2, 3]
        kwargs = {"key": "value"}

        task_message = await create_test_task_message(
            task_name="custom_task",
            args=args,
            kwargs=kwargs,
            queue="custom_queue",
            priority=TaskPriority.HIGH,
        )

        assert task_message.task_name == "custom_task"
        assert task_message.args == args
        assert task_message.kwargs == kwargs
        assert task_message.queue == "custom_queue"
        assert task_message.priority == TaskPriority.HIGH


class TestMockServiceIntegration:
    """Test integration between mock services."""

    def setup_method(self):
        """Set up test fixtures."""
        self.queue_service = MockQueueService()
        self.worker_service = MockWorkerService()
        self.storage_service = MockStorageService()

    @pytest.mark.asyncio
    async def test_full_task_workflow(self):
        """Test complete task workflow using mock services."""
        # Connect services
        await self.queue_service.connect()
        await self.worker_service.start()
        await self.storage_service.connect()

        # Register task handler
        def add_numbers(x, y):
            return x + y

        self.worker_service.register_task("add", add_numbers)

        # Create and send task
        task_message = await create_test_task_message(task_name="add", args=[5, 3])

        await self.queue_service.send_task(task_message)

        # Worker receives and processes task
        received_task = await self.queue_service.receive_task()
        assert received_task == task_message

        result = await self.worker_service.process_task_mock(received_task)
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 8

        # Acknowledge task
        await self.queue_service.ack_task(task_message.task_id)
        status = await self.queue_service.get_task_status(task_message.task_id)
        assert status == TaskStatus.SUCCESS

        # Store result in storage
        await self.storage_service.set(f"result:{task_message.task_id}", result.result)
        stored_result = await self.storage_service.get(f"result:{task_message.task_id}")
        assert stored_result == 8

    @pytest.mark.asyncio
    async def test_task_failure_workflow(self):
        """Test task failure workflow using mock services."""
        await self.queue_service.connect()
        await self.worker_service.start()

        # Register failing task handler
        def failing_task():
            raise RuntimeError("Task intentionally failed")

        self.worker_service.register_task("fail", failing_task)

        # Create and send task
        task_message = await create_test_task_message(task_name="fail")
        await self.queue_service.send_task(task_message)

        # Worker processes task (should fail)
        received_task = await self.queue_service.receive_task()
        result = await self.worker_service.process_task_mock(received_task)

        assert result.status == TaskStatus.FAILURE
        assert "Task intentionally failed" in result.error

        # Nack task
        await self.queue_service.nack_task(task_message.task_id, requeue=False)
        status = await self.queue_service.get_task_status(task_message.task_id)
        assert status == TaskStatus.FAILURE


class TestMockServiceEdgeCases:
    """Test edge cases and error conditions in mock services."""

    @pytest.mark.asyncio
    async def test_queue_service_operations_without_connection(self):
        """Test that queue operations fail without connection."""
        queue_service = MockQueueService()
        task_message = await create_test_task_message()

        # Send task should fail
        with pytest.raises(RuntimeError, match="Not connected"):
            await queue_service.send_task(task_message)

        # Receive task should fail
        with pytest.raises(RuntimeError, match="Not connected"):
            await queue_service.receive_task()

    @pytest.mark.asyncio
    async def test_storage_large_data_handling(self):
        """Test storage service with large data."""
        storage_service = MockStorageService()
        await storage_service.connect()

        # Test with large string
        large_data = "x" * 10000
        await storage_service.set("large_key", large_data)
        retrieved_data = await storage_service.get("large_key")
        assert retrieved_data == large_data

        # Test with complex nested structure
        complex_data = {
            "level1": {
                "level2": {
                    "list": [1, 2, 3, {"nested": "value"}],
                    "tuple": (1, 2, 3),
                }
            },
            "array": list(range(1000)),
        }
        await storage_service.set("complex_key", complex_data)
        retrieved_complex = await storage_service.get("complex_key")
        assert retrieved_complex == complex_data

    @pytest.mark.asyncio
    async def test_concurrent_mock_operations(self):
        """Test concurrent operations on mock services."""
        queue_service = MockQueueService()
        await queue_service.connect()

        # Send multiple tasks concurrently
        tasks = []
        for i in range(10):
            task_message = await create_test_task_message(task_name=f"task_{i}")
            tasks.append(queue_service.send_task(task_message))

        await asyncio.gather(*tasks)

        # Verify all tasks were queued
        queue_size = await queue_service.get_queue_size("default")
        assert queue_size == 10

    def test_mock_services_call_log_completeness(self):
        """Test that all operations are logged in call_log."""
        queue_service = MockQueueService()
        worker_service = MockWorkerService()
        storage_service = MockStorageService()

        # Each service should start with empty call log
        assert queue_service.call_log == []
        assert worker_service.call_log == []
        assert storage_service.call_log == []

        # All operations should be logged (tested implicitly in other tests)
        # This test serves as documentation of the logging behavior
