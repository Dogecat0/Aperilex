"""Queue provider implementations and optional loaders."""

from __future__ import annotations

from pydantic import BaseModel

from src.application.interfaces.queue import IQueueProvider

from .rabbitmq import RabbitMQConfig, RabbitMQQueueProvider


def load_sqs_queue_provider() -> type[IQueueProvider]:
    """Load the SQS queue provider implementation if available."""

    from .sqs import SQSQueueProvider

    return SQSQueueProvider


def load_sqs_config() -> type[BaseModel]:
    """Load the SQS queue provider configuration class if available."""

    from .sqs import SQSConfig

    return SQSConfig


__all__ = [
    "RabbitMQQueueProvider",
    "RabbitMQConfig",
    "load_sqs_queue_provider",
    "load_sqs_config",
]
