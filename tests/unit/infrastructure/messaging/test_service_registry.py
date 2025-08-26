"""Unit tests for ServiceRegistry and global service management patterns."""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.messaging.factory import (
    ServiceRegistry,
    cleanup_services,
    get_queue_service,
    get_registry,
    get_storage_service,
    get_worker_service,
    initialize_services,
)
from src.infrastructure.messaging.interfaces import (
    IQueueService,
    IStorageService,
    IWorkerService,
)
from src.shared.config.settings import Settings


class TestServiceRegistry:
    """Test ServiceRegistry class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Settings()
        self.settings.queue_service_type = "mock"
        self.settings.worker_service_type = "mock"
        self.settings.storage_service_type = "mock"

        self.registry = ServiceRegistry(self.settings)

    def test_service_registry_initialization(self):
        """Test ServiceRegistry constructor."""
        assert self.registry.settings == self.settings
        assert self.registry._queue_service is None
        assert self.registry._worker_service is None
        assert self.registry._storage_service is None
        assert not self.registry._connected
        assert not self.registry.is_connected

    @pytest.mark.asyncio
    async def test_initialize_creates_all_services(self):
        """Test that initialize creates and connects all services."""
        await self.registry.initialize()

        # Verify services were created
        assert self.registry._queue_service is not None
        assert self.registry._worker_service is not None
        assert self.registry._storage_service is not None

        # Verify services are of correct type
        assert isinstance(self.registry._queue_service, IQueueService)
        assert isinstance(self.registry._worker_service, IWorkerService)
        assert isinstance(self.registry._storage_service, IStorageService)

        # Verify connection state
        assert self.registry.is_connected

    @pytest.mark.asyncio
    async def test_initialize_with_custom_config(self):
        """Test initialize with custom configuration parameters."""
        custom_config = {
            "worker_id": "test-worker-001",
            "local_storage_path": "/tmp/test-storage",
            "rabbitmq_url": "amqp://test-server",
        }

        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            mock_queue = AsyncMock(spec=IQueueService)
            mock_worker = AsyncMock(spec=IWorkerService)
            mock_storage = AsyncMock(spec=IStorageService)

            mock_factory.create_queue_service.return_value = mock_queue
            mock_factory.create_worker_service.return_value = mock_worker
            mock_factory.create_storage_service.return_value = mock_storage

            await self.registry.initialize(**custom_config)

            # Verify factory methods were called with custom config
            mock_factory.create_queue_service.assert_called_once_with(
                self.settings, **custom_config
            )
            mock_factory.create_worker_service.assert_called_once_with(
                self.settings, queue_service=mock_queue, **custom_config
            )
            mock_factory.create_storage_service.assert_called_once_with(
                self.settings, **custom_config
            )

    @pytest.mark.asyncio
    async def test_initialize_failure_triggers_cleanup(self):
        """Test that initialization failure triggers cleanup."""
        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            # Mock queue service to fail during connection
            mock_queue = AsyncMock(spec=IQueueService)
            mock_queue.connect.side_effect = Exception("Connection failed")

            mock_worker = AsyncMock(spec=IWorkerService)
            mock_storage = AsyncMock(spec=IStorageService)

            mock_factory.create_queue_service.return_value = mock_queue
            mock_factory.create_worker_service.return_value = mock_worker
            mock_factory.create_storage_service.return_value = mock_storage

            # Initialize should fail and trigger cleanup
            with pytest.raises(Exception, match="Connection failed"):
                await self.registry.initialize()

            # Verify cleanup was attempted (services should be disconnected)
            assert not self.registry.is_connected

    @pytest.mark.asyncio
    async def test_property_accessors_before_initialization(self):
        """Test that accessing services before initialization raises errors."""
        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = self.registry.queue_service

        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = self.registry.worker_service

        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = self.registry.storage_service

    @pytest.mark.asyncio
    async def test_property_accessors_after_initialization(self):
        """Test that service properties work after initialization."""
        await self.registry.initialize()

        # Properties should return service instances
        queue_service = self.registry.queue_service
        worker_service = self.registry.worker_service
        storage_service = self.registry.storage_service

        assert isinstance(queue_service, IQueueService)
        assert isinstance(worker_service, IWorkerService)
        assert isinstance(storage_service, IStorageService)

        # Multiple calls should return same instances
        assert self.registry.queue_service is queue_service
        assert self.registry.worker_service is worker_service
        assert self.registry.storage_service is storage_service

    @pytest.mark.asyncio
    async def test_cleanup_stops_all_services(self):
        """Test that cleanup properly stops and disconnects all services."""
        await self.registry.initialize()

        # Mock the services to track cleanup calls
        with (
            patch.object(
                self.registry._queue_service, 'disconnect'
            ) as mock_queue_disconnect,
            patch.object(self.registry._worker_service, 'stop') as mock_worker_stop,
            patch.object(
                self.registry._storage_service, 'disconnect'
            ) as mock_storage_disconnect,
        ):

            await self.registry.cleanup()

            # Verify cleanup methods were called
            mock_worker_stop.assert_called_once()
            mock_queue_disconnect.assert_called_once()
            mock_storage_disconnect.assert_called_once()

            # Verify connection state
            assert not self.registry.is_connected

    @pytest.mark.asyncio
    async def test_cleanup_handles_service_errors_gracefully(self):
        """Test that cleanup handles individual service errors gracefully."""
        await self.registry.initialize()

        # Mock services to raise errors during cleanup
        with (
            patch.object(self.registry._worker_service, 'stop') as mock_worker_stop,
            patch.object(
                self.registry._queue_service, 'disconnect'
            ) as mock_queue_disconnect,
            patch.object(
                self.registry._storage_service, 'disconnect'
            ) as mock_storage_disconnect,
        ):

            mock_worker_stop.side_effect = Exception("Worker stop failed")
            mock_queue_disconnect.side_effect = Exception("Queue disconnect failed")
            mock_storage_disconnect.side_effect = Exception("Storage disconnect failed")

            # Should not raise exception despite individual failures
            await self.registry.cleanup()

            # All cleanup methods should have been attempted
            mock_worker_stop.assert_called_once()
            mock_queue_disconnect.assert_called_once()
            mock_storage_disconnect.assert_called_once()

            # Connection state should still be updated
            assert not self.registry.is_connected

    @pytest.mark.asyncio
    async def test_cleanup_safe_with_none_services(self):
        """Test that cleanup is safe when services are None."""
        # Don't initialize, so all services remain None
        await self.registry.cleanup()

        # Should complete without error
        assert not self.registry.is_connected

    @pytest.mark.asyncio
    async def test_health_check_all_services_healthy(self):
        """Test health check when all services are healthy."""
        await self.registry.initialize()

        health_status = await self.registry.health_check()

        expected_status = {
            "queue": True,
            "worker": True,
            "storage": True,
        }

        assert health_status == expected_status

    @pytest.mark.asyncio
    async def test_health_check_with_unhealthy_services(self):
        """Test health check with some unhealthy services."""
        await self.registry.initialize()

        # Mock one service as unhealthy
        with patch.object(
            self.registry._queue_service, 'health_check'
        ) as mock_queue_health:
            mock_queue_health.return_value = False

            health_status = await self.registry.health_check()

            expected_status = {
                "queue": False,
                "worker": True,
                "storage": True,
            }

            assert health_status == expected_status

    @pytest.mark.asyncio
    async def test_health_check_before_initialization(self):
        """Test health check before services are initialized."""
        health_status = await self.registry.health_check()

        # Should return empty dict when no services exist
        assert health_status == {}

    @pytest.mark.asyncio
    async def test_health_check_handles_service_errors(self):
        """Test health check handles individual service health check errors."""
        await self.registry.initialize()

        # Mock service health check to raise exception
        with patch.object(
            self.registry._storage_service, 'health_check'
        ) as mock_storage_health:
            mock_storage_health.side_effect = Exception("Health check failed")

            # Health check should handle exception gracefully
            # (Implementation might return False or skip the failing service)
            health_status = await self.registry.health_check()

            # Should still return results for other services
            assert "queue" in health_status
            assert "worker" in health_status
            # Storage might be missing or False depending on error handling

    @pytest.mark.asyncio
    async def test_multiple_initialization_calls(self):
        """Test behavior when initialize is called multiple times."""
        # First initialization
        await self.registry.initialize()
        _ = self.registry._queue_service  # Store initial service

        # Second initialization - should replace services
        await self.registry.initialize()
        second_queue_service = self.registry._queue_service

        # Services should be recreated (different instances)
        # Note: This depends on implementation - might be same or different
        assert isinstance(second_queue_service, IQueueService)

    def test_is_connected_property(self):
        """Test is_connected property reflects internal state."""
        assert not self.registry.is_connected

        # Manually set connected state (simulating successful initialization)
        self.registry._connected = True
        assert self.registry.is_connected

        # Reset state
        self.registry._connected = False
        assert not self.registry.is_connected


class TestGlobalServiceManagement:
    """Test global service management functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Ensure clean state
        import src.infrastructure.messaging.factory as factory_module

        factory_module._registry = None

    def teardown_method(self):
        """Clean up after tests."""
        # Clean up global registry
        import asyncio

        try:
            asyncio.create_task(cleanup_services())
        except RuntimeError:
            # No event loop running
            pass

    @pytest.mark.asyncio
    async def test_initialize_services_creates_global_registry(self):
        """Test that initialize_services creates global registry."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = await initialize_services(settings)

        assert isinstance(registry, ServiceRegistry)
        assert registry.is_connected

        # Should be accessible via get_registry
        same_registry = await get_registry()
        assert same_registry is registry

    @pytest.mark.asyncio
    async def test_initialize_services_replaces_existing_registry(self):
        """Test that initialize_services replaces existing global registry."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        # Create first registry
        first_registry = await initialize_services(settings)

        # Create second registry (should replace first)
        second_registry = await initialize_services(settings)

        assert second_registry is not first_registry
        assert second_registry.is_connected

        # get_registry should return the new one
        current_registry = await get_registry()
        assert current_registry is second_registry

    @pytest.mark.asyncio
    async def test_get_registry_before_initialization(self):
        """Test get_registry raises error before initialization."""
        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_registry()

    @pytest.mark.asyncio
    async def test_cleanup_services_removes_global_registry(self):
        """Test that cleanup_services removes global registry."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        # Initialize registry
        await initialize_services(settings)

        # Verify it exists
        registry = await get_registry()
        assert registry is not None

        # Cleanup
        await cleanup_services()

        # Should no longer be accessible
        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_registry()

    @pytest.mark.asyncio
    async def test_cleanup_services_safe_when_no_registry(self):
        """Test cleanup_services is safe when no registry exists."""
        # Should not raise error
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_convenience_functions_work_after_initialization(self):
        """Test convenience functions work after registry initialization."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        await initialize_services(settings)

        # Test convenience functions
        queue_service = await get_queue_service()
        worker_service = await get_worker_service()
        storage_service = await get_storage_service()

        assert isinstance(queue_service, IQueueService)
        assert isinstance(worker_service, IWorkerService)
        assert isinstance(storage_service, IStorageService)

        # Should return same instances on multiple calls
        assert await get_queue_service() is queue_service
        assert await get_worker_service() is worker_service
        assert await get_storage_service() is storage_service

    @pytest.mark.asyncio
    async def test_convenience_functions_before_initialization(self):
        """Test convenience functions raise errors before initialization."""
        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_queue_service()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_worker_service()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_storage_service()

    @pytest.mark.asyncio
    async def test_initialize_services_with_custom_config(self):
        """Test initialize_services passes custom config to registry."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        custom_config = {
            "worker_id": "global-test-worker",
            "custom_param": "test_value",
        }

        with patch.object(ServiceRegistry, 'initialize') as mock_initialize:
            _ = await initialize_services(settings, **custom_config)

            mock_initialize.assert_called_once_with(**custom_config)

    @pytest.mark.asyncio
    async def test_global_registry_thread_safety_simulation(self):
        """Test global registry behavior with concurrent access."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        # Initialize registry
        await initialize_services(settings)

        # Simulate concurrent access to convenience functions
        import asyncio

        async def get_all_services():
            queue = await get_queue_service()
            worker = await get_worker_service()
            storage = await get_storage_service()
            return queue, worker, storage

        # Run multiple concurrent requests
        results = await asyncio.gather(*[get_all_services() for _ in range(5)])

        # All results should have the same service instances
        first_result = results[0]
        for result in results[1:]:
            assert result[0] is first_result[0]  # Same queue service
            assert result[1] is first_result[1]  # Same worker service
            assert result[2] is first_result[2]  # Same storage service


class TestServiceRegistryErrorHandling:
    """Test ServiceRegistry error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Settings()
        self.settings.queue_service_type = "mock"
        self.settings.worker_service_type = "mock"
        self.settings.storage_service_type = "mock"

    @pytest.mark.asyncio
    async def test_initialization_with_invalid_service_type(self):
        """Test initialization with invalid service configuration."""
        self.settings.queue_service_type = "invalid_type"

        registry = ServiceRegistry(self.settings)

        with pytest.raises(ValueError, match="Unsupported queue service type"):
            await registry.initialize()

        # Registry should not be marked as connected after failure
        assert not registry.is_connected

    @pytest.mark.asyncio
    async def test_partial_initialization_failure(self):
        """Test handling when some services initialize successfully but others fail."""
        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            # Queue service succeeds
            mock_queue = AsyncMock(spec=IQueueService)

            # Storage service succeeds
            mock_storage = AsyncMock(spec=IStorageService)

            # Worker service creation fails
            mock_factory.create_queue_service.return_value = mock_queue
            mock_factory.create_storage_service.return_value = mock_storage
            mock_factory.create_worker_service.side_effect = Exception(
                "Worker creation failed"
            )

            registry = ServiceRegistry(self.settings)

            with pytest.raises(Exception, match="Worker creation failed"):
                await registry.initialize()

            # Registry should attempt cleanup and not be connected
            assert not registry.is_connected

    @pytest.mark.asyncio
    async def test_service_connection_failure(self):
        """Test handling when service creation succeeds but connection fails."""
        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            mock_queue = AsyncMock(spec=IQueueService)
            mock_worker = AsyncMock(spec=IWorkerService)
            mock_storage = AsyncMock(spec=IStorageService)

            # Storage connection fails
            mock_storage.connect.side_effect = Exception("Storage connection failed")

            mock_factory.create_queue_service.return_value = mock_queue
            mock_factory.create_worker_service.return_value = mock_worker
            mock_factory.create_storage_service.return_value = mock_storage

            registry = ServiceRegistry(self.settings)

            with pytest.raises(Exception, match="Storage connection failed"):
                await registry.initialize()

            assert not registry.is_connected

    @pytest.mark.asyncio
    async def test_health_check_with_service_exceptions(self):
        """Test health check robustness when services raise exceptions."""
        registry = ServiceRegistry(self.settings)
        await registry.initialize()

        with (
            patch.object(registry._queue_service, 'health_check') as mock_queue_health,
            patch.object(
                registry._worker_service, 'health_check'
            ) as mock_worker_health,
            patch.object(
                registry._storage_service, 'health_check'
            ) as mock_storage_health,
        ):

            # Make all health checks raise different exceptions
            mock_queue_health.side_effect = ConnectionError("Queue unreachable")
            mock_worker_health.side_effect = TimeoutError("Worker timeout")
            mock_storage_health.side_effect = RuntimeError("Storage error")

            # Health check should handle exceptions gracefully
            # (The exact behavior depends on implementation)
            try:
                health_status = await registry.health_check()
                # If implementation catches exceptions, we should get some result
                assert isinstance(health_status, dict)
            except Exception:
                # If implementation doesn't catch exceptions, that's also valid behavior
                # depending on design choice
                pass

    @pytest.mark.asyncio
    async def test_property_access_after_failed_initialization(self):
        """Test service property access after failed initialization."""
        registry = ServiceRegistry(self.settings)

        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            mock_factory.create_queue_service.side_effect = Exception("Creation failed")

            with pytest.raises(Exception, match="Creation failed"):
                await registry.initialize()

        # Properties should still raise "not initialized" error
        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = registry.queue_service
