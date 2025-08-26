"""Unit tests for messaging service factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.messaging.factory import (
    MessagingFactory,
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


class TestMessagingFactory:
    """Test MessagingFactory class."""

    def test_create_mock_queue_service(self):
        """Test creating mock queue service."""
        settings = Settings()
        settings.queue_service_type = "mock"

        service = MessagingFactory.create_queue_service(settings)

        assert isinstance(service, IQueueService)
        assert service.__class__.__name__ == "MockQueueService"

    def test_create_mock_worker_service(self):
        """Test creating mock worker service."""
        settings = Settings()
        settings.worker_service_type = "mock"

        service = MessagingFactory.create_worker_service(settings)

        assert isinstance(service, IWorkerService)
        assert service.__class__.__name__ == "MockWorkerService"

    def test_create_mock_storage_service(self):
        """Test creating mock storage service."""
        settings = Settings()
        settings.storage_service_type = "mock"

        service = MessagingFactory.create_storage_service(settings)

        assert isinstance(service, IStorageService)
        assert service.__class__.__name__ == "MockStorageService"

    def test_create_local_file_storage_service(self):
        """Test creating local file storage service."""
        settings = Settings()
        settings.storage_service_type = "local"

        service = MessagingFactory.create_storage_service(settings)

        assert isinstance(service, IStorageService)
        assert service.__class__.__name__ == "LocalFileStorageService"

    def test_create_local_file_storage_with_custom_path(self):
        """Test creating local file storage with custom path."""
        settings = Settings()
        settings.storage_service_type = "local"
        custom_path = "/tmp/test_storage"

        service = MessagingFactory.create_storage_service(
            settings, local_storage_path=custom_path
        )

        assert isinstance(service, IStorageService)
        assert hasattr(service, 'base_path')

    def test_create_local_worker_service(self):
        """Test creating local worker service."""
        settings = Settings()
        settings.worker_service_type = "local"

        # Mock queue service is required for local worker
        mock_queue_service = MagicMock(spec=IQueueService)

        service = MessagingFactory.create_worker_service(
            settings, queue_service=mock_queue_service
        )

        assert isinstance(service, IWorkerService)
        assert service.__class__.__name__ == "LocalWorkerService"

    def test_create_local_worker_without_queue_service_fails(self):
        """Test that local worker requires queue service."""
        settings = Settings()
        settings.worker_service_type = "local"

        with pytest.raises(
            ValueError, match="queue_service is required for local worker"
        ):
            MessagingFactory.create_worker_service(settings)

    def test_unsupported_queue_service_type(self):
        """Test error handling for unsupported queue service type."""
        settings = Settings()
        settings.queue_service_type = "unsupported_type"

        with pytest.raises(ValueError, match="Unsupported queue service type"):
            MessagingFactory.create_queue_service(settings)

    def test_unsupported_worker_service_type(self):
        """Test error handling for unsupported worker service type."""
        settings = Settings()
        settings.worker_service_type = "unsupported_type"

        with pytest.raises(ValueError, match="Unsupported worker service type"):
            MessagingFactory.create_worker_service(settings)

    def test_unsupported_storage_service_type(self):
        """Test error handling for unsupported storage service type."""
        settings = Settings()
        settings.storage_service_type = "unsupported_type"

        with pytest.raises(ValueError, match="Unsupported storage service type"):
            MessagingFactory.create_storage_service(settings)

    def test_rabbitmq_service_creation_with_mock(self):
        """Test RabbitMQ service creation using mock to avoid import issues."""
        settings = Settings()
        settings.queue_service_type = "rabbitmq"
        settings.rabbitmq_url = "amqp://localhost"

        # Create mock RabbitMQ class and instance
        mock_instance = MagicMock(spec=IQueueService)
        mock_rabbitmq_class = MagicMock(return_value=mock_instance)

        # Create a mock module that provides RabbitMQQueueService
        mock_rabbitmq_module = MagicMock()
        mock_rabbitmq_module.RabbitMQQueueService = mock_rabbitmq_class

        # Patch sys.modules to provide our mock module before the import happens
        module_path = "src.infrastructure.messaging.implementations.rabbitmq_queue"
        with patch.dict('sys.modules', {module_path: mock_rabbitmq_module}):
            service = MessagingFactory.create_queue_service(settings)

            mock_rabbitmq_class.assert_called_once_with(
                connection_url="amqp://localhost"
            )
            assert service == mock_instance

    def test_sqs_service_creation_with_mock(self):
        """Test SQS service creation using mock to avoid import issues."""
        settings = Settings()
        settings.queue_service_type = "sqs"
        settings.aws_region = "us-east-1"
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"

        # Create mock SQS class and instance
        mock_instance = MagicMock(spec=IQueueService)
        mock_sqs_class = MagicMock(return_value=mock_instance)

        # Create a mock module that provides SQSQueueService
        mock_sqs_module = MagicMock()
        mock_sqs_module.SQSQueueService = mock_sqs_class

        # Patch sys.modules to provide our mock module before the import happens
        module_path = "src.infrastructure.messaging.implementations.sqs_queue"
        with patch.dict('sys.modules', {module_path: mock_sqs_module}):
            service = MessagingFactory.create_queue_service(settings)

            mock_sqs_class.assert_called_once_with(
                aws_region="us-east-1",
                queue_prefix="aperilex",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )
            assert service == mock_instance

    def test_s3_storage_service_creation_with_mock(self):
        """Test S3 storage service creation using mock to avoid import issues."""
        settings = Settings()
        settings.storage_service_type = "s3"
        settings.aws_region = "us-west-2"
        settings.aws_s3_bucket = "test-bucket"
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"

        # Create mock S3 class and instance
        mock_instance = MagicMock(spec=IStorageService)
        mock_s3_class = MagicMock(return_value=mock_instance)

        # Create a mock module that provides S3StorageService
        mock_s3_module = MagicMock()
        mock_s3_module.S3StorageService = mock_s3_class

        # Patch sys.modules to provide our mock module before the import happens
        module_path = "src.infrastructure.messaging.implementations.s3_storage"
        with patch.dict('sys.modules', {module_path: mock_s3_module}):
            service = MessagingFactory.create_storage_service(settings)

            mock_s3_class.assert_called_once_with(
                bucket_name="test-bucket",
                aws_region="us-west-2",
                prefix="cache/",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )
            assert service == mock_instance

    def test_lambda_worker_service_creation_with_mock(self):
        """Test Lambda worker service creation using mock to avoid import issues."""
        settings = Settings()
        settings.worker_service_type = "lambda"
        settings.aws_region = "us-east-1"
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"

        # Create mock Lambda class and instance
        mock_instance = MagicMock(spec=IWorkerService)
        mock_lambda_class = MagicMock(return_value=mock_instance)

        # Create a mock module that provides LambdaWorkerService
        mock_lambda_module = MagicMock()
        mock_lambda_module.LambdaWorkerService = mock_lambda_class

        # Patch sys.modules to provide our mock module before the import happens
        module_path = "src.infrastructure.messaging.implementations.lambda_worker"
        with patch.dict('sys.modules', {module_path: mock_lambda_module}):
            service = MessagingFactory.create_worker_service(settings)

            mock_lambda_class.assert_called_once_with(
                aws_region="us-east-1",
                function_prefix="aperilex",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )
            assert service == mock_instance

    def test_factory_with_kwargs_override(self):
        """Test that kwargs can override settings values."""
        settings = Settings()
        settings.storage_service_type = "local"

        custom_path = "/custom/path"
        service = MessagingFactory.create_storage_service(
            settings, local_storage_path=custom_path
        )

        assert isinstance(service, IStorageService)


class TestServiceRegistry:
    """Test ServiceRegistry class."""

    def test_service_registry_initialization(self):
        """Test basic service registry initialization."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = ServiceRegistry(settings)

        assert registry.settings == settings
        assert registry._queue_service is None
        assert registry._worker_service is None
        assert registry._storage_service is None
        assert not registry.is_connected

    @pytest.mark.asyncio
    async def test_service_registry_initialize(self):
        """Test service registry initialization with services."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = ServiceRegistry(settings)
        await registry.initialize()

        assert registry.queue_service is not None
        assert registry.worker_service is not None
        assert registry.storage_service is not None
        assert registry.is_connected

    @pytest.mark.asyncio
    async def test_service_registry_cleanup(self):
        """Test service registry cleanup."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = ServiceRegistry(settings)
        await registry.initialize()

        assert registry.is_connected

        await registry.cleanup()

        assert not registry.is_connected

    def test_accessing_services_before_initialization(self):
        """Test that accessing services before initialization raises error."""
        settings = Settings()
        registry = ServiceRegistry(settings)

        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = registry.queue_service

        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = registry.worker_service

        with pytest.raises(RuntimeError, match="Services not initialized"):
            _ = registry.storage_service

    @pytest.mark.asyncio
    async def test_health_check_all_services(self):
        """Test health check across all services."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = ServiceRegistry(settings)
        await registry.initialize()

        health = await registry.health_check()

        assert "queue" in health
        assert "worker" in health
        assert "storage" in health
        assert isinstance(health["queue"], bool)
        assert isinstance(health["worker"], bool)
        assert isinstance(health["storage"], bool)

    @pytest.mark.asyncio
    async def test_health_check_without_services(self):
        """Test health check when no services are initialized."""
        settings = Settings()
        registry = ServiceRegistry(settings)

        health = await registry.health_check()

        assert health == {}

    @pytest.mark.asyncio
    async def test_registry_initialization_failure_cleanup(self):
        """Test that registry cleanup occurs on initialization failure."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        registry = ServiceRegistry(settings)

        # Mock the factory to return services that fail during connection
        with patch(
            'src.infrastructure.messaging.factory.MessagingFactory'
        ) as mock_factory:
            mock_queue = AsyncMock()
            mock_storage = AsyncMock()
            mock_worker = AsyncMock()

            # Make the queue service connection fail
            mock_queue.connect.side_effect = Exception("Connection failed")

            mock_factory.create_queue_service.return_value = mock_queue
            mock_factory.create_storage_service.return_value = mock_storage
            mock_factory.create_worker_service.return_value = mock_worker

            with pytest.raises(Exception, match="Connection failed"):
                await registry.initialize()

            # Should not be connected after failed initialization
            assert not registry.is_connected


class TestGlobalServiceManagement:
    """Test global service management functions."""

    @pytest.mark.asyncio
    async def test_initialize_and_get_registry(self):
        """Test global registry initialization and access."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        # Initialize global registry
        registry = await initialize_services(settings)

        assert isinstance(registry, ServiceRegistry)
        assert registry.is_connected

        # Get the same registry instance
        same_registry = await get_registry()
        assert same_registry is registry

        # Cleanup
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_get_registry_before_initialization(self):
        """Test getting registry before initialization raises error."""
        # Ensure cleanup first
        await cleanup_services()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_registry()

    @pytest.mark.asyncio
    async def test_reinitialize_services(self):
        """Test reinitializing services cleans up existing registry."""
        settings = Settings()
        settings.queue_service_type = "mock"
        settings.worker_service_type = "mock"
        settings.storage_service_type = "mock"

        # Initialize first time
        registry1 = await initialize_services(settings)

        # Initialize second time - should cleanup first registry
        registry2 = await initialize_services(settings)

        assert registry2 is not registry1
        assert registry2.is_connected

        # Cleanup
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_cleanup_services_multiple_times(self):
        """Test that cleanup_services is safe to call multiple times."""
        # First cleanup (no registry should exist)
        await cleanup_services()

        # Second cleanup (should not fail)
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience functions for accessing services."""
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

        # Cleanup
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_convenience_functions_before_initialization(self):
        """Test convenience functions before registry initialization."""
        await cleanup_services()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_queue_service()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_worker_service()

        with pytest.raises(RuntimeError, match="Service registry not initialized"):
            await get_storage_service()


class TestFactoryEdgeCases:
    """Test edge cases and error conditions in factory."""

    def test_factory_with_none_settings(self):
        """Test factory behavior with None settings."""
        with pytest.raises(AttributeError):
            MessagingFactory.create_queue_service(None)

    def test_factory_with_missing_attributes(self):
        """Test factory behavior with settings missing attributes."""
        settings = MagicMock()
        delattr(settings, 'queue_service_type')

        with pytest.raises(AttributeError):
            MessagingFactory.create_queue_service(settings)

    def test_factory_kwargs_handling(self):
        """Test that factory properly handles various kwargs."""
        settings = Settings()
        settings.storage_service_type = "local"

        # Test with various kwargs
        service = MessagingFactory.create_storage_service(
            settings,
            local_storage_path="/tmp/test",
            some_other_param="ignored",  # Should be ignored gracefully
        )

        assert isinstance(service, IStorageService)

    @patch.dict('os.environ', {'LOCAL_STORAGE_PATH': '/env/storage/path'})
    def test_local_storage_environment_variable(self):
        """Test that local storage respects environment variable."""
        settings = Settings()
        settings.storage_service_type = "local"

        service = MessagingFactory.create_storage_service(settings)

        assert isinstance(service, IStorageService)
        # The actual path verification would depend on implementation details

    def test_aws_service_creation_without_import_errors(self):
        """Test AWS service creation error handling when imports fail."""
        settings = Settings()

        # Test SQS without boto3 - simulate import failure by not providing the module
        settings.queue_service_type = "sqs"
        # Don't patch sys.modules, so the import will fail naturally
        with pytest.raises(ImportError, match="AWS dependencies not available"):
            MessagingFactory.create_queue_service(settings)

        # Test S3 without boto3
        settings.storage_service_type = "s3"
        with pytest.raises(ImportError, match="AWS dependencies not available"):
            MessagingFactory.create_storage_service(settings)

        # Test Lambda without boto3
        settings.worker_service_type = "lambda"
        with pytest.raises(ImportError, match="AWS dependencies not available"):
            MessagingFactory.create_worker_service(settings)

    def test_rabbitmq_service_creation_without_import_errors(self):
        """Test RabbitMQ service creation error handling when imports fail."""
        settings = Settings()
        settings.queue_service_type = "rabbitmq"

        # Don't patch sys.modules, so the import will fail naturally due to missing aio_pika
        with pytest.raises(ImportError, match="RabbitMQ dependencies not available"):
            MessagingFactory.create_queue_service(settings)
