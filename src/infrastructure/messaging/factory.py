"""Service factory for messaging infrastructure."""

import logging
import os
from typing import Any

from src.shared.config.settings import Settings

# Lazy imports - only import what we need for each environment
from .interfaces import IQueueService, IStorageService, IWorkerService

logger = logging.getLogger(__name__)


class MessagingFactory:
    """Factory for creating messaging service implementations."""

    @staticmethod
    def create_queue_service(settings: Settings, **kwargs: Any) -> IQueueService:
        """Create queue service based on settings.

        Args:
            settings: Application settings
            **kwargs: Additional provider-specific configuration

        Returns:
            Queue service implementation
        """
        if settings.queue_service_type == "rabbitmq":
            # Use RabbitMQ for local development
            try:
                from .implementations.rabbitmq_queue import RabbitMQQueueService

                connection_url = kwargs.get("rabbitmq_url", settings.rabbitmq_url)
                return RabbitMQQueueService(connection_url=connection_url)
            except ImportError as e:
                raise ImportError(
                    "RabbitMQ dependencies not available for development environment. "
                    "Install with: poetry add aio-pika"
                ) from e

        elif settings.queue_service_type == "mock":
            # Use mock service for testing
            from .implementations.mock_services import MockQueueService

            return MockQueueService()

        elif settings.queue_service_type == "sqs":
            # Use AWS SQS for production
            try:
                from .implementations.sqs_queue import SQSQueueService

                return SQSQueueService(
                    aws_region=kwargs.get("aws_region", settings.aws_region),
                    queue_prefix=kwargs.get("queue_prefix", "aperilex"),
                    aws_access_key_id=kwargs.get(
                        "aws_access_key_id", settings.aws_access_key_id
                    ),
                    aws_secret_access_key=kwargs.get(
                        "aws_secret_access_key", settings.aws_secret_access_key
                    ),
                )
            except ImportError as e:
                raise ImportError(
                    "AWS dependencies not available for production environment. "
                    "Install with: poetry add boto3"
                ) from e

        else:
            raise ValueError(
                f"Unsupported queue service type: {settings.queue_service_type}"
            )

    @staticmethod
    def create_worker_service(
        settings: Settings,
        queue_service: IQueueService | None = None,
        **kwargs: Any,
    ) -> IWorkerService:
        """Create worker service based on settings.

        Args:
            settings: Application settings
            queue_service: Queue service instance (required for local workers)
            **kwargs: Additional provider-specific configuration

        Returns:
            Worker service implementation
        """
        if settings.worker_service_type == "local":
            # Use local worker with RabbitMQ
            from .implementations.local_worker import LocalWorkerService

            if queue_service is None:
                raise ValueError("queue_service is required for local worker")
            worker_id = kwargs.get("worker_id")
            return LocalWorkerService(queue_service=queue_service, worker_id=worker_id)

        elif settings.worker_service_type == "mock":
            # Use mock service for testing
            from .implementations.mock_services import MockWorkerService

            return MockWorkerService()

        elif settings.worker_service_type == "lambda":
            # Use AWS Lambda for production
            try:
                from .implementations.lambda_worker import LambdaWorkerService

                return LambdaWorkerService(
                    aws_region=kwargs.get("aws_region", settings.aws_region),
                    function_prefix=kwargs.get("function_prefix", "aperilex"),
                    aws_access_key_id=kwargs.get(
                        "aws_access_key_id", settings.aws_access_key_id
                    ),
                    aws_secret_access_key=kwargs.get(
                        "aws_secret_access_key", settings.aws_secret_access_key
                    ),
                )
            except ImportError as e:
                raise ImportError(
                    "AWS dependencies not available for production environment. "
                    "Install with: poetry add boto3"
                ) from e

        else:
            raise ValueError(
                f"Unsupported worker service type: {settings.worker_service_type}"
            )

    @staticmethod
    def create_storage_service(settings: Settings, **kwargs: Any) -> IStorageService:
        """Create storage service based on settings.

        Args:
            settings: Application settings
            **kwargs: Additional provider-specific configuration

        Returns:
            Storage service implementation
        """
        if settings.storage_service_type == "local":
            # For development, use local file storage for persistence
            from .implementations.local_file_storage import LocalFileStorageService

            # Use environment variable or kwargs, fallback to ./data
            base_path = kwargs.get(
                "local_storage_path", os.getenv("LOCAL_STORAGE_PATH", "./data")
            )
            return LocalFileStorageService(base_path=base_path)

        elif settings.storage_service_type == "mock":
            # Use mock service for testing
            from .implementations.mock_services import MockStorageService

            return MockStorageService()

        elif settings.storage_service_type == "s3":
            # Use AWS S3 for production storage (no Redis)
            try:
                from .implementations.s3_storage import S3StorageService

                return S3StorageService(
                    bucket_name=kwargs.get(
                        "s3_bucket_name", settings.aws_s3_bucket or "aperilex-cache"
                    ),
                    aws_region=kwargs.get("aws_region", settings.aws_region),
                    prefix=kwargs.get("s3_prefix", "cache/"),
                    aws_access_key_id=kwargs.get(
                        "aws_access_key_id", settings.aws_access_key_id
                    ),
                    aws_secret_access_key=kwargs.get(
                        "aws_secret_access_key", settings.aws_secret_access_key
                    ),
                )
            except ImportError as e:
                raise ImportError(
                    "AWS dependencies not available for production environment. "
                    "Install with: poetry add boto3"
                ) from e

        else:
            raise ValueError(
                f"Unsupported storage service type: {settings.storage_service_type}"
            )


class ServiceRegistry:
    """Registry for managing service instances."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._queue_service: IQueueService | None = None
        self._worker_service: IWorkerService | None = None
        self._storage_service: IStorageService | None = None
        self._connected = False

    async def initialize(self, **config: Any) -> None:
        """Initialize all services with configuration."""
        try:
            # Create services
            self._queue_service = MessagingFactory.create_queue_service(
                self.settings, **config
            )

            self._storage_service = MessagingFactory.create_storage_service(
                self.settings, **config
            )

            self._worker_service = MessagingFactory.create_worker_service(
                self.settings, queue_service=self._queue_service, **config
            )

            # Connect services
            await self._queue_service.connect()
            await self._storage_service.connect()

            self._connected = True
            logger.info(
                f"Initialized messaging services - Queue: {self.settings.queue_service_type}, "
                f"Storage: {self.settings.storage_service_type}, Worker: {self.settings.worker_service_type}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize messaging services: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        """Cleanup all services."""
        if self._worker_service:
            try:
                await self._worker_service.stop()
            except Exception as e:
                logger.warning(f"Error stopping worker service: {e}")

        if self._queue_service:
            try:
                await self._queue_service.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting queue service: {e}")

        if self._storage_service:
            try:
                await self._storage_service.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting storage service: {e}")

        self._connected = False
        logger.info("Cleaned up messaging services")

    @property
    def queue_service(self) -> IQueueService:
        """Get queue service instance."""
        if not self._queue_service:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        return self._queue_service

    @property
    def worker_service(self) -> IWorkerService:
        """Get worker service instance."""
        if not self._worker_service:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        return self._worker_service

    @property
    def storage_service(self) -> IStorageService:
        """Get storage service instance."""
        if not self._storage_service:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        return self._storage_service

    @property
    def is_connected(self) -> bool:
        """Check if services are connected."""
        return self._connected

    async def health_check(self) -> dict[str, bool]:
        """Perform health check on all services."""
        health = {}

        if self._queue_service:
            health["queue"] = await self._queue_service.health_check()

        if self._worker_service:
            health["worker"] = await self._worker_service.health_check()

        if self._storage_service:
            health["storage"] = await self._storage_service.health_check()

        return health


# Global registry instance
_registry: ServiceRegistry | None = None


async def get_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _registry
    if _registry is None:
        raise RuntimeError(
            "Service registry not initialized. Call initialize_services() first."
        )
    return _registry


async def initialize_services(settings: Settings, **config: Any) -> ServiceRegistry:
    """Initialize global service registry."""
    global _registry

    if _registry is not None:
        await _registry.cleanup()

    _registry = ServiceRegistry(settings)
    await _registry.initialize(**config)

    return _registry


async def cleanup_services() -> None:
    """Cleanup global service registry."""
    global _registry
    if _registry is not None:
        await _registry.cleanup()
        _registry = None


# Convenience functions for accessing services


async def get_queue_service() -> IQueueService:
    """Get the queue service instance."""
    registry = await get_registry()
    return registry.queue_service


async def get_worker_service() -> IWorkerService:
    """Get the worker service instance."""
    registry = await get_registry()
    return registry.worker_service


async def get_storage_service() -> IStorageService:
    """Get the storage service instance."""
    registry = await get_registry()
    return registry.storage_service
