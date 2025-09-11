from pydantic import BaseModel

from src.shared.enums import (
    DatabaseProvider,
    DataSourceProvider,
)


class DataSourceConfig(BaseModel):
    """Configuration for data source provider."""

    schema_version: int = 1
    provider: DataSourceProvider
    api_key_secret_name: str | None = None
    base_url: str | None = None
    rate_limit_per_second: int = 10
    retry_attempts: int = 3
    timeout_seconds: int = 30
    user_agent: str = "Aperilex/1.0"


class DatabaseConfig(BaseModel):
    """Configuration for database provider."""

    schema_version: int = 1
    provider: DatabaseProvider
    connection_string_secret_name: str
    max_connections: int = 10
    connection_timeout_seconds: int = 30
    query_timeout_seconds: int = 30
    enable_ssl: bool = True
    enable_connection_pooling: bool = True


class SecretRotationConfig(BaseModel):
    """Configuration for automatic secret rotation."""

    schema_version: int = 1
    rotation_lambda_arn: str | None = None
    rotation_period_days: int = 30
    automatically_after_days: int | None = None
