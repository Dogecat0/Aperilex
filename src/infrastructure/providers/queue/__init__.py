"""Queue provider implementations."""

from __future__ import annotations

from .rabbitmq import RabbitMQConfig, RabbitMQQueueProvider

try:  # pragma: no cover - optional dependency
    from .sqs import SQSConfig, SQSQueueProvider
except ModuleNotFoundError:  # aioboto3 optional
    SQSConfig = None  # type: ignore[assignment]
    SQSQueueProvider = None  # type: ignore[assignment]

__all__ = [
    "RabbitMQQueueProvider",
    "RabbitMQConfig",
    "SQSQueueProvider",
    "SQSConfig",
]
