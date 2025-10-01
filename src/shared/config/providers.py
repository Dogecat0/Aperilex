"""
Provider configuration models.

These configuration models are used across the application for provider setup.
They should be in the shared layer as they are data models, not interfaces.
"""

from aio_pika import ExchangeType  # Used in RabbitMQConfig
from pydantic import BaseModel

from src.shared.enums import (
    LLMProvider,
)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    schema_version: int = 1
    hourly_limit: int | None = None
    daily_limit: int | None = None
    burst_limit: int | None = None
    enabled: bool = True
    excluded_paths: list[str] = []


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    schema_version: int = 1
    provider: LLMProvider
    model_name: str
    api_key_secret_name: str
    api_endpoint: str | None = None
    retry_attempts: int = 3
    timeout_seconds: int = 60
    rate_limit_per_minute: int = 60


class PostgresConfig(BaseModel):
    """Configuration for PostgreSQL database provider."""

    schema_version: int = 1
    host: str = "localhost"
    port: int = 5432
    database: str = "aperilex"
    username: str = "postgres"
    password_secret_name: str = "postgres_password"
    max_connections: int = 10
    min_connections: int = 2
    connection_timeout_seconds: int = 30
    query_timeout_seconds: int = 30
    enable_ssl: bool = False
    enable_connection_pooling: bool = True
    retry_attempts: int = 3
    echo_sql: bool = False


class AuroraConfig(BaseModel):
    """Configuration for Aurora Serverless v2 database provider."""

    schema_version: int = 1
    cluster_endpoint: str  # e.g., mydb.cluster-xxx.us-east-2.rds.amazonaws.com
    database: str = "aperilex"
    username: str = "postgres"
    password_secret_name: str = "aurora_password"
    port: int = 5432
    region: str = "us-east-2"
    # Aurora-specific settings
    min_acu: float = 0  # 0 ACU for true scale-to-zero
    max_acu: float = 16  # Maximum ACUs
    max_connections: int = 50  # Higher than local Postgres due to serverless scaling
    min_connections: int = 0  # Allow scaling to zero connections
    connection_timeout_seconds: int = 60  # Longer timeout for cold starts
    query_timeout_seconds: int = 30
    enable_ssl: bool = True  # Always use SSL for Aurora
    enable_iam_auth: bool = False  # Use IAM authentication if enabled
    enable_connection_pooling: bool = True
    retry_attempts: int = 5  # More retries for serverless cold starts


class SQSConfig(BaseModel):
    """Configuration for SQS provider."""

    schema_version: int = 1
    queue_url: str
    region: str = "us-east-2"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    use_fifo: bool = True
    message_group_id: str = "default"
    visibility_timeout_seconds: int = 300
    message_retention_seconds: int = 345600  # 4 days
    max_receive_count: int = 3
    enable_content_deduplication: bool = True
    wait_time_seconds: int = 20  # Long polling
    batch_size: int = 10


class RabbitMQConfig(BaseModel):
    """Configuration for RabbitMQ provider."""

    schema_version: int = 1
    connection_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "aperilex"
    exchange_type: ExchangeType = ExchangeType.DIRECT
    queue_name: str = "tasks"
    routing_key: str = "task"
    durable: bool = True
    auto_delete: bool = False
    prefetch_count: int = 10
    message_ttl_seconds: int = 86400  # 24 hours
    max_retries: int = 3
    deduplication_window_seconds: int = 300  # 5 minutes
    enable_deduplication: bool = True


class LambdaWorkerConfig(BaseModel):
    """Configuration for Lambda worker provider."""

    schema_version: int = 1
    function_name: str = "aperilex-worker"
    region: str = "us-east-2"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    qualifier: str = "$LATEST"  # Version or alias
    invocation_type: str = "RequestResponse"  # or "Event" for async
    log_type: str = "Tail"  # Include logs in response
    max_payload_size: int = 6 * 1024 * 1024  # 6MB Lambda limit
    timeout_seconds: int = 900  # 15 minutes max
    memory_mb: int = 1024
    reserved_concurrent_executions: int = 100
    dead_letter_queue_arn: str | None = None
    environment_variables: dict[str, str] = {}
    vpc_config: dict[str, list[str]] | None = None
    retry_config: dict[str, int | str] = {"max_attempts": 3, "mode": "adaptive"}


class DockerWorkerConfig(BaseModel):
    """Configuration for Docker worker provider."""

    schema_version: int = 1
    image_name: str = "aperilex-worker:latest"
    container_prefix: str = "aperilex-worker"
    network_name: str = "aperilex-network"
    max_concurrent_tasks: int = 5
    cpu_limit: float = 1.0  # Number of CPUs
    memory_limit: int = 512  # MB
    environment_vars: dict[str, str] = {}
    volume_mounts: dict[str, str] = {}  # host_path: container_path
    auto_remove: bool = True
    enable_gpu: bool = False
    log_driver: str = "json-file"
    log_max_size: str = "10m"
    log_max_files: str = "3"
    status_store_path: str = "task-status"
