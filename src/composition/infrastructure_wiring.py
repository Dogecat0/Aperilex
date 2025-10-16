"""
Infrastructure container for managing concrete implementations.
"""

from typing import TYPE_CHECKING

from dependency_injector import containers, providers
from dependency_injector.providers import Dependency

from src.infrastructure.database.cache.manager import CacheManager
from src.infrastructure.database.models.base import (
    async_session_maker,
    engine,
)
from src.infrastructure.database.postgres import PostgresDatabaseProvider
from src.infrastructure.providers.rate_limiting.in_memory import (
    InMemoryRateLimitingProvider,
)
from src.infrastructure.query_services import (
    AnalysisQueryService,
    CompanyQueryService,
    FilingQueryService,
    LearningProgressQueryService,
    LearningWalkthroughBindingQueryService,
    QuizAttemptQueryService,
    UserQueryService,
)
from src.shared.config.providers import PostgresConfig, RateLimitConfig

if TYPE_CHECKING:
    from src.application.interfaces import IConfigProvider, ISecretManager


class InfrastructureWiring(containers.DeclarativeContainer):
    """Container for infrastructure implementations."""

    # Config and secret dependencies from parent container
    config_provider: Dependency["IConfigProvider"] = providers.Dependency()
    secret_manager: Dependency["ISecretManager"] = providers.Dependency()

    # Parent container reference for accessing abstract providers
    providers_container = providers.DependenciesContainer()

    # Cache Manager as singleton
    cache_manager = providers.Singleton(
        CacheManager,
    )

    # Database Engine (reuse existing engine from base.py)
    db_engine = providers.Singleton(
        lambda: engine,
    )

    # Database Session Factory (reuse existing session factory)
    db_session_factory = providers.Singleton(
        lambda: async_session_maker,
    )

    # Helper to instantiate lightweight sessions for query services
    session_provider = providers.Callable(
        lambda factory: factory(),
        db_session_factory,
    )

    # PostgreSQL configuration
    postgres_config = providers.Factory(
        lambda cp: PostgresConfig(
            host=cp.get_string("database.postgres.host", "localhost"),
            port=cp.get_int("database.postgres.port", 5432),
            database=cp.get_string("database.postgres.database", "aperilex"),
            username=cp.get_string("database.postgres.username", "postgres"),
            password_secret_name=cp.get_string(
                "database.postgres.password_secret", "postgres_password"
            ),  # nosec B106 - This is a secret name, not a password
            max_connections=cp.get_int("database.postgres.max_connections", 10),
            min_connections=cp.get_int("database.postgres.min_connections", 2),
            connection_timeout_seconds=cp.get_int(
                "database.postgres.connection_timeout_seconds", 30
            ),
            query_timeout_seconds=cp.get_int(
                "database.postgres.query_timeout_seconds", 30
            ),
            enable_ssl=cp.get_bool("database.postgres.enable_ssl", False),
            enable_connection_pooling=cp.get_bool(
                "database.postgres.enable_connection_pooling", True
            ),
            retry_attempts=cp.get_int("database.postgres.retry_attempts", 3),
            echo_sql=cp.get_bool("database.postgres.echo_sql", False),
        ),
        cp=config_provider,
    )

    # Database Provider (concrete implementation)
    database_provider = providers.Singleton(
        PostgresDatabaseProvider,
        config=postgres_config,
        secret_manager=secret_manager,
        cache_manager=cache_manager,
    )

    # Repository Factory
    repository_factory = providers.Factory(
        lambda db_provider: db_provider.get_repository_factory(),
        db_provider=database_provider,
    )

    # Individual Repository Providers (for direct injection)
    company_repository = providers.Factory(
        lambda factory: factory.get_company_repository(),
        factory=repository_factory,
    )

    filing_repository = providers.Factory(
        lambda factory: factory.get_filing_repository(),
        factory=repository_factory,
    )

    analysis_repository = providers.Factory(
        lambda factory: factory.get_analysis_repository(),
        factory=repository_factory,
    )

    user_repository = providers.Factory(
        lambda factory: factory.get_user_repository(),
        factory=repository_factory,
    )

    user_identity_repository = providers.Factory(
        lambda factory: factory.get_user_identity_repository(),
        factory=repository_factory,
    )

    user_profile_repository = providers.Factory(
        lambda factory: factory.get_user_profile_repository(),
        factory=repository_factory,
    )

    learning_progress_repository = providers.Factory(
        lambda factory: factory.get_learning_progress_repository(),
        factory=repository_factory,
    )

    learning_walkthrough_binding_repository = providers.Factory(
        lambda factory: factory.get_learning_walkthrough_binding_repository(),
        factory=repository_factory,
    )

    quiz_attempt_repository = providers.Factory(
        lambda factory: factory.get_quiz_attempt_repository(),
        factory=repository_factory,
    )

    auth_session_repository = providers.Factory(
        lambda factory: factory.get_auth_session_repository(),
        factory=repository_factory,
    )

    auth_rate_limit_repository = providers.Factory(
        lambda factory: factory.get_auth_rate_limit_repository(),
        factory=repository_factory,
    )

    # Rate limiting configuration
    # Using Factory with lambda to defer config_provider access until runtime
    rate_limit_config = providers.Factory(
        lambda cp: RateLimitConfig(
            hourly_limit=cp.get_int("rate_limit_hourly", None),
            daily_limit=cp.get_int("rate_limit_daily", None),
            burst_limit=cp.get_int("rate_limit_burst", None),
            enabled=cp.get_bool("rate_limit_enabled", True),
            excluded_paths=cp.get_list(
                "rate_limit_excluded_paths",
                ["/health", "/", "/docs", "/openapi.json", "/redoc"],
            ),
        ),
        cp=config_provider,
    )

    # Rate limiting provider (concrete implementation)
    rate_limiting_provider = providers.Singleton(
        InMemoryRateLimitingProvider,
        config=rate_limit_config,
    )

    # Query service providers (factories to ensure scoped sessions per request)
    analysis_query_service = providers.Factory(
        AnalysisQueryService,
        session=session_provider,
    )

    filing_query_service = providers.Factory(
        FilingQueryService,
        session=session_provider,
    )

    company_query_service = providers.Factory(
        CompanyQueryService,
        session=session_provider,
    )

    user_query_service = providers.Factory(
        UserQueryService,
        session=session_provider,
    )

    learning_progress_query_service = providers.Factory(
        LearningProgressQueryService,
        session=session_provider,
    )

    learning_walkthrough_binding_query_service = providers.Factory(
        LearningWalkthroughBindingQueryService,
        session=session_provider,
    )

    quiz_attempt_query_service = providers.Factory(
        QuizAttemptQueryService,
        session=session_provider,
    )

    # Override the abstract database provider in ProvidersContainer
    # This should be done when wiring the containers in ApplicationContainer
    def wire_providers(self) -> None:
        """Wire abstract providers with concrete implementations."""
        if hasattr(self, "providers_container") and self.providers_container:
            # Override the abstract database provider with our concrete implementation
            self.providers_container.database_provider.override(self.database_provider)
            # Override the abstract rate limiting provider with our concrete implementation
            self.providers_container.rate_limiting_provider.override(
                self.rate_limiting_provider
            )
