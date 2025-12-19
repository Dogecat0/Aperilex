"""
Infrastructure container for managing concrete implementations.
"""

from typing import TYPE_CHECKING

from dependency_injector import containers, providers
from dependency_injector.providers import Dependency

from src.application.interfaces.database import IDatabaseProvider
from src.infrastructure.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from src.infrastructure.providers.rate_limiting.in_memory import (
    InMemoryRateLimitingProvider,
)
from src.infrastructure.query_services import (
    AnalysisQueryService,
    CompanyQueryService,
    FilingQueryService,
    LearningProgressQueryService,
    QuizAttemptQueryService,
    UserQueryService,
)
from src.shared.config.providers import RateLimitConfig

if TYPE_CHECKING:
    from src.application.interfaces import IConfigProvider


def _require_sqlalchemy_provider(
    db_provider: IDatabaseProvider,
) -> SQLAlchemyDatabaseProvider:
    if not isinstance(db_provider, SQLAlchemyDatabaseProvider):
        raise RuntimeError(
            "Infrastructure query services require SQLAlchemyDatabaseProvider. "
            f"Received {type(db_provider).__name__}."
        )
    return db_provider


class InfrastructureWiring(containers.DeclarativeContainer):
    """Container for infrastructure implementations."""

    # Config dependencies from parent container
    config_provider: Dependency["IConfigProvider"] = providers.Dependency()

    # Parent container reference for accessing abstract providers
    providers_container = providers.DependenciesContainer()

    # Database Provider (delegate to application container)
    database_provider = providers.Delegate(
        providers_container.database_provider,
    )

    # Database Session Factory (requires SQLAlchemy-based provider)
    db_session_factory = providers.Callable(
        lambda db_provider: _require_sqlalchemy_provider(
            db_provider
        ).get_session_factory(),
        db_provider=database_provider,
    )

    # Helper to instantiate lightweight sessions for query services
    session_provider = providers.Callable(
        lambda factory: factory(),
        db_session_factory,
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
