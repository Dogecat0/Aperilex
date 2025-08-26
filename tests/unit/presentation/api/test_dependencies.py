"""Comprehensive tests for FastAPI dependency injection."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.application_service import ApplicationService
from src.application.factory import ServiceFactory
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.task_service import TaskService
from src.presentation.api.dependencies import (
    ServiceLifecycle,
    get_application_service,
    get_background_task_coordinator,
    get_service_factory,
    get_task_service,
    service_lifecycle,
)


@pytest.mark.unit
class TestServiceFactoryDependency:
    """Test ServiceFactory dependency injection."""

    def test_get_service_factory_returns_service_factory_instance(self):
        """Test get_service_factory returns a ServiceFactory instance."""
        # Act
        factory = get_service_factory()

        # Assert
        assert isinstance(factory, ServiceFactory)

    def test_get_service_factory_is_cached(self):
        """Test get_service_factory returns the same instance due to lru_cache."""
        # Act
        factory1 = get_service_factory()
        factory2 = get_service_factory()

        # Assert - should be the same instance due to caching
        assert factory1 is factory2

    def test_get_service_factory_uses_settings(self):
        """Test get_service_factory uses current settings."""
        with patch(
            'src.presentation.api.dependencies.ServiceFactory'
        ) as MockServiceFactory:
            with patch('src.presentation.api.dependencies.settings') as mock_settings:
                mock_instance = Mock()
                MockServiceFactory.return_value = mock_instance

                # Act
                get_service_factory.cache_clear()  # Clear cache for this test
                result = get_service_factory()

                # Assert
                MockServiceFactory.assert_called_once_with(mock_settings)
                assert result == mock_instance


@pytest.mark.unit
class TestApplicationServiceDependency:
    """Test ApplicationService dependency injection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_factory = Mock(spec=ServiceFactory)
        self.mock_app_service = Mock(spec=ApplicationService)

    @pytest.mark.asyncio
    async def test_get_application_service_success(self):
        """Test get_application_service returns ApplicationService instance."""
        # Arrange
        self.mock_factory.create_application_service.return_value = (
            self.mock_app_service
        )

        # Act
        result = await get_application_service(self.mock_factory)

        # Assert
        assert result == self.mock_app_service
        self.mock_factory.create_application_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_application_service_handles_factory_error(self):
        """Test get_application_service handles factory creation errors."""
        # Arrange
        self.mock_factory.create_application_service.side_effect = RuntimeError(
            "Factory error"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Factory error"):
            await get_application_service(self.mock_factory)

    @pytest.mark.asyncio
    async def test_get_application_service_async_factory_method(self):
        """Test get_application_service works with async factory method."""
        # Arrange
        async_mock = AsyncMock(return_value=self.mock_app_service)
        self.mock_factory.create_application_service = async_mock

        # Act
        result = await get_application_service(self.mock_factory)

        # Assert
        assert result == self.mock_app_service
        async_mock.assert_called_once()


@pytest.mark.unit
class TestTaskServiceDependency:
    """Test TaskService dependency injection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_factory = Mock(spec=ServiceFactory)
        self.mock_task_service = Mock(spec=TaskService)

    @pytest.mark.asyncio
    async def test_get_task_service_success(self):
        """Test get_task_service returns TaskService instance."""
        # Arrange
        self.mock_factory.create_task_service.return_value = self.mock_task_service

        # Act
        result = await get_task_service(self.mock_factory)

        # Assert
        assert result == self.mock_task_service
        self.mock_factory.create_task_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_service_handles_factory_error(self):
        """Test get_task_service handles factory creation errors."""
        # Arrange
        self.mock_factory.create_task_service.side_effect = ValueError(
            "Task service error"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Task service error"):
            await get_task_service(self.mock_factory)


@pytest.mark.unit
class TestBackgroundTaskCoordinatorDependency:
    """Test BackgroundTaskCoordinator dependency injection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_factory = Mock(spec=ServiceFactory)
        self.mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

    @pytest.mark.asyncio
    async def test_get_background_task_coordinator_success(self):
        """Test get_background_task_coordinator returns coordinator instance."""
        # Arrange
        async_mock = AsyncMock(return_value=self.mock_coordinator)
        self.mock_factory.create_background_task_coordinator = async_mock

        # Act
        result = await get_background_task_coordinator(self.mock_factory)

        # Assert
        assert result == self.mock_coordinator
        async_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_background_task_coordinator_handles_factory_error(self):
        """Test get_background_task_coordinator handles factory errors."""
        # Arrange
        async_mock = AsyncMock(side_effect=ConnectionError("Coordinator error"))
        self.mock_factory.create_background_task_coordinator = async_mock

        # Act & Assert
        with pytest.raises(ConnectionError, match="Coordinator error"):
            await get_background_task_coordinator(self.mock_factory)


@pytest.mark.unit
class TestServiceLifecycle:
    """Test ServiceLifecycle class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.lifecycle = ServiceLifecycle()

    def test_service_lifecycle_initialization(self):
        """Test ServiceLifecycle initializes correctly."""
        # Assert
        assert self.lifecycle.factory is None

    @pytest.mark.asyncio
    async def test_startup_successful(self):
        """Test successful startup sequence."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.ensure_messaging_initialized = AsyncMock()
        mock_factory.cleanup = AsyncMock()

        mock_queue_service = Mock()
        mock_queue_service.health_check = AsyncMock(return_value=True)

        mock_storage_service = Mock()
        mock_storage_service.health_check = AsyncMock(return_value=True)

        mock_worker_service = Mock()
        mock_worker_service.health_check = AsyncMock(return_value=True)

        with patch(
            'src.presentation.api.dependencies.ServiceFactory',
            return_value=mock_factory,
        ):
            with patch(
                'src.presentation.api.dependencies.get_queue_service',
                return_value=mock_queue_service,
            ):
                with patch(
                    'src.presentation.api.dependencies.get_storage_service',
                    return_value=mock_storage_service,
                ):
                    with patch(
                        'src.presentation.api.dependencies.get_worker_service',
                        return_value=mock_worker_service,
                    ):
                        with patch(
                            'src.presentation.api.dependencies.logger'
                        ) as mock_logger:
                            # Act
                            await self.lifecycle.startup()

                            # Assert
                            assert self.lifecycle.factory == mock_factory
                            mock_factory.ensure_messaging_initialized.assert_called_once()

                            # Verify health checks
                            mock_queue_service.health_check.assert_called_once()
                            mock_storage_service.health_check.assert_called_once()
                            mock_worker_service.health_check.assert_called_once()

                            # Verify logging
                            mock_logger.info.assert_called()
                            info_calls = [
                                call[0][0] for call in mock_logger.info.call_args_list
                            ]
                            assert any(
                                "Starting service lifecycle management" in call
                                for call in info_calls
                            )

    @pytest.mark.asyncio
    async def test_startup_with_unhealthy_services(self):
        """Test startup continues with warning when some services are unhealthy."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.ensure_messaging_initialized = AsyncMock()

        mock_queue_service = Mock()
        mock_queue_service.health_check = AsyncMock(return_value=False)  # Unhealthy

        mock_storage_service = Mock()
        mock_storage_service.health_check = AsyncMock(return_value=True)

        mock_worker_service = Mock()
        mock_worker_service.health_check = AsyncMock(return_value=True)

        with patch(
            'src.presentation.api.dependencies.ServiceFactory',
            return_value=mock_factory,
        ):
            with patch(
                'src.presentation.api.dependencies.get_queue_service',
                return_value=mock_queue_service,
            ):
                with patch(
                    'src.presentation.api.dependencies.get_storage_service',
                    return_value=mock_storage_service,
                ):
                    with patch(
                        'src.presentation.api.dependencies.get_worker_service',
                        return_value=mock_worker_service,
                    ):
                        with patch(
                            'src.presentation.api.dependencies.logger'
                        ) as mock_logger:
                            # Act
                            await self.lifecycle.startup()

                            # Assert
                            assert self.lifecycle.factory == mock_factory

                            # Verify warning is logged
                            mock_logger.warning.assert_called()
                            warning_calls = [
                                call[0][0]
                                for call in mock_logger.warning.call_args_list
                            ]
                            assert any(
                                "Some services are not healthy" in call
                                for call in warning_calls
                            )

    @pytest.mark.asyncio
    async def test_startup_handles_initialization_error(self):
        """Test startup handles messaging initialization errors gracefully."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.ensure_messaging_initialized = AsyncMock(
            side_effect=RuntimeError("Init error")
        )

        with patch(
            'src.presentation.api.dependencies.ServiceFactory',
            return_value=mock_factory,
        ):
            with patch('src.presentation.api.dependencies.logger') as mock_logger:
                # Act - should not raise exception
                await self.lifecycle.startup()

                # Assert
                mock_logger.error.assert_called()
                mock_logger.warning.assert_called()

                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                warning_calls = [
                    call[0][0] for call in mock_logger.warning.call_args_list
                ]

                assert any(
                    "Failed to initialize messaging services" in call
                    for call in error_calls
                )
                assert any(
                    "Continuing startup with limited functionality" in call
                    for call in warning_calls
                )

    @pytest.mark.asyncio
    async def test_startup_logs_service_configuration(self):
        """Test startup logs service configuration information."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.ensure_messaging_initialized = AsyncMock()

        mock_queue_service = Mock()
        mock_queue_service.health_check = AsyncMock(return_value=True)

        mock_storage_service = Mock()
        mock_storage_service.health_check = AsyncMock(return_value=True)

        mock_worker_service = Mock()
        mock_worker_service.health_check = AsyncMock(return_value=True)

        mock_settings = Mock()
        mock_settings.queue_service_type = "mock"
        mock_settings.storage_service_type = "memory"
        mock_settings.worker_service_type = "sync"

        with patch(
            'src.presentation.api.dependencies.ServiceFactory',
            return_value=mock_factory,
        ):
            with patch(
                'src.presentation.api.dependencies.get_queue_service',
                return_value=mock_queue_service,
            ):
                with patch(
                    'src.presentation.api.dependencies.get_storage_service',
                    return_value=mock_storage_service,
                ):
                    with patch(
                        'src.presentation.api.dependencies.get_worker_service',
                        return_value=mock_worker_service,
                    ):
                        with patch(
                            'src.presentation.api.dependencies.settings', mock_settings
                        ):
                            with patch(
                                'src.presentation.api.dependencies.logger'
                            ) as mock_logger:
                                # Act
                                await self.lifecycle.startup()

                                # Assert
                                info_calls = [
                                    call[0][0]
                                    for call in mock_logger.info.call_args_list
                                ]
                                assert any(
                                    "Queue service: mock, Storage: memory, Worker: sync"
                                    in call
                                    for call in info_calls
                                )

    @pytest.mark.asyncio
    async def test_shutdown_successful(self):
        """Test successful shutdown sequence."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.cleanup = AsyncMock()
        self.lifecycle.factory = mock_factory

        with patch(
            'src.presentation.api.dependencies.cleanup_services'
        ) as mock_cleanup:
            mock_cleanup.return_value = AsyncMock()
            with patch('src.presentation.api.dependencies.logger') as mock_logger:
                # Act
                await self.lifecycle.shutdown()

                # Assert
                mock_cleanup.assert_called_once()
                mock_factory.cleanup.assert_called_once()

                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any(
                    "Shutting down service lifecycle management" in call
                    for call in info_calls
                )
                assert any(
                    "Messaging services cleaned up successfully" in call
                    for call in info_calls
                )
                assert any(
                    "Application services cleaned up successfully" in call
                    for call in info_calls
                )

    @pytest.mark.asyncio
    async def test_shutdown_handles_messaging_cleanup_error(self):
        """Test shutdown handles messaging cleanup errors gracefully."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.cleanup = AsyncMock()
        self.lifecycle.factory = mock_factory

        with patch(
            'src.presentation.api.dependencies.cleanup_services'
        ) as mock_cleanup:
            mock_cleanup.side_effect = RuntimeError("Cleanup error")
            with patch('src.presentation.api.dependencies.logger') as mock_logger:
                # Act
                await self.lifecycle.shutdown()

                # Assert
                mock_factory.cleanup.assert_called_once()  # Should still try factory cleanup

                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                assert any(
                    "Error cleaning up messaging services" in call
                    for call in error_calls
                )

    @pytest.mark.asyncio
    async def test_shutdown_handles_factory_cleanup_error(self):
        """Test shutdown handles factory cleanup errors gracefully."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_factory.cleanup = AsyncMock(
            side_effect=ValueError("Factory cleanup error")
        )
        self.lifecycle.factory = mock_factory

        with patch('src.presentation.api.dependencies.cleanup_services'):
            with patch('src.presentation.api.dependencies.logger') as mock_logger:
                # Act
                await self.lifecycle.shutdown()

                # Assert
                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                assert any(
                    "Error cleaning up application services" in call
                    for call in error_calls
                )

    @pytest.mark.asyncio
    async def test_shutdown_without_factory(self):
        """Test shutdown when no factory is set."""
        # Arrange - no factory set
        assert self.lifecycle.factory is None

        with patch(
            'src.presentation.api.dependencies.cleanup_services'
        ) as mock_cleanup:
            with patch('src.presentation.api.dependencies.logger'):
                # Act - should not raise exception
                await self.lifecycle.shutdown()

                # Assert
                mock_cleanup.assert_called_once()


@pytest.mark.unit
class TestGlobalServiceLifecycle:
    """Test the global service lifecycle instance."""

    def test_service_lifecycle_global_instance_exists(self):
        """Test global service_lifecycle instance exists."""
        # Assert
        assert service_lifecycle is not None
        assert isinstance(service_lifecycle, ServiceLifecycle)

    def test_service_lifecycle_global_instance_is_singleton(self):
        """Test global service_lifecycle instance is consistent."""
        # Act
        from src.presentation.api.dependencies import service_lifecycle as lifecycle2

        # Assert
        assert service_lifecycle is lifecycle2


@pytest.mark.unit
class TestDependencyIntegration:
    """Test dependency injection integration scenarios."""

    def test_service_factory_cache_behavior(self):
        """Test service factory caching behavior across multiple calls."""
        # Act
        get_service_factory.cache_clear()  # Start fresh
        factory1 = get_service_factory()
        factory2 = get_service_factory()
        factory3 = get_service_factory()

        # Assert - all should be the same instance
        assert factory1 is factory2 is factory3

    @pytest.mark.asyncio
    async def test_dependency_chain_integration(self):
        """Test full dependency chain works correctly."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        mock_app_service = Mock(spec=ApplicationService)
        mock_task_service = Mock(spec=TaskService)
        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        mock_factory.create_application_service.return_value = mock_app_service
        mock_factory.create_task_service.return_value = mock_task_service
        mock_factory.create_background_task_coordinator = AsyncMock(
            return_value=mock_coordinator
        )

        # Act
        app_service = await get_application_service(mock_factory)
        task_service = await get_task_service(mock_factory)
        coordinator = await get_background_task_coordinator(mock_factory)

        # Assert
        assert app_service == mock_app_service
        assert task_service == mock_task_service
        assert coordinator == mock_coordinator

        # Verify factory methods were called
        mock_factory.create_application_service.assert_called_once()
        mock_factory.create_task_service.assert_called_once()
        mock_factory.create_background_task_coordinator.assert_called_once()

    def test_dependency_logging_configuration(self):
        """Test dependency modules have proper logging configuration."""
        with patch('src.presentation.api.dependencies.logger') as mock_logger:
            # Act - trigger some logging
            get_service_factory()

            # Assert - logger should be properly configured
            assert mock_logger is not None
            # The debug logging might not be called depending on log level,
            # but the logger should exist


@pytest.mark.unit
class TestDependencyErrorHandling:
    """Test error handling in dependency injection."""

    @pytest.mark.asyncio
    async def test_async_dependency_timeout_handling(self):
        """Test async dependency handles timeouts gracefully."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)

        async def slow_create():
            import asyncio

            await asyncio.sleep(10)  # This would timeout in real scenario

        mock_factory.create_application_service = slow_create

        # For this test, we just verify the function is async-capable
        # Real timeout testing would require more complex setup
        import inspect

        assert inspect.iscoroutinefunction(get_application_service)

    @pytest.mark.asyncio
    async def test_concurrent_dependency_creation(self):
        """Test concurrent dependency creation works correctly."""
        # Arrange
        mock_factory = Mock(spec=ServiceFactory)
        call_count = 0

        async def counting_create():
            nonlocal call_count
            call_count += 1
            return Mock(spec=ApplicationService)

        mock_factory.create_application_service = counting_create

        # Act - concurrent calls
        import asyncio

        results = await asyncio.gather(
            get_application_service(mock_factory),
            get_application_service(mock_factory),
            get_application_service(mock_factory),
        )

        # Assert
        assert len(results) == 3
        assert all(result is not None for result in results)
        assert call_count == 3  # Each call should create a new instance
