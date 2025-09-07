"""
Provider enums for different service implementations.
"""

from enum import Enum


class StorageProvider(str, Enum):
    """Available storage provider implementations."""

    S3 = "S3"
    LOCAL = "LOCAL"


class QueueProvider(str, Enum):
    """Available queue provider implementations."""

    SQS = "SQS"
    RABBITMQ = "RABBITMQ"


class WorkerProvider(str, Enum):
    """Available worker provider implementations."""

    LAMBDA = "LAMBDA"
    DOCKER = "DOCKER"


class LLMProvider(str, Enum):
    """Available LLM provider implementations."""

    OPENAI = "OPENAI"
    BEDROCK = "BEDROCK"
    GOOGLE = "GOOGLE"


class DataSourceProvider(str, Enum):
    """Available data source provider implementations."""

    EDGAR = "EDGAR"


class DatabaseProvider(str, Enum):
    """Available database provider implementations."""

    POSTGRES = "POSTGRES"
    AURORA = "AURORA"
    COCKROACHDB = "COCKROACHDB"
