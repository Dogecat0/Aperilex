"""Helpers for loading database configuration from the config provider."""

from src.application.interfaces.config import IConfigProvider
from src.shared.config.providers import PostgresConfig


def load_postgres_config(config_provider: IConfigProvider) -> PostgresConfig:
    """Build PostgresConfig from the configured environment values."""
    return PostgresConfig(
        host=config_provider.get_string("database.postgres.host", "localhost"),
        port=config_provider.get_int("database.postgres.port", 5432),
        database=config_provider.get_string("database.postgres.database", "aperilex"),
        username=config_provider.get_string("database.postgres.username", "postgres"),
        password_secret_name=config_provider.get_string(
            "database.postgres.password_secret", "postgres_password"
        ),  # nosec B106 - This is a secret name, not a password
        max_connections=config_provider.get_int(
            "database.postgres.max_connections", 10
        ),
        min_connections=config_provider.get_int(
            "database.postgres.min_connections", 2
        ),
        connection_timeout_seconds=config_provider.get_int(
            "database.postgres.connection_timeout_seconds", 30
        ),
        query_timeout_seconds=config_provider.get_int(
            "database.postgres.query_timeout_seconds", 30
        ),
        enable_ssl=config_provider.get_bool("database.postgres.enable_ssl", False),
        enable_connection_pooling=config_provider.get_bool(
            "database.postgres.enable_connection_pooling", True
        ),
        retry_attempts=config_provider.get_int("database.postgres.retry_attempts", 3),
        echo_sql=config_provider.get_bool("database.postgres.echo_sql", False),
    )
