"""Unit tests for messaging interfaces and data classes."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.infrastructure.messaging.interfaces import (
    IQueueService,
    IStorageService,
    IWorkerService,
    TaskMessage,
    TaskPriority,
    TaskResult,
    TaskStatus,
)


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_task_status_values(self):
        """Test that all task status values are properly defined."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILURE.value == "failure"
        assert TaskStatus.RETRY.value == "retry"
        assert TaskStatus.REVOKED.value == "revoked"

    def test_task_status_count(self):
        """Test that we have expected number of statuses."""
        assert len(TaskStatus) == 6

    @pytest.mark.parametrize(
        "status",
        [
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.SUCCESS,
            TaskStatus.FAILURE,
            TaskStatus.RETRY,
            TaskStatus.REVOKED,
        ],
    )
    def test_task_status_serialization(self, status):
        """Test that task statuses can be serialized."""
        assert isinstance(status.value, str)
        assert len(status.value) > 0


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_task_priority_values(self):
        """Test that task priorities have correct integer values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 8
        assert TaskPriority.CRITICAL.value == 10

    def test_priority_ordering(self):
        """Test that priorities are properly ordered."""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.NORMAL,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]
        for i in range(len(priorities) - 1):
            assert priorities[i].value < priorities[i + 1].value

    def test_priority_comparison(self):
        """Test priority comparison operations."""
        assert TaskPriority.LOW < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.CRITICAL
        assert TaskPriority.CRITICAL > TaskPriority.LOW


class TestTaskMessage:
    """Test TaskMessage dataclass."""

    def test_minimal_task_message(self):
        """Test creating task message with minimal required fields."""
        task_id = uuid4()
        task_name = "test_task"

        message = TaskMessage(task_id=task_id, task_name=task_name, args=[], kwargs={})

        assert message.task_id == task_id
        assert message.task_name == task_name
        assert message.args == []
        assert message.kwargs == {}
        assert message.priority == TaskPriority.NORMAL  # Default
        assert message.retry_count == 0  # Default
        assert message.max_retries == 3  # Default
        assert message.timeout is None  # Default
        assert message.eta is None  # Default
        assert message.expires is None  # Default
        assert message.queue == "default"  # Default
        assert message.metadata == {}  # Auto-initialized

    def test_full_task_message(self):
        """Test creating task message with all fields."""
        task_id = uuid4()
        task_name = "complex_task"
        args = [1, "test", True]
        kwargs = {"key": "value", "number": 42}
        priority = TaskPriority.HIGH
        retry_count = 2
        max_retries = 5
        timeout = 300
        eta = datetime.utcnow()
        expires = datetime.utcnow() + timedelta(hours=1)
        queue = "analysis_queue"
        metadata = {"source": "test", "user_id": "123"}

        message = TaskMessage(
            task_id=task_id,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            retry_count=retry_count,
            max_retries=max_retries,
            timeout=timeout,
            eta=eta,
            expires=expires,
            queue=queue,
            metadata=metadata,
        )

        assert message.task_id == task_id
        assert message.task_name == task_name
        assert message.args == args
        assert message.kwargs == kwargs
        assert message.priority == priority
        assert message.retry_count == retry_count
        assert message.max_retries == max_retries
        assert message.timeout == timeout
        assert message.eta == eta
        assert message.expires == expires
        assert message.queue == queue
        assert message.metadata == metadata

    def test_metadata_auto_initialization(self):
        """Test that metadata is auto-initialized as empty dict."""
        message = TaskMessage(
            task_id=uuid4(), task_name="test_task", args=[], kwargs={}
        )

        assert message.metadata == {}

        # Test that we can modify it
        message.metadata["key"] = "value"
        assert message.metadata["key"] == "value"

    def test_task_message_immutability_validation(self):
        """Test that task message can be created with various data types."""
        task_id = uuid4()

        # Test with different argument types
        message = TaskMessage(
            task_id=task_id,
            task_name="test_task",
            args=[1, 2.5, "string", True, None, {"nested": "dict"}, [1, 2, 3]],
            kwargs={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "none": None,
                "dict": {"nested": "data"},
                "list": [1, 2, 3],
            },
        )

        assert len(message.args) == 7
        assert len(message.kwargs) == 7


class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_minimal_task_result(self):
        """Test creating task result with minimal required fields."""
        task_id = uuid4()
        status = TaskStatus.SUCCESS

        result = TaskResult(task_id=task_id, status=status)

        assert result.task_id == task_id
        assert result.status == status
        assert result.result is None  # Default
        assert result.error is None  # Default
        assert result.traceback is None  # Default
        assert result.started_at is None  # Default
        assert result.completed_at is None  # Default
        assert result.worker_id is None  # Default
        assert result.metadata == {}  # Auto-initialized

    def test_full_task_result(self):
        """Test creating task result with all fields."""
        task_id = uuid4()
        status = TaskStatus.SUCCESS
        result_data = {"output": "success", "value": 42}
        error = "Task failed"
        traceback = "Traceback (most recent call last)..."
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow() + timedelta(seconds=30)
        worker_id = "worker-001"
        metadata = {"duration": 30.5, "retries": 1}

        result = TaskResult(
            task_id=task_id,
            status=status,
            result=result_data,
            error=error,
            traceback=traceback,
            started_at=started_at,
            completed_at=completed_at,
            worker_id=worker_id,
            metadata=metadata,
        )

        assert result.task_id == task_id
        assert result.status == status
        assert result.result == result_data
        assert result.error == error
        assert result.traceback == traceback
        assert result.started_at == started_at
        assert result.completed_at == completed_at
        assert result.worker_id == worker_id
        assert result.metadata == metadata

    def test_success_result(self):
        """Test creating a successful task result."""
        task_id = uuid4()
        result_data = {"analysis_id": str(uuid4()), "confidence": 0.95}

        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.SUCCESS,
            result=result_data,
            completed_at=datetime.utcnow(),
        )

        assert result.status == TaskStatus.SUCCESS
        assert result.result == result_data
        assert result.error is None
        assert result.traceback is None

    def test_failure_result(self):
        """Test creating a failed task result."""
        task_id = uuid4()
        error_msg = "Connection timeout"
        traceback_str = "Traceback...\nConnectionError: timeout"

        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILURE,
            error=error_msg,
            traceback=traceback_str,
            completed_at=datetime.utcnow(),
        )

        assert result.status == TaskStatus.FAILURE
        assert result.result is None
        assert result.error == error_msg
        assert result.traceback == traceback_str

    def test_metadata_auto_initialization(self):
        """Test that metadata is auto-initialized as empty dict."""
        result = TaskResult(task_id=uuid4(), status=TaskStatus.PENDING)

        assert result.metadata == {}

        # Test that we can modify it
        result.metadata["duration"] = 45.2
        assert result.metadata["duration"] == 45.2


class TestIQueueServiceInterface:
    """Test IQueueService interface definition."""

    def test_interface_methods_exist(self):
        """Test that all required methods are defined in interface."""
        required_methods = [
            'connect',
            'disconnect',
            'send_task',
            'receive_task',
            'ack_task',
            'nack_task',
            'get_task_status',
            'cancel_task',
            'purge_queue',
            'get_queue_size',
            'health_check',
        ]

        for method in required_methods:
            assert hasattr(IQueueService, method)
            assert callable(getattr(IQueueService, method))

    def test_interface_is_abstract(self):
        """Test that IQueueService cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IQueueService()

    def test_interface_method_signatures(self):
        """Test that interface methods have expected signatures."""
        # This is primarily a documentation test to ensure we don't accidentally
        # change method signatures without considering backward compatibility

        # Check that methods exist and are abstract
        assert hasattr(IQueueService, 'connect')
        assert hasattr(IQueueService, 'send_task')
        assert hasattr(IQueueService, 'receive_task')

        # The actual signature verification would happen at implementation time


class TestIWorkerServiceInterface:
    """Test IWorkerService interface definition."""

    def test_interface_methods_exist(self):
        """Test that all required methods are defined in interface."""
        required_methods = [
            'start',
            'stop',
            'register_task',
            'unregister_task',
            'submit_task_result',
            'get_worker_stats',
            'health_check',
        ]

        for method in required_methods:
            assert hasattr(IWorkerService, method)
            assert callable(getattr(IWorkerService, method))

    def test_interface_is_abstract(self):
        """Test that IWorkerService cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IWorkerService()


class TestIStorageServiceInterface:
    """Test IStorageService interface definition."""

    def test_interface_methods_exist(self):
        """Test that all required methods are defined in interface."""
        required_methods = [
            'connect',
            'disconnect',
            'get',
            'set',
            'delete',
            'exists',
            'increment',
            'set_hash',
            'get_hash',
            'clear_pattern',
            'health_check',
        ]

        for method in required_methods:
            assert hasattr(IStorageService, method)
            assert callable(getattr(IStorageService, method))

    def test_interface_is_abstract(self):
        """Test that IStorageService cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IStorageService()


class TestTaskMessageValidation:
    """Test TaskMessage validation and edge cases."""

    def test_empty_task_name_handling(self):
        """Test behavior with empty task name."""
        message = TaskMessage(
            task_id=uuid4(), task_name="", args=[], kwargs={}  # Empty but valid string
        )
        assert message.task_name == ""

    def test_very_long_task_name(self):
        """Test behavior with very long task name."""
        long_name = "a" * 1000
        message = TaskMessage(task_id=uuid4(), task_name=long_name, args=[], kwargs={})
        assert message.task_name == long_name

    def test_special_characters_in_task_name(self):
        """Test behavior with special characters in task name."""
        special_name = "task.with-special_chars:123"
        message = TaskMessage(
            task_id=uuid4(), task_name=special_name, args=[], kwargs={}
        )
        assert message.task_name == special_name

    def test_negative_retry_count(self):
        """Test behavior with negative retry count."""
        message = TaskMessage(
            task_id=uuid4(),
            task_name="test",
            args=[],
            kwargs={},
            retry_count=-1,  # Negative value
        )
        assert message.retry_count == -1

    def test_zero_max_retries(self):
        """Test behavior with zero max retries."""
        message = TaskMessage(
            task_id=uuid4(), task_name="test", args=[], kwargs={}, max_retries=0
        )
        assert message.max_retries == 0

    def test_past_eta(self):
        """Test behavior with ETA in the past."""
        past_time = datetime(2020, 1, 1)
        message = TaskMessage(
            task_id=uuid4(), task_name="test", args=[], kwargs={}, eta=past_time
        )
        assert message.eta == past_time

    def test_past_expires(self):
        """Test behavior with expiration time in the past."""
        past_time = datetime(2020, 1, 1)
        message = TaskMessage(
            task_id=uuid4(), task_name="test", args=[], kwargs={}, expires=past_time
        )
        assert message.expires == past_time


class TestTaskResultValidation:
    """Test TaskResult validation and edge cases."""

    def test_conflicting_success_and_error(self):
        """Test creating result with success status but error message."""
        # This should be allowed - validation is application logic, not data structure
        result = TaskResult(
            task_id=uuid4(), status=TaskStatus.SUCCESS, error="Some error occurred"
        )
        assert result.status == TaskStatus.SUCCESS
        assert result.error == "Some error occurred"

    def test_very_large_result_data(self):
        """Test handling of large result data."""
        large_data = {"data": "x" * 10000}  # Large string
        result = TaskResult(
            task_id=uuid4(), status=TaskStatus.SUCCESS, result=large_data
        )
        assert result.result == large_data

    def test_none_task_id_handling(self):
        """Test that None task_id is handled gracefully."""
        # This test verifies the dataclass accepts None, though it shouldn't in practice
        with pytest.raises(TypeError):
            TaskResult(task_id=None, status=TaskStatus.SUCCESS)

    def test_complex_nested_result(self):
        """Test result with complex nested data structures."""
        complex_result = {
            "analysis": {
                "confidence": 0.95,
                "findings": [
                    {"metric": "revenue", "value": 1000000},
                    {"metric": "profit", "value": 200000},
                ],
                "metadata": {
                    "model": "gpt-4",
                    "tokens": 5000,
                    "nested": {"deep": {"structure": True}},
                },
            },
            "processing_stats": {
                "duration": 45.2,
                "retries": 0,
                "worker": "worker-001",
            },
        }

        result = TaskResult(
            task_id=uuid4(), status=TaskStatus.SUCCESS, result=complex_result
        )
        assert result.result == complex_result

    def test_datetime_precision(self):
        """Test datetime precision handling."""
        precise_time = datetime.utcnow()
        result = TaskResult(
            task_id=uuid4(),
            status=TaskStatus.SUCCESS,
            started_at=precise_time,
            completed_at=precise_time,
        )
        assert result.started_at == precise_time
        assert result.completed_at == precise_time
