"""
Provider enums for different service implementations.
"""

from enum import Enum


class StorageProvider(str, Enum):
    """Available storage provider implementations."""

    S3 = "S3"
    LOCAL = "LOCAL"
    GCS = "GCS"
    AZURE_BLOB = "AZURE_BLOB"


class QueueProvider(str, Enum):
    """Available queue provider implementations."""

    SQS = "SQS"
    RABBITMQ = "RABBITMQ"
    PUBSUB = "PUBSUB"
    SERVICE_BUS = "SERVICE_BUS"


class WorkerProvider(str, Enum):
    """Available worker provider implementations."""

    LAMBDA = "LAMBDA"
    DOCKER = "DOCKER"
    CLOUD_RUN = "CLOUD_RUN"
    CONTAINER_INSTANCES = "CONTAINER_INSTANCES"


class LLMProvider(str, Enum):
    """Available LLM provider implementations."""

    OPENAI = "OPENAI"
    BEDROCK = "BEDROCK"
    VERTEX_AI = "VERTEX_AI"
    ANTHROPIC = "ANTHROPIC"
    OLLAMA = "OLLAMA"
    GOOGLE = "GOOGLE"


class DataSourceProvider(str, Enum):
    """Available data source provider implementations."""

    EDGAR = "EDGAR"
    REFINITIV = "REFINITIV"
    BLOOMBERG = "BLOOMBERG"
    CUSTOM_API = "CUSTOM_API"


class DatabaseProvider(str, Enum):
    """Available database provider implementations."""

    POSTGRES = "POSTGRES"
    AURORA = "AURORA"
    COCKROACHDB = "COCKROACHDB"
    MYSQL = "MYSQL"
    SQLSERVER = "SQLSERVER"


class RateLimitingProvider(str, Enum):
    """Available rate limiting provider implementations."""

    IN_MEMORY = "IN_MEMORY"
    REDIS = "REDIS"
    MEMCACHED = "MEMCACHED"
