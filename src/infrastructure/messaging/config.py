"""Configuration helpers for messaging services."""

import os
from typing import Any

from .factory import EnvironmentType


class MessagingConfig:
    """Configuration manager for messaging services."""

    @staticmethod
    def get_environment() -> EnvironmentType:
        """Get environment type from environment variables."""
        env = os.getenv("ENVIRONMENT", "development").lower()

        if env in ["dev", "development", "local"]:
            return EnvironmentType.DEVELOPMENT
        elif env in ["test", "testing"]:
            return EnvironmentType.TESTING
        elif env in ["prod", "production"]:
            return EnvironmentType.PRODUCTION
        else:
            return EnvironmentType.DEVELOPMENT

    @staticmethod
    def get_config() -> dict[str, Any]:
        """Get configuration for messaging services based on environment."""
        environment = MessagingConfig.get_environment()

        if environment == EnvironmentType.DEVELOPMENT:
            return MessagingConfig._get_development_config()
        elif environment == EnvironmentType.TESTING:
            return MessagingConfig._get_testing_config()
        elif environment == EnvironmentType.PRODUCTION:
            return MessagingConfig._get_production_config()
        else:
            return MessagingConfig._get_development_config()

    @staticmethod
    def _get_development_config() -> dict[str, Any]:
        """Get configuration for development environment."""
        return {
            # RabbitMQ configuration
            "rabbitmq_url": os.getenv("RABBITMQ_URL", "amqp://localhost"),
            # Worker configuration
            "worker_id": os.getenv("WORKER_ID"),
        }

    @staticmethod
    def _get_testing_config() -> dict[str, Any]:
        """Get configuration for testing environment."""
        return {
            "storage_type": "memory",  # Always use memory for tests
        }

    @staticmethod
    def _get_production_config() -> dict[str, Any]:
        """Get configuration for production environment (AWS)."""
        return {
            # AWS configuration
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            # SQS configuration
            "queue_prefix": os.getenv("SQS_QUEUE_PREFIX", "aperilex"),
            # Lambda configuration
            "function_prefix": os.getenv("LAMBDA_FUNCTION_PREFIX", "aperilex"),
            # S3 Storage configuration
            "s3_bucket_name": os.getenv("S3_CACHE_BUCKET", "aperilex-cache"),
            "s3_prefix": os.getenv("S3_CACHE_PREFIX", "cache/"),
        }

    @staticmethod
    async def initialize_from_env() -> None:
        """Initialize messaging services from environment configuration."""
        from .factory import initialize_services

        environment = MessagingConfig.get_environment()
        config = MessagingConfig.get_config()

        await initialize_services(environment, **config)


# Environment-specific initialization functions


async def initialize_development_services(
    rabbitmq_url: str = "amqp://localhost",
    worker_id: str | None = None,
) -> None:
    """Initialize services for development environment."""
    from .factory import initialize_services

    await initialize_services(
        EnvironmentType.DEVELOPMENT,
        rabbitmq_url=rabbitmq_url,
        worker_id=worker_id,
    )


async def initialize_testing_services() -> None:
    """Initialize services for testing environment."""
    from .factory import initialize_services

    await initialize_services(
        EnvironmentType.TESTING,
        storage_type="memory",
    )


async def initialize_production_services(
    aws_region: str = "us-east-1",
    queue_prefix: str = "aperilex",
    function_prefix: str = "aperilex",
    s3_bucket_name: str = "aperilex-cache",
    s3_prefix: str = "cache/",
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
) -> None:
    """Initialize services for production environment (AWS)."""
    from .factory import initialize_services

    await initialize_services(
        EnvironmentType.PRODUCTION,
        aws_region=aws_region,
        queue_prefix=queue_prefix,
        function_prefix=function_prefix,
        s3_bucket_name=s3_bucket_name,
        s3_prefix=s3_prefix,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
