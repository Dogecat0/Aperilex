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

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/1" if _is_testing() else "",
        validation_alias="REDIS_URL",
    )

    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/2" if _is_testing() else "",
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/3" if _is_testing() else "",
        validation_alias="CELERY_RESULT_BACKEND",
    )
    celery_worker_concurrency: int = Field(
        default=4, validation_alias="CELERY_WORKER_CONCURRENCY"
    )
    celery_task_serializer: str = Field(
        default="json", validation_alias="CELERY_TASK_SERIALIZER"
    )
    celery_result_serializer: str = Field(
        default="json", validation_alias="CELERY_RESULT_SERIALIZER"
    )
    celery_accept_content: list[str] = Field(
        default=["json"], validation_alias="CELERY_ACCEPT_CONTENT"
    )
    celery_timezone: str = Field(default="UTC", validation_alias="CELERY_TIMEZONE")
    celery_enable_utc: bool = Field(default=True, validation_alias="CELERY_ENABLE_UTC")
    celery_task_track_started: bool = Field(
        default=True, validation_alias="CELERY_TASK_TRACK_STARTED"
    )
    celery_task_time_limit: int = Field(
        default=3600, validation_alias="CELERY_TASK_TIME_LIMIT"
    )  # 1 hour
    celery_task_soft_time_limit: int = Field(
        default=3300, validation_alias="CELERY_TASK_SOFT_TIME_LIMIT"
    )  # 55 minutes

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
