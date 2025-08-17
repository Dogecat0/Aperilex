"""Tests for the new messaging service infrastructure."""

from datetime import timedelta
from uuid import uuid4

import pytest

from src.infrastructure.messaging import (
    AsyncResult,
    EnvironmentType,
    TaskMessage,
    TaskPriority,
    cleanup_services,
    get_queue_service,
    get_storage_service,
    get_worker_service,
    initialize_services,
    task,
)


@pytest.fixture
async def test_services():
    """Initialize test services."""
    await initialize_services(EnvironmentType.TESTING, storage_type="memory")
    yield
    await cleanup_services()


@pytest.mark.asyncio
async def test_queue_service_basic_operations(test_services):
    """Test basic queue service operations."""
    queue_service = await get_queue_service()

    # Test health check
    assert await queue_service.health_check()

    # Create a test task message
    task_message = TaskMessage(
        task_id=uuid4(),
        task_name="test_task",
        args=["arg1", "arg2"],
        kwargs={"key": "value"},
        queue="test_queue",
        priority=TaskPriority.HIGH,
    )

    # Send task
    task_id = await queue_service.send_task(task_message)
    assert task_id == task_message.task_id

    # Check queue size
    queue_size = await queue_service.get_queue_size("test_queue")
    assert queue_size == 1

    # Receive task
    received_task = await queue_service.receive_task("test_queue")
    assert received_task is not None
    assert received_task.task_id == task_message.task_id
    assert received_task.task_name == "test_task"
    assert received_task.args == ["arg1", "arg2"]
    assert received_task.kwargs == {"key": "value"}

    # Acknowledge task
    success = await queue_service.ack_task(task_id)
    assert success


@pytest.mark.asyncio
async def test_storage_service_basic_operations(test_services):
    """Test basic storage service operations."""
    storage_service = await get_storage_service()

    # Test health check
    assert await storage_service.health_check()

    # Test set and get
    key = "test_key"
    value = {"data": "test_value", "number": 42}

    success = await storage_service.set(key, value)
    assert success

    retrieved_value = await storage_service.get(key)
    assert retrieved_value == value

    # Test exists
    assert await storage_service.exists(key)
    assert not await storage_service.exists("nonexistent_key")

    # Test delete
    success = await storage_service.delete(key)
    assert success
    assert not await storage_service.exists(key)

    # Test TTL
    await storage_service.set("ttl_key", "ttl_value", ttl=timedelta(seconds=1))
    assert await storage_service.exists("ttl_key")

    # Test increment
    counter_key = "counter"
    new_value = await storage_service.increment(counter_key, 5)
    assert new_value == 5

    new_value = await storage_service.increment(counter_key, 3)
    assert new_value == 8


@pytest.mark.asyncio
async def test_worker_service_basic_operations(test_services):
    """Test basic worker service operations."""
    worker_service = await get_worker_service()

    # Test health check
    assert await worker_service.health_check()

    # Register a test task handler
    def test_handler(x, y):
        return x + y

    worker_service.register_task("add_numbers", test_handler)

    # Get worker stats
    stats = await worker_service.get_worker_stats()
    assert "add_numbers" in stats["registered_tasks"]

    # Unregister task
    worker_service.unregister_task("add_numbers")

    stats = await worker_service.get_worker_stats()
    assert "add_numbers" not in stats["registered_tasks"]


@pytest.mark.asyncio
async def test_task_decorator(test_services):
    """Test the task decorator functionality."""

    # Define a task using the decorator
    @task(name="test_add", queue="math_queue", priority=TaskPriority.HIGH)
    async def add_task(x: int, y: int) -> int:
        return x + y

    # Test task properties
    assert add_task.name == "test_add"
    assert add_task.queue == "math_queue"
    assert add_task.priority == TaskPriority.HIGH

    # Test delay method
    result = await add_task.delay(5, 3)
    assert isinstance(result, AsyncResult)
    assert result.id is not None


@pytest.mark.asyncio
async def test_hash_operations(test_services):
    """Test hash storage operations."""
    storage_service = await get_storage_service()

    hash_key = "test_hash"
    hash_data = {"field1": "value1", "field2": 42, "field3": {"nested": "data"}}

    # Set hash
    success = await storage_service.set_hash(hash_key, hash_data)
    assert success

    # Get hash
    retrieved_hash = await storage_service.get_hash(hash_key)
    assert retrieved_hash == hash_data

    # Test non-existent hash
    non_existent = await storage_service.get_hash("nonexistent_hash")
    assert non_existent is None


@pytest.mark.asyncio
async def test_pattern_clearing(test_services):
    """Test pattern-based key clearing."""
    storage_service = await get_storage_service()

    # Set multiple keys with pattern
    await storage_service.set("test:key1", "value1")
    await storage_service.set("test:key2", "value2")
    await storage_service.set("other:key", "value3")

    # Clear keys matching pattern
    deleted_count = await storage_service.clear_pattern("test:*")
    assert deleted_count == 2

    # Verify only matching keys were deleted
    assert not await storage_service.exists("test:key1")
    assert not await storage_service.exists("test:key2")
    assert await storage_service.exists("other:key")


@pytest.mark.asyncio
async def test_queue_purging(test_services):
    """Test queue purging functionality."""
    queue_service = await get_queue_service()

    # Send multiple tasks to queue
    for i in range(5):
        task_message = TaskMessage(
            task_id=uuid4(),
            task_name=f"task_{i}",
            args=[i],
            kwargs={},
            queue="purge_test",
        )
        await queue_service.send_task(task_message)

    # Verify queue has messages
    queue_size = await queue_service.get_queue_size("purge_test")
    assert queue_size == 5

    # Purge queue
    purged_count = await queue_service.purge_queue("purge_test")
    assert purged_count == 5

    # Verify queue is empty
    queue_size = await queue_service.get_queue_size("purge_test")
    assert queue_size == 0
