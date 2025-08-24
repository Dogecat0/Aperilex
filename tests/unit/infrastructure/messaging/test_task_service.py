"""Unit tests for task service, decorators, and async result handling."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.infrastructure.messaging.interfaces import (
    IQueueService,
    IWorkerService,
    TaskMessage,
    TaskPriority,
    TaskStatus,
)
from src.infrastructure.messaging.task_service import (
    AsyncResult,
    Task,
    TaskFailure,
    TaskService,
    TaskTimeout,
    task,
)


class TestTask:
    """Test Task decorator class."""

    def test_task_initialization_minimal(self):
        """Test task initialization with minimal parameters."""
        task_decorator = Task()

        assert task_decorator.name is None
        assert task_decorator.queue == "default"
        assert task_decorator.priority == TaskPriority.NORMAL
        assert task_decorator.max_retries == 3
        assert task_decorator.timeout is None
        assert task_decorator.func is None
        assert not task_decorator._registered

    def test_task_initialization_full(self):
        """Test task initialization with all parameters."""
        task_decorator = Task(
            name="custom_task",
            queue="analysis_queue",
            priority=TaskPriority.HIGH,
            max_retries=5,
            timeout=300,
        )

        assert task_decorator.name == "custom_task"
        assert task_decorator.queue == "analysis_queue"
        assert task_decorator.priority == TaskPriority.HIGH
        assert task_decorator.max_retries == 5
        assert task_decorator.timeout == 300

    def test_task_decorator_function_wrapping(self):
        """Test task decorator properly wraps functions."""
        task_decorator = Task(name="test_task")

        @task_decorator
        def sample_function(x, y):
            return x + y

        # After decoration, sample_function should be the Task instance
        assert sample_function is task_decorator
        assert task_decorator.name == "test_task"
        assert callable(task_decorator.func)

    def test_task_decorator_name_inference(self):
        """Test task decorator infers name from function when not provided."""
        task_decorator = Task()

        @task_decorator
        def inferred_name_task():
            return "result"

        assert task_decorator.name == "inferred_name_task"

    def test_task_decorator_returns_self(self):
        """Test task decorator returns itself when wrapping function."""
        task_decorator = Task()

        def sample_function():
            pass

        result = task_decorator(sample_function)

        assert result is task_decorator
        assert result.func is sample_function

    @pytest.mark.asyncio
    async def test_delay_method(self):
        """Test task delay method creates and queues task message."""
        task_decorator = Task(name="test_task")

        def sample_function(x, y, z=None):
            return x + y + (z or 0)

        task_decorator(sample_function)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            result = await task_decorator.delay(1, 2, z=3)

            # Verify queue service was called
            mock_queue_service.send_task.assert_called_once()
            call_args = mock_queue_service.send_task.call_args[0][0]

            assert isinstance(call_args, TaskMessage)
            assert call_args.task_name == "test_task"
            assert call_args.args == [1, 2]
            assert call_args.kwargs == {"z": 3}

            # Verify AsyncResult is returned
            assert isinstance(result, AsyncResult)

    @pytest.mark.asyncio
    async def test_apply_async_method(self):
        """Test apply_async method with all options."""
        task_decorator = Task(name="test_task")

        def sample_function():
            pass

        task_decorator(sample_function)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            task_id = uuid4()
            eta = datetime.utcnow() + timedelta(minutes=5)
            expires = datetime.utcnow() + timedelta(hours=1)

            result = await task_decorator.apply_async(
                args=[1, 2],
                kwargs={"key": "value"},
                task_id=task_id,
                eta=eta,
                expires=expires,
                queue="custom_queue",
                priority=TaskPriority.HIGH,
                max_retries=5,
                timeout=600,
            )

            # Verify queue service was called with correct message
            mock_queue_service.send_task.assert_called_once()
            call_args = mock_queue_service.send_task.call_args[0][0]

            assert isinstance(call_args, TaskMessage)
            assert call_args.task_id == task_id
            assert call_args.task_name == "test_task"
            assert call_args.args == [1, 2]
            assert call_args.kwargs == {"key": "value"}
            assert call_args.queue == "custom_queue"
            assert call_args.priority == TaskPriority.HIGH
            assert call_args.max_retries == 5
            assert call_args.timeout == 600
            assert call_args.eta == eta
            assert call_args.expires == expires

            # Verify AsyncResult is returned
            assert isinstance(result, AsyncResult)
            assert result.task_id == task_id

    @pytest.mark.asyncio
    async def test_apply_async_without_task_name_fails(self):
        """Test apply_async fails when task name is not set."""
        task_decorator = Task()  # No name provided

        # Don't wrap a function, so name remains None
        with pytest.raises(ValueError, match="Task name must be set"):
            await task_decorator.apply_async(args=[1, 2])

    @pytest.mark.asyncio
    async def test_apply_async_generates_task_id_when_not_provided(self):
        """Test apply_async generates task ID when not provided."""
        task_decorator = Task(name="test_task")
        task_decorator.func = lambda: None

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            result = await task_decorator.apply_async()

            # Verify task ID was generated
            call_args = mock_queue_service.send_task.call_args[0][0]
            assert isinstance(call_args.task_id, UUID)
            assert result.task_id == call_args.task_id

    def test_task_repr(self):
        """Test task string representation."""
        task_decorator = Task(name="test_task")

        assert repr(task_decorator) == "Task(test_task)"

    @pytest.mark.asyncio
    async def test_ensure_registered_success(self):
        """Test successful task registration."""
        task_decorator = Task(name="test_task")
        task_decorator.func = lambda: None

        with patch(
            'src.infrastructure.messaging.task_service.get_worker_service'
        ) as mock_get_worker:
            mock_worker_service = AsyncMock(spec=IWorkerService)
            mock_get_worker.return_value = mock_worker_service

            await task_decorator._ensure_registered()

            assert task_decorator._registered
            mock_worker_service.register_task.assert_called_once_with(
                "test_task", task_decorator.func
            )

    @pytest.mark.asyncio
    async def test_ensure_registered_already_registered(self):
        """Test that already registered tasks are not re-registered."""
        task_decorator = Task(name="test_task")
        task_decorator.func = lambda: None
        task_decorator._registered = True

        with patch(
            'src.infrastructure.messaging.task_service.get_worker_service'
        ) as mock_get_worker:
            mock_worker_service = AsyncMock(spec=IWorkerService)
            mock_get_worker.return_value = mock_worker_service

            await task_decorator._ensure_registered()

            # Should not call register_task since already registered
            mock_worker_service.register_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_registered_handles_exceptions(self):
        """Test that registration exceptions are handled gracefully."""
        task_decorator = Task(name="test_task")
        task_decorator.func = lambda: None

        with patch(
            'src.infrastructure.messaging.task_service.get_worker_service'
        ) as mock_get_worker:
            mock_get_worker.side_effect = Exception("Worker service unavailable")

            # Should not raise exception
            await task_decorator._ensure_registered()

            # Should not be marked as registered
            assert not task_decorator._registered

    def test_task_decorator_registration_on_import(self):
        """Test task registration attempt during import/decoration."""
        # This test verifies that the decorator attempts registration
        # but handles RuntimeError gracefully when no event loop exists

        with patch('asyncio.create_task') as mock_create_task:
            mock_create_task.side_effect = RuntimeError("No event loop")

            task_decorator = Task(name="test_task")

            @task_decorator
            def sample_function():
                pass

            # Should not raise exception despite RuntimeError
            # After decoration, sample_function should be the Task instance
            assert sample_function is task_decorator


class TestAsyncResult:
    """Test AsyncResult class."""

    def test_async_result_initialization(self):
        """Test AsyncResult initialization."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        assert result.task_id == task_id
        assert result._result is None
        assert result._status is None
        assert result._error is None

    def test_async_result_id_property(self):
        """Test AsyncResult id property returns string."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        assert result.id == str(task_id)
        assert isinstance(result.id, str)

    @pytest.mark.asyncio
    async def test_get_successful_result(self):
        """Test getting successful task result."""
        task_id = uuid4()
        result = AsyncResult(task_id)
        expected_result = {"data": "success"}
        result._result = expected_result

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_task_status.return_value = TaskStatus.SUCCESS
            mock_get_queue.return_value = mock_queue_service

            actual_result = await result.get(timeout=1)

            assert actual_result == expected_result

    @pytest.mark.asyncio
    async def test_get_failed_result_raises_exception(self):
        """Test that failed result raises TaskFailure exception."""
        task_id = uuid4()
        result = AsyncResult(task_id)
        result._error = "Task execution failed"

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_task_status.return_value = TaskStatus.FAILURE
            mock_get_queue.return_value = mock_queue_service

            with pytest.raises(
                TaskFailure, match="Task .+ failed: Task execution failed"
            ):
                await result.get(timeout=1)

    @pytest.mark.asyncio
    async def test_get_revoked_result_raises_exception(self):
        """Test that revoked result raises TaskFailure exception."""
        task_id = uuid4()
        result = AsyncResult(task_id)
        result._error = "Task was revoked"

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_task_status.return_value = TaskStatus.REVOKED
            mock_get_queue.return_value = mock_queue_service

            with pytest.raises(TaskFailure, match="Task .+ failed: Task was revoked"):
                await result.get(timeout=1)

    @pytest.mark.asyncio
    async def test_get_timeout_raises_exception(self):
        """Test that timeout raises TaskTimeout exception."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_task_status.return_value = TaskStatus.RUNNING
            mock_get_queue.return_value = mock_queue_service

            with pytest.raises(TaskTimeout, match="Task .+ timed out after 1 seconds"):
                await result.get(timeout=1)

    @pytest.mark.asyncio
    async def test_get_without_timeout_waits(self):
        """Test get without timeout waits for completion."""
        task_id = uuid4()
        result = AsyncResult(task_id)
        expected_result = {"final": "result"}
        result._result = expected_result

        call_count = 0

        def mock_get_status(task_id):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return TaskStatus.RUNNING
            return TaskStatus.SUCCESS

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_task_status.side_effect = mock_get_status
            mock_get_queue.return_value = mock_queue_service

            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                actual_result = await result.get()

                # Should have called sleep while waiting
                assert mock_sleep.call_count >= 2
                assert actual_result == expected_result

    @pytest.mark.asyncio
    async def test_ready_method(self):
        """Test ready method for different task states."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            # Test not ready states
            for status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRY]:
                mock_queue_service.get_task_status.return_value = status
                assert not await result.ready()

            # Test ready states
            for status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]:
                mock_queue_service.get_task_status.return_value = status
                assert await result.ready()

    @pytest.mark.asyncio
    async def test_successful_method(self):
        """Test successful method returns True only for SUCCESS status."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            # Test successful status
            mock_queue_service.get_task_status.return_value = TaskStatus.SUCCESS
            assert await result.successful()

            # Test all other statuses
            for status in [
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
                TaskStatus.FAILURE,
                TaskStatus.RETRY,
                TaskStatus.REVOKED,
            ]:
                mock_queue_service.get_task_status.return_value = status
                assert not await result.successful()

    @pytest.mark.asyncio
    async def test_failed_method(self):
        """Test failed method returns True only for FAILURE status."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            # Test failed status
            mock_queue_service.get_task_status.return_value = TaskStatus.FAILURE
            assert await result.failed()

            # Test all other statuses
            for status in [
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
                TaskStatus.SUCCESS,
                TaskStatus.RETRY,
                TaskStatus.REVOKED,
            ]:
                mock_queue_service.get_task_status.return_value = status
                assert not await result.failed()

    @pytest.mark.asyncio
    async def test_get_status_method(self):
        """Test get_status method returns current task status."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            for expected_status in TaskStatus:
                mock_queue_service.get_task_status.return_value = expected_status
                actual_status = await result.get_status()
                assert actual_status == expected_status

    @pytest.mark.asyncio
    async def test_revoke_method(self):
        """Test revoke method cancels the task."""
        task_id = uuid4()
        result = AsyncResult(task_id)

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.cancel_task.return_value = True
            mock_get_queue.return_value = mock_queue_service

            success = await result.revoke()

            assert success
            mock_queue_service.cancel_task.assert_called_once_with(task_id)


class TestTaskService:
    """Test TaskService static methods."""

    def test_task_static_method(self):
        """Test TaskService.task creates Task decorator."""
        task_decorator = TaskService.task(
            name="service_task", queue="service_queue", priority=TaskPriority.HIGH
        )

        assert isinstance(task_decorator, Task)
        assert task_decorator.name == "service_task"
        assert task_decorator.queue == "service_queue"
        assert task_decorator.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_send_task_method(self):
        """Test TaskService.send_task creates and sends task."""
        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            result = await TaskService.send_task(
                task_name="direct_task",
                args=[1, 2, 3],
                kwargs={"key": "value"},
                queue="direct_queue",
                priority=TaskPriority.HIGH,
            )

            # Verify queue service was called
            mock_queue_service.send_task.assert_called_once()
            call_args = mock_queue_service.send_task.call_args[0][0]

            assert isinstance(call_args, TaskMessage)
            assert call_args.task_name == "direct_task"
            assert call_args.args == [1, 2, 3]
            assert call_args.kwargs == {"key": "value"}
            assert call_args.queue == "direct_queue"
            assert call_args.priority == TaskPriority.HIGH

            # Verify AsyncResult is returned
            assert isinstance(result, AsyncResult)

    @pytest.mark.asyncio
    async def test_get_task_result_method(self):
        """Test TaskService.get_task_result creates AsyncResult."""
        task_id = uuid4()
        result = await TaskService.get_task_result(task_id)

        assert isinstance(result, AsyncResult)
        assert result.task_id == task_id

    @pytest.mark.asyncio
    async def test_purge_queue_method(self):
        """Test TaskService.purge_queue."""
        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.purge_queue.return_value = 5
            mock_get_queue.return_value = mock_queue_service

            count = await TaskService.purge_queue("test_queue")

            assert count == 5
            mock_queue_service.purge_queue.assert_called_once_with("test_queue")

    @pytest.mark.asyncio
    async def test_get_queue_size_method(self):
        """Test TaskService.get_queue_size."""
        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_queue_service.get_queue_size.return_value = 10
            mock_get_queue.return_value = mock_queue_service

            size = await TaskService.get_queue_size("test_queue")

            assert size == 10
            mock_queue_service.get_queue_size.assert_called_once_with("test_queue")

    @pytest.mark.asyncio
    async def test_get_worker_stats_method(self):
        """Test TaskService.get_worker_stats."""
        expected_stats = {"active_tasks": 3, "completed_tasks": 100}

        with patch(
            'src.infrastructure.messaging.task_service.get_worker_service'
        ) as mock_get_worker:
            mock_worker_service = AsyncMock(spec=IWorkerService)
            mock_worker_service.get_worker_stats.return_value = expected_stats
            mock_get_worker.return_value = mock_worker_service

            stats = await TaskService.get_worker_stats()

            assert stats == expected_stats
            mock_worker_service.get_worker_stats.assert_called_once()


class TestConvenienceTask:
    """Test convenience task function."""

    def test_convenience_task_function(self):
        """Test that convenience task function creates Task decorator."""
        task_decorator = task(
            name="convenience_task",
            queue="convenience_queue",
            priority=TaskPriority.LOW,
            max_retries=1,
            timeout=60,
        )

        assert isinstance(task_decorator, Task)
        assert task_decorator.name == "convenience_task"
        assert task_decorator.queue == "convenience_queue"
        assert task_decorator.priority == TaskPriority.LOW
        assert task_decorator.max_retries == 1
        assert task_decorator.timeout == 60

    def test_convenience_task_usage_as_decorator(self):
        """Test using convenience task function as decorator."""

        @task(name="decorated_task", priority=TaskPriority.HIGH)
        def sample_task(x, y):
            return x * y

        assert isinstance(sample_task, Task)
        assert sample_task.name == "decorated_task"
        assert sample_task.priority == TaskPriority.HIGH
        assert sample_task.func is not None


class TestTaskExceptions:
    """Test task-related exception classes."""

    def test_task_failure_exception(self):
        """Test TaskFailure exception."""
        error_message = "Task execution failed"
        exc = TaskFailure(error_message)

        assert str(exc) == error_message
        assert isinstance(exc, Exception)

    def test_task_timeout_exception(self):
        """Test TaskTimeout exception."""
        timeout_message = "Task timed out after 30 seconds"
        exc = TaskTimeout(timeout_message)

        assert str(exc) == timeout_message
        assert isinstance(exc, Exception)

    def test_exceptions_are_distinct(self):
        """Test that TaskFailure and TaskTimeout are distinct exception types."""
        failure = TaskFailure("failure")
        timeout = TaskTimeout("timeout")

        assert type(failure) is not type(timeout)
        assert not isinstance(failure, TaskTimeout)
        assert not isinstance(timeout, TaskFailure)


class TestTaskServiceEdgeCases:
    """Test edge cases and error conditions in task service."""

    @pytest.mark.asyncio
    async def test_task_delay_with_no_queue_service(self):
        """Test task delay behavior when queue service is unavailable."""
        task_decorator = Task(name="test_task")
        task_decorator.func = lambda: None

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_get_queue.side_effect = Exception("Queue service unavailable")

            with pytest.raises(Exception, match="Queue service unavailable"):
                await task_decorator.delay(1, 2, 3)

    @pytest.mark.asyncio
    async def test_async_result_with_no_queue_service(self):
        """Test AsyncResult behavior when queue service is unavailable."""
        result = AsyncResult(uuid4())

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_get_queue.side_effect = Exception("Queue service unavailable")

            with pytest.raises(Exception, match="Queue service unavailable"):
                await result.get_status()

    def test_task_service_global_instance(self):
        """Test that task_service global instance exists and is TaskService."""
        from src.infrastructure.messaging.task_service import task_service

        assert isinstance(task_service, TaskService)

    @pytest.mark.asyncio
    async def test_send_task_with_uuid_task_id(self):
        """Test send_task with UUID task_id parameter."""
        task_id = uuid4()

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            result = await TaskService.send_task(task_name="test_task", task_id=task_id)

            # Verify the task_id was used
            call_args = mock_queue_service.send_task.call_args[0][0]
            assert call_args.task_id == task_id
            assert result.task_id == task_id

    @pytest.mark.asyncio
    async def test_task_with_complex_arguments(self):
        """Test task handling complex argument types."""
        task_decorator = Task(name="complex_task")
        task_decorator.func = lambda: None

        complex_args = [
            {"nested": {"data": [1, 2, 3]}},
            [1, "string", True, None],
            42,
            3.14159,
        ]

        complex_kwargs = {
            "dict_arg": {"key": "value"},
            "list_arg": [1, 2, 3],
            "str_arg": "test string",
            "num_arg": 123,
            "bool_arg": True,
            "none_arg": None,
        }

        with patch(
            'src.infrastructure.messaging.task_service.get_queue_service'
        ) as mock_get_queue:
            mock_queue_service = AsyncMock(spec=IQueueService)
            mock_get_queue.return_value = mock_queue_service

            result = await task_decorator.apply_async(
                args=complex_args, kwargs=complex_kwargs
            )

            # Verify complex arguments were passed correctly
            call_args = mock_queue_service.send_task.call_args[0][0]
            assert call_args.args == complex_args
            assert call_args.kwargs == complex_kwargs
            assert isinstance(result, AsyncResult)
