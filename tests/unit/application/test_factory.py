"""Tests for ServiceFactory with comprehensive coverage."""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.shared.config.settings import Settings


class TestServiceFactory:
    """Test cases for ServiceFactory initialization."""

    def test_init(self):
        """Test ServiceFactory initialization."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        settings.celery_broker_url = "redis://localhost:6379/1"
        
        factory = ServiceFactory(settings)
        
        assert factory.settings is settings
        assert factory._redis_service is None
        assert factory._repositories == {}
        assert factory._services == {}

    def test_use_redis_property_true(self):
        """Test use_redis property when Redis URL is configured."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        
        factory = ServiceFactory(settings)
        
        assert factory.use_redis is True

    def test_use_redis_property_false_none(self):
        """Test use_redis property when Redis URL is None."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        factory = ServiceFactory(settings)
        
        assert factory.use_redis is False

    def test_use_redis_property_false_empty(self):
        """Test use_redis property when Redis URL is empty string."""
        settings = Mock(spec=Settings)
        settings.redis_url = ""
        
        factory = ServiceFactory(settings)
        
        assert factory.use_redis is False

    def test_use_celery_property_true(self):
        """Test use_celery property when Celery broker URL is configured."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = "redis://localhost:6379/1"
        
        factory = ServiceFactory(settings)
        
        assert factory.use_celery is True

    def test_use_celery_property_false_none(self):
        """Test use_celery property when Celery broker URL is None."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = None
        
        factory = ServiceFactory(settings)
        
        assert factory.use_celery is False

    def test_use_celery_property_false_empty(self):
        """Test use_celery property when Celery broker URL is empty string."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = ""
        
        factory = ServiceFactory(settings)
        
        assert factory.use_celery is False


class TestServiceFactoryRedisService:
    """Test cases for Redis service creation."""

    def test_get_redis_service_none_when_not_configured(self):
        """Test get_redis_service returns None when Redis is not configured."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        factory = ServiceFactory(settings)
        result = factory.get_redis_service()
        
        assert result is None

    @patch('src.application.factory.RedisService')
    @patch('src.application.factory.logger')
    def test_get_redis_service_creates_service(self, mock_logger, mock_redis_service_class):
        """Test get_redis_service creates Redis service when configured."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        
        mock_redis_service = Mock()
        mock_redis_service_class.return_value = mock_redis_service
        
        factory = ServiceFactory(settings)
        result = factory.get_redis_service()
        
        assert result is mock_redis_service
        assert factory._redis_service is mock_redis_service
        mock_redis_service_class.assert_called_once_with("redis://localhost:6379/0")
        mock_logger.info.assert_called_once_with("Initializing Redis service")

    @patch('src.application.factory.RedisService')
    def test_get_redis_service_returns_cached_instance(self, mock_redis_service_class):
        """Test get_redis_service returns cached Redis service instance."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        
        mock_redis_service = Mock()
        mock_redis_service_class.return_value = mock_redis_service
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.get_redis_service()
        # Second call
        result2 = factory.get_redis_service()
        
        assert result1 is result2
        assert result1 is mock_redis_service
        mock_redis_service_class.assert_called_once()  # Only called once


class TestServiceFactoryCacheService:
    """Test cases for cache service creation."""

    @patch('src.application.factory.CacheService')
    @patch('src.application.factory.logger')
    def test_create_cache_service_with_redis(self, mock_logger, mock_cache_service_class):
        """Test creating cache service with Redis backend."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        
        mock_redis_service = Mock()
        mock_cache_service = Mock()
        mock_cache_service_class.return_value = mock_cache_service
        
        factory = ServiceFactory(settings)
        factory._redis_service = mock_redis_service
        
        result = factory.create_cache_service()
        
        assert result is mock_cache_service
        mock_cache_service_class.assert_called_once_with(redis_service=mock_redis_service)
        mock_logger.info.assert_called_once_with("Creating CacheService with Redis backend")

    @patch('src.application.factory.CacheService')
    @patch('src.application.factory.logger')
    def test_create_cache_service_in_memory(self, mock_logger, mock_cache_service_class):
        """Test creating cache service with in-memory backend."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        mock_cache_service = Mock()
        mock_cache_service_class.return_value = mock_cache_service
        
        factory = ServiceFactory(settings)
        result = factory.create_cache_service()
        
        assert result is mock_cache_service
        mock_cache_service_class.assert_called_once_with()
        mock_logger.info.assert_called_once_with("Creating CacheService with in-memory backend")

    @patch('src.application.factory.CacheService')
    def test_create_cache_service_returns_cached_instance(self, mock_cache_service_class):
        """Test create_cache_service returns cached service instance."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        mock_cache_service = Mock()
        mock_cache_service_class.return_value = mock_cache_service
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.create_cache_service()
        # Second call
        result2 = factory.create_cache_service()
        
        assert result1 is result2
        assert result1 is mock_cache_service
        mock_cache_service_class.assert_called_once()  # Only called once


class TestServiceFactoryTaskService:
    """Test cases for task service creation."""

    @patch('src.application.factory.TaskService')
    @patch('src.application.factory.logger')
    def test_create_task_service_with_redis(self, mock_logger, mock_task_service_class):
        """Test creating task service with Redis backend."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        
        mock_redis_service = Mock()
        mock_task_service = Mock()
        mock_task_service_class.return_value = mock_task_service
        
        factory = ServiceFactory(settings)
        factory._redis_service = mock_redis_service
        
        result = factory.create_task_service()
        
        assert result is mock_task_service
        mock_task_service_class.assert_called_once_with(redis_service=mock_redis_service)
        mock_logger.info.assert_called_once_with("Creating TaskService with Redis backend")

    @patch('src.application.factory.TaskService')
    @patch('src.application.factory.logger')
    def test_create_task_service_in_memory(self, mock_logger, mock_task_service_class):
        """Test creating task service with in-memory backend."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        mock_task_service = Mock()
        mock_task_service_class.return_value = mock_task_service
        
        factory = ServiceFactory(settings)
        result = factory.create_task_service()
        
        assert result is mock_task_service
        mock_task_service_class.assert_called_once_with()
        mock_logger.info.assert_called_once_with("Creating TaskService with in-memory backend")

    @patch('src.application.factory.TaskService')
    def test_create_task_service_returns_cached_instance(self, mock_task_service_class):
        """Test create_task_service returns cached service instance."""
        settings = Mock(spec=Settings)
        settings.redis_url = None
        
        mock_task_service = Mock()
        mock_task_service_class.return_value = mock_task_service
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.create_task_service()
        # Second call
        result2 = factory.create_task_service()
        
        assert result1 is result2
        assert result1 is mock_task_service
        mock_task_service_class.assert_called_once()  # Only called once


class TestServiceFactoryBackgroundTaskCoordinator:
    """Test cases for background task coordinator creation."""

    @patch('src.application.factory.BackgroundTaskCoordinator')
    @patch('src.application.factory.logger')
    def test_create_background_task_coordinator_with_celery(
        self, mock_logger, mock_coordinator_class
    ):
        """Test creating background task coordinator with Celery backend."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = "redis://localhost:6379/1"
        
        session = Mock(spec=AsyncSession)
        mock_analysis_orchestrator = Mock()
        mock_task_service = Mock()
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        
        factory = ServiceFactory(settings)
        factory.create_analysis_orchestrator = Mock(return_value=mock_analysis_orchestrator)
        factory.create_task_service = Mock(return_value=mock_task_service)
        
        result = factory.create_background_task_coordinator(session)
        
        assert result is mock_coordinator
        mock_coordinator_class.assert_called_once_with(
            analysis_orchestrator=mock_analysis_orchestrator,
            task_service=mock_task_service,
            use_celery=True,
        )
        mock_logger.info.assert_called_once_with(
            "Creating BackgroundTaskCoordinator with Celery backend"
        )

    @patch('src.application.factory.BackgroundTaskCoordinator')
    @patch('src.application.factory.logger')
    def test_create_background_task_coordinator_synchronous(
        self, mock_logger, mock_coordinator_class
    ):
        """Test creating background task coordinator with synchronous backend."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = None
        
        session = Mock(spec=AsyncSession)
        mock_analysis_orchestrator = Mock()
        mock_task_service = Mock()
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        
        factory = ServiceFactory(settings)
        factory.create_analysis_orchestrator = Mock(return_value=mock_analysis_orchestrator)
        factory.create_task_service = Mock(return_value=mock_task_service)
        
        result = factory.create_background_task_coordinator(session)
        
        assert result is mock_coordinator
        mock_coordinator_class.assert_called_once_with(
            analysis_orchestrator=mock_analysis_orchestrator,
            task_service=mock_task_service,
            use_celery=False,
        )
        mock_logger.info.assert_called_once_with(
            "Creating BackgroundTaskCoordinator with synchronous backend"
        )

    @patch('src.application.factory.BackgroundTaskCoordinator')
    def test_create_background_task_coordinator_returns_cached_instance(
        self, mock_coordinator_class
    ):
        """Test create_background_task_coordinator returns cached coordinator instance."""
        settings = Mock(spec=Settings)
        settings.celery_broker_url = None
        
        session = Mock(spec=AsyncSession)
        mock_analysis_orchestrator = Mock()
        mock_task_service = Mock()
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        
        factory = ServiceFactory(settings)
        factory.create_analysis_orchestrator = Mock(return_value=mock_analysis_orchestrator)
        factory.create_task_service = Mock(return_value=mock_task_service)
        
        # First call
        result1 = factory.create_background_task_coordinator(session)
        # Second call
        result2 = factory.create_background_task_coordinator(session)
        
        assert result1 is result2
        assert result1 is mock_coordinator
        mock_coordinator_class.assert_called_once()  # Only called once


class TestServiceFactoryRepositories:
    """Test cases for repository creation."""

    @patch('src.application.factory.AnalysisRepository')
    @patch('src.application.factory.logger')
    def test_create_analysis_repository(self, mock_logger, mock_repository_class):
        """Test creating analysis repository."""
        session = Mock(spec=AsyncSession)
        mock_repository = Mock()
        mock_repository_class.return_value = mock_repository
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_analysis_repository(session)
        
        assert result is mock_repository
        mock_repository_class.assert_called_once_with(session)
        mock_logger.debug.assert_called_once_with(
            "Creating AnalysisRepository with database session"
        )

    @patch('src.application.factory.FilingRepository')
    @patch('src.application.factory.logger')
    def test_create_filing_repository(self, mock_logger, mock_repository_class):
        """Test creating filing repository."""
        session = Mock(spec=AsyncSession)
        mock_repository = Mock()
        mock_repository_class.return_value = mock_repository
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_filing_repository(session)
        
        assert result is mock_repository
        mock_repository_class.assert_called_once_with(session)
        mock_logger.debug.assert_called_once_with(
            "Creating FilingRepository with database session"
        )

    @patch('src.application.factory.CompanyRepository')
    @patch('src.application.factory.logger')
    def test_create_company_repository(self, mock_logger, mock_repository_class):
        """Test creating company repository."""
        session = Mock(spec=AsyncSession)
        mock_repository = Mock()
        mock_repository_class.return_value = mock_repository
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_company_repository(session)
        
        assert result is mock_repository
        mock_repository_class.assert_called_once_with(session)
        mock_logger.debug.assert_called_once_with(
            "Creating CompanyRepository with database session"
        )


class TestServiceFactoryEdgarService:
    """Test cases for Edgar service creation."""

    @patch('src.application.factory.EdgarService')
    @patch('src.application.factory.logger')
    def test_create_edgar_service(self, mock_logger, mock_edgar_service_class):
        """Test creating Edgar service."""
        mock_edgar_service = Mock()
        mock_edgar_service_class.return_value = mock_edgar_service
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_edgar_service()
        
        assert result is mock_edgar_service
        mock_edgar_service_class.assert_called_once()
        mock_logger.debug.assert_called_once_with("Creating EdgarService")

    @patch('src.application.factory.EdgarService')
    def test_create_edgar_service_returns_cached_instance(self, mock_edgar_service_class):
        """Test create_edgar_service returns cached service instance."""
        mock_edgar_service = Mock()
        mock_edgar_service_class.return_value = mock_edgar_service
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.create_edgar_service()
        # Second call
        result2 = factory.create_edgar_service()
        
        assert result1 is result2
        assert result1 is mock_edgar_service
        mock_edgar_service_class.assert_called_once()  # Only called once


class TestServiceFactoryLLMProvider:
    """Test cases for LLM provider creation."""

    @patch('src.infrastructure.llm.openai_provider.OpenAIProvider')
    @patch('src.application.factory.logger')
    def test_create_llm_provider(self, mock_logger, mock_llm_provider_class):
        """Test creating LLM provider."""
        mock_llm_provider = Mock()
        mock_llm_provider_class.return_value = mock_llm_provider
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory._create_llm_provider()
        
        assert result is mock_llm_provider
        mock_llm_provider_class.assert_called_once()
        mock_logger.debug.assert_called_once_with("Creating OpenAI LLM provider")

    @patch('src.infrastructure.llm.openai_provider.OpenAIProvider')
    def test_create_llm_provider_returns_cached_instance(self, mock_llm_provider_class):
        """Test _create_llm_provider returns cached provider instance."""
        mock_llm_provider = Mock()
        mock_llm_provider_class.return_value = mock_llm_provider
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory._create_llm_provider()
        # Second call
        result2 = factory._create_llm_provider()
        
        assert result1 is result2
        assert result1 is mock_llm_provider
        mock_llm_provider_class.assert_called_once()  # Only called once


class TestServiceFactoryAnalysisOrchestrator:
    """Test cases for analysis orchestrator creation."""

    @patch('src.application.factory.logger')
    def test_create_analysis_orchestrator_without_session(self, mock_logger):
        """Test creating analysis orchestrator without session returns mock."""
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_analysis_orchestrator(session=None)
        
        # Should return a MagicMock
        assert isinstance(result, MagicMock)
        mock_logger.debug.assert_called_once_with(
            "Creating AnalysisOrchestrator (mocked - no session provided)"
        )

    @patch('src.application.factory.AnalysisOrchestrator')
    @patch('src.application.factory.logger')
    def test_create_analysis_orchestrator_with_session(
        self, mock_logger, mock_orchestrator_class
    ):
        """Test creating analysis orchestrator with session."""
        session = Mock(spec=AsyncSession)
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        mock_analysis_repository = Mock()
        mock_filing_repository = Mock()
        mock_edgar_service = Mock()
        mock_template_service = Mock()
        mock_llm_provider = Mock()
        
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        factory.create_analysis_repository = Mock(return_value=mock_analysis_repository)
        factory.create_filing_repository = Mock(return_value=mock_filing_repository)
        factory.create_edgar_service = Mock(return_value=mock_edgar_service)
        factory.create_analysis_template_service = Mock(return_value=mock_template_service)
        factory._create_llm_provider = Mock(return_value=mock_llm_provider)
        
        result = factory.create_analysis_orchestrator(session)
        
        assert result is mock_orchestrator
        mock_orchestrator_class.assert_called_once_with(
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            edgar_service=mock_edgar_service,
            llm_provider=mock_llm_provider,
            template_service=mock_template_service,
        )
        mock_logger.debug.assert_called_once_with(
            "Creating AnalysisOrchestrator with session-dependent repositories"
        )

    @patch('src.application.factory.AnalysisOrchestrator')
    def test_create_analysis_orchestrator_caches_per_session(self, mock_orchestrator_class):
        """Test analysis orchestrator is cached per session ID."""
        session1 = Mock(spec=AsyncSession)
        session2 = Mock(spec=AsyncSession)
        
        mock_orchestrator1 = Mock()
        mock_orchestrator2 = Mock()
        mock_orchestrator_class.side_effect = [mock_orchestrator1, mock_orchestrator2]
        
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        # Mock other dependencies
        factory.create_analysis_repository = Mock()
        factory.create_filing_repository = Mock()
        factory.create_edgar_service = Mock()
        factory.create_analysis_template_service = Mock()
        factory._create_llm_provider = Mock()
        
        # Call with first session twice
        result1a = factory.create_analysis_orchestrator(session1)
        result1b = factory.create_analysis_orchestrator(session1)
        
        # Call with second session
        result2 = factory.create_analysis_orchestrator(session2)
        
        # First session calls should return same instance
        assert result1a is result1b
        assert result1a is mock_orchestrator1
        
        # Second session should return different instance
        assert result2 is mock_orchestrator2
        assert result2 != result1a
        
        # Should have created two orchestrators total
        assert mock_orchestrator_class.call_count == 2


class TestServiceFactoryAnalysisTemplateService:
    """Test cases for analysis template service creation."""

    @patch('src.application.factory.AnalysisTemplateService')
    @patch('src.application.factory.logger')
    def test_create_analysis_template_service(self, mock_logger, mock_template_service_class):
        """Test creating analysis template service."""
        mock_template_service = Mock()
        mock_template_service_class.return_value = mock_template_service
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_analysis_template_service()
        
        assert result is mock_template_service
        mock_template_service_class.assert_called_once()
        mock_logger.debug.assert_called_once_with("Creating AnalysisTemplateService")

    @patch('src.application.factory.AnalysisTemplateService')
    def test_create_analysis_template_service_returns_cached_instance(
        self, mock_template_service_class
    ):
        """Test create_analysis_template_service returns cached service instance."""
        mock_template_service = Mock()
        mock_template_service_class.return_value = mock_template_service
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.create_analysis_template_service()
        # Second call
        result2 = factory.create_analysis_template_service()
        
        assert result1 is result2
        assert result1 is mock_template_service
        mock_template_service_class.assert_called_once()  # Only called once


class TestServiceFactoryDispatcher:
    """Test cases for dispatcher creation."""

    @patch('src.application.factory.register_handlers')
    @patch('src.application.factory.Dispatcher')
    @patch('src.application.factory.logger')
    def test_create_dispatcher(self, mock_logger, mock_dispatcher_class, mock_register):
        """Test creating dispatcher with handlers registered."""
        mock_dispatcher = Mock()
        mock_dispatcher_class.return_value = mock_dispatcher
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_dispatcher()
        
        assert result is mock_dispatcher
        mock_dispatcher_class.assert_called_once()
        mock_register.assert_called_once_with(mock_dispatcher)
        mock_logger.info.assert_called_once_with("Creating CQRS Dispatcher")

    @patch('src.application.factory.register_handlers')
    @patch('src.application.factory.Dispatcher')
    def test_create_dispatcher_returns_cached_instance(
        self, mock_dispatcher_class, mock_register
    ):
        """Test create_dispatcher returns cached dispatcher instance."""
        mock_dispatcher = Mock()
        mock_dispatcher_class.return_value = mock_dispatcher
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        
        # First call
        result1 = factory.create_dispatcher()
        # Second call
        result2 = factory.create_dispatcher()
        
        assert result1 is result2
        assert result1 is mock_dispatcher
        mock_dispatcher_class.assert_called_once()  # Only called once
        mock_register.assert_called_once()  # Only called once


class TestServiceFactoryApplicationService:
    """Test cases for application service creation."""

    @patch('src.application.factory.logger')
    def test_create_application_service_without_session(self, mock_logger):
        """Test creating application service without session returns mock."""
        settings = Mock(spec=Settings)
        
        factory = ServiceFactory(settings)
        result = factory.create_application_service(session=None)
        
        # Should return a MagicMock
        assert isinstance(result, MagicMock)
        mock_logger.debug.assert_called_once_with(
            "Creating ApplicationService (mocked - no session provided)"
        )

    @patch('src.application.factory.ApplicationService')
    @patch('src.application.factory.logger')
    def test_create_application_service_with_session(
        self, mock_logger, mock_app_service_class
    ):
        """Test creating application service with session and all dependencies."""
        session = Mock(spec=AsyncSession)
        mock_app_service = Mock()
        mock_app_service_class.return_value = mock_app_service
        
        # Mock all dependencies
        mock_dispatcher = Mock()
        mock_analysis_orchestrator = Mock()
        mock_template_service = Mock()
        mock_edgar_service = Mock()
        mock_background_coordinator = Mock()
        mock_analysis_repository = Mock()
        mock_filing_repository = Mock()
        mock_company_repository = Mock()
        
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        settings.celery_broker_url = "redis://localhost:6379/1"
        factory = ServiceFactory(settings)
        
        factory.create_dispatcher = Mock(return_value=mock_dispatcher)
        factory.create_analysis_orchestrator = Mock(return_value=mock_analysis_orchestrator)
        factory.create_analysis_template_service = Mock(return_value=mock_template_service)
        factory.create_edgar_service = Mock(return_value=mock_edgar_service)
        factory.create_background_task_coordinator = Mock(return_value=mock_background_coordinator)
        factory.create_analysis_repository = Mock(return_value=mock_analysis_repository)
        factory.create_filing_repository = Mock(return_value=mock_filing_repository)
        factory.create_company_repository = Mock(return_value=mock_company_repository)
        
        result = factory.create_application_service(session)
        
        assert result is mock_app_service
        mock_app_service_class.assert_called_once_with(
            dispatcher=mock_dispatcher,
            analysis_orchestrator=mock_analysis_orchestrator,
            analysis_template_service=mock_template_service,
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
            background_task_coordinator=mock_background_coordinator,
        )
        mock_logger.info.assert_called_once_with(
            "Creating ApplicationService with session-dependent repositories "
            "(Redis: True, Celery: True)"
        )


class TestServiceFactoryHandlerDependencies:
    """Test cases for handler dependencies."""

    def test_get_handler_dependencies(self):
        """Test getting handler dependencies with all services."""
        session = Mock(spec=AsyncSession)
        
        # Mock all dependencies
        mock_analysis_repository = Mock()
        mock_filing_repository = Mock()
        mock_company_repository = Mock()
        mock_edgar_service = Mock()
        mock_analysis_orchestrator = Mock()
        mock_background_coordinator = Mock()
        mock_template_service = Mock()
        
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        factory.create_analysis_repository = Mock(return_value=mock_analysis_repository)
        factory.create_filing_repository = Mock(return_value=mock_filing_repository)
        factory.create_company_repository = Mock(return_value=mock_company_repository)
        factory.create_edgar_service = Mock(return_value=mock_edgar_service)
        factory.create_analysis_orchestrator = Mock(return_value=mock_analysis_orchestrator)
        factory.create_background_task_coordinator = Mock(return_value=mock_background_coordinator)
        factory.create_analysis_template_service = Mock(return_value=mock_template_service)
        
        result = factory.get_handler_dependencies(session)
        
        expected_dependencies = {
            "analysis_repository": mock_analysis_repository,
            "filing_repository": mock_filing_repository,
            "company_repository": mock_company_repository,
            "edgar_service": mock_edgar_service,
            "analysis_orchestrator": mock_analysis_orchestrator,
            "background_task_coordinator": mock_background_coordinator,
            "template_service": mock_template_service,
        }
        
        assert result == expected_dependencies
        
        # Verify all create methods were called with correct parameters
        factory.create_analysis_repository.assert_called_once_with(session)
        factory.create_filing_repository.assert_called_once_with(session)
        factory.create_company_repository.assert_called_once_with(session)
        factory.create_edgar_service.assert_called_once()
        factory.create_analysis_orchestrator.assert_called_once_with(session)
        factory.create_background_task_coordinator.assert_called_once()
        factory.create_analysis_template_service.assert_called_once()


class TestServiceFactoryCleanup:
    """Test cases for cleanup operations."""

    async def test_cleanup_with_no_redis_service(self):
        """Test cleanup when no Redis service is initialized."""
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        # Should complete without error
        await factory.cleanup()

    @patch('src.application.factory.logger')
    async def test_cleanup_with_redis_service(self, mock_logger):
        """Test cleanup when Redis service is initialized."""
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        # Mock Redis service with async disconnect
        mock_redis_service = Mock()
        mock_redis_service.disconnect = AsyncMock()
        factory._redis_service = mock_redis_service
        
        await factory.cleanup()
        
        mock_redis_service.disconnect.assert_called_once()
        mock_logger.info.assert_called_once_with("Closing Redis connection")

    @patch('src.application.factory.logger')
    async def test_cleanup_redis_disconnect_error(self, mock_logger):
        """Test cleanup propagates Redis disconnect errors."""
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        # Mock Redis service that raises error on disconnect
        mock_redis_service = Mock()
        mock_redis_service.disconnect = AsyncMock(side_effect=Exception("Redis error"))
        factory._redis_service = mock_redis_service
        
        # Should raise the Redis exception
        with pytest.raises(Exception, match="Redis error"):
            await factory.cleanup()
        
        mock_redis_service.disconnect.assert_called_once()
        mock_logger.info.assert_called_once_with("Closing Redis connection")


class TestServiceFactoryEdgeCases:
    """Test edge cases and error scenarios."""

    def test_multiple_configurations(self):
        """Test factory with different configuration combinations."""
        # Redis only
        settings_redis_only = Mock(spec=Settings)
        settings_redis_only.redis_url = "redis://localhost:6379/0"
        settings_redis_only.celery_broker_url = None
        
        factory_redis = ServiceFactory(settings_redis_only)
        assert factory_redis.use_redis is True
        assert factory_redis.use_celery is False
        
        # Celery only
        settings_celery_only = Mock(spec=Settings)
        settings_celery_only.redis_url = None
        settings_celery_only.celery_broker_url = "redis://localhost:6379/1"
        
        factory_celery = ServiceFactory(settings_celery_only)
        assert factory_celery.use_redis is False
        assert factory_celery.use_celery is True
        
        # Both
        settings_both = Mock(spec=Settings)
        settings_both.redis_url = "redis://localhost:6379/0"
        settings_both.celery_broker_url = "redis://localhost:6379/1"
        
        factory_both = ServiceFactory(settings_both)
        assert factory_both.use_redis is True
        assert factory_both.use_celery is True
        
        # Neither
        settings_neither = Mock(spec=Settings)
        settings_neither.redis_url = None
        settings_neither.celery_broker_url = None
        
        factory_neither = ServiceFactory(settings_neither)
        assert factory_neither.use_redis is False
        assert factory_neither.use_celery is False

    def test_service_caching_independence(self):
        """Test that different services are cached independently."""
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        # Set up mocks for different services
        with patch('src.application.factory.EdgarService') as mock_edgar:
            with patch('src.application.factory.AnalysisTemplateService') as mock_template:
                mock_edgar_instance = Mock()
                mock_template_instance = Mock()
                mock_edgar.return_value = mock_edgar_instance
                mock_template.return_value = mock_template_instance
                
                # Create services
                edgar1 = factory.create_edgar_service()
                template1 = factory.create_analysis_template_service()
                edgar2 = factory.create_edgar_service()
                template2 = factory.create_analysis_template_service()
                
                # Each service type should be cached independently
                assert edgar1 is edgar2
                assert template1 is template2
                assert edgar1 is not template1
                
                # Each service should only be created once
                mock_edgar.assert_called_once()
                mock_template.assert_called_once()

    def test_session_id_based_caching(self):
        """Test that session-dependent services are cached by session ID."""
        settings = Mock(spec=Settings)
        factory = ServiceFactory(settings)
        
        session1 = Mock(spec=AsyncSession)
        session2 = Mock(spec=AsyncSession)
        
        with patch('src.application.factory.AnalysisOrchestrator') as mock_orchestrator:
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_orchestrator.side_effect = [mock_instance1, mock_instance2]
            
            # Mock other dependencies
            factory.create_analysis_repository = Mock()
            factory.create_filing_repository = Mock()
            factory.create_edgar_service = Mock()
            factory.create_analysis_template_service = Mock()
            factory._create_llm_provider = Mock()
            
            # Create orchestrators for different sessions
            orch1a = factory.create_analysis_orchestrator(session1)
            orch1b = factory.create_analysis_orchestrator(session1)
            orch2 = factory.create_analysis_orchestrator(session2)
            
            # Same session should return same instance
            assert orch1a is orch1b
            assert orch1a is mock_instance1
            
            # Different session should return different instance
            assert orch2 is mock_instance2
            assert orch2 != orch1a
            
            # Should create two different instances
            assert mock_orchestrator.call_count == 2