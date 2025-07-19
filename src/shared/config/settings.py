from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Aperilex", validation_alias="APP_NAME")
    app_version: str = Field(default="2.0.0", validation_alias="APP_VERSION")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Database
    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="", validation_alias="REDIS_URL")

    # Celery
    celery_broker_url: str = Field(default="", validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="", validation_alias="CELERY_RESULT_BACKEND"
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
    secret_key: str = Field(default="", validation_alias="SECRET_KEY")
    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # SEC API
    edgar_identity: str = Field(default="", validation_alias="EDGAR_IDENTITY")

    # LLM
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(
        default=None, validation_alias="OPENAI_BASE_URL"
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
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
