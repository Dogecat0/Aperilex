import os
import sys

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def _is_testing() -> bool:
    """Check if we're running in a test environment."""
    return (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("TESTING", "").lower() in ("true", "1", "yes")
    )


def _get_messaging_environment() -> str:
    """Determine messaging environment based on context."""
    if _is_testing():
        return "testing"

    env = os.environ.get("ENVIRONMENT", "development").lower()
    if env == "production":
        return "production"
    return "development"


class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Aperilex", validation_alias="APP_NAME")
    app_version: str = Field(default="1.0.0", validation_alias="APP_VERSION")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Database
    database_url: str = Field(
        default="sqlite:///:memory:" if _is_testing() else "",
        validation_alias="DATABASE_URL",
    )

    # Messaging System Configuration
    messaging_environment: str = Field(
        default_factory=_get_messaging_environment,
        validation_alias="MESSAGING_ENVIRONMENT",
    )

    # RabbitMQ (Development)
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        validation_alias="RABBITMQ_URL",
    )

    # AWS Configuration (Production)
    aws_region: str = Field(
        default="us-east-1",
        validation_alias="AWS_REGION",
    )
    aws_access_key_id: str = Field(
        default="",
        validation_alias="AWS_ACCESS_KEY_ID",
    )
    aws_secret_access_key: str = Field(
        default="",
        validation_alias="AWS_SECRET_ACCESS_KEY",
    )
    aws_sqs_queue_url: str = Field(
        default="",
        validation_alias="AWS_SQS_QUEUE_URL",
    )
    aws_s3_bucket: str = Field(
        default="",
        validation_alias="AWS_S3_BUCKET",
    )

    # Worker Polling Configuration
    worker_queue_timeout: float = Field(
        default=0.2,
        validation_alias="WORKER_QUEUE_TIMEOUT",
    )
    worker_min_sleep: float = Field(
        default=0.1,
        validation_alias="WORKER_MIN_SLEEP",
    )
    worker_max_sleep: float = Field(
        default=30.0,
        validation_alias="WORKER_MAX_SLEEP",
    )
    worker_backoff_factor: float = Field(
        default=1.5,
        validation_alias="WORKER_BACKOFF_FACTOR",
    )

    # Security
    secret_key: str = Field(
        default="test_secret_key_for_testing_only" if _is_testing() else "",
        validation_alias="SECRET_KEY",
    )
    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # SEC API
    edgar_identity: str = Field(
        default="test@example.com" if _is_testing() else "",
        validation_alias="EDGAR_IDENTITY",
    )

    # LLM
    llm_model: str = Field(
        default="default" if _is_testing() else "", validation_alias="LLM_MODEL"
    )
    default_llm_provider: str = Field(
        default="openai", validation_alias="DEFAULT_LLM_PROVIDER"
    )
    llm_temperature: float = Field(default=0.0, validation_alias="LLM_TEMPERATURE")
    openai_api_key: str | None = Field(
        default="dummy_openai_key" if _is_testing() else "dummy",
        validation_alias="OPENAI_API_KEY",
    )
    openai_base_url: str | None = Field(
        default="https://api.openai.com/v1" if _is_testing() else None,
        validation_alias="OPENAI_BASE_URL",
    )
    google_api_key: str | None = Field(
        default="dummy_google_key" if _is_testing() else None,
        validation_alias="GOOGLE_API_KEY",
    )

    # CORS
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    # Monitoring
    prometheus_enabled: bool = Field(
        default=True, validation_alias="PROMETHEUS_ENABLED"
    )
    opentelemetry_enabled: bool = Field(
        default=False, validation_alias="OPENTELEMETRY_ENABLED"
    )

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if _is_testing() and not v:
            return "test_encryption_key_32_chars_long"
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters long")
        return v

    class Config:
        env_file = None if _is_testing() else ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
