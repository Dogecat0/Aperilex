"""Tests for Celery application configuration."""

from unittest.mock import Mock, patch

import pytest

from src.infrastructure.tasks.celery_app import create_celery_app


class TestCreateCeleryApp:
    """Test cases for create_celery_app function."""

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_with_default_settings(
        self, mock_celery_class, mock_settings
    ):
        """Test creating Celery app with default settings."""
        # Setup mock settings
        mock_settings.celery_broker_url = None
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_result_backend = None
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        result = create_celery_app()

        # Verify Celery was created with correct parameters
        mock_celery_class.assert_called_once_with(
            "aperilex",
            broker="redis://localhost:6379/0",  # Falls back to redis_url
            backend="redis://localhost:6379/0",  # Falls back to redis_url
            include=[
                "src.infrastructure.tasks.filing_tasks",
                "src.infrastructure.tasks.analysis_tasks",
            ],
        )

        # Verify configuration was updated
        mock_celery_instance.conf.update.assert_called_once()
        config_args = mock_celery_instance.conf.update.call_args[1]

        # Verify key configuration values
        assert config_args["task_serializer"] == "json"
        assert config_args["result_serializer"] == "json"
        assert config_args["accept_content"] == ["json"]
        assert config_args["timezone"] == "UTC"
        assert config_args["enable_utc"] is True
        assert config_args["task_track_started"] is True
        assert config_args["task_time_limit"] == 3600
        assert config_args["task_soft_time_limit"] == 3300
        assert config_args["worker_concurrency"] == 4

        # Verify task routing configuration
        assert "task_routes" in config_args
        task_routes = config_args["task_routes"]
        assert task_routes["analyze_filing"] == {"queue": "analysis_queue"}
        assert task_routes["analyze_filing_comprehensive"] == {"queue": "analysis_queue"}
        assert task_routes["batch_analyze_filings"] == {"queue": "analysis_queue"}
        assert task_routes["fetch_company_filings"] == {"queue": "filing_queue"}
        assert task_routes["process_filing"] == {"queue": "filing_queue"}
        assert task_routes["process_pending_filings"] == {"queue": "filing_queue"}

        # Verify additional configuration
        assert config_args["result_expires"] == 3600
        assert config_args["worker_prefetch_multiplier"] == 1
        assert config_args["task_acks_late"] is True
        assert config_args["worker_max_tasks_per_child"] == 1000
        assert config_args["task_send_sent_event"] is True
        assert config_args["worker_send_task_events"] is True

        assert result == mock_celery_instance

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_with_custom_broker_and_backend(
        self, mock_celery_class, mock_settings
    ):
        """Test creating Celery app with custom broker and backend settings."""
        # Setup mock settings with custom broker and backend
        mock_settings.celery_broker_url = "redis://custom-broker:6379/1"
        mock_settings.celery_result_backend = "redis://custom-backend:6379/2"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_task_serializer = "pickle"
        mock_settings.celery_result_serializer = "pickle"
        mock_settings.celery_accept_content = ["pickle", "json"]
        mock_settings.celery_timezone = "US/Pacific"
        mock_settings.celery_enable_utc = False
        mock_settings.celery_task_track_started = False
        mock_settings.celery_task_time_limit = 7200
        mock_settings.celery_task_soft_time_limit = 6900
        mock_settings.celery_worker_concurrency = 8

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        result = create_celery_app()

        # Verify Celery was created with custom broker and backend
        mock_celery_class.assert_called_once_with(
            "aperilex",
            broker="redis://custom-broker:6379/1",
            backend="redis://custom-backend:6379/2",
            include=[
                "src.infrastructure.tasks.filing_tasks",
                "src.infrastructure.tasks.analysis_tasks",
            ],
        )

        # Verify configuration with custom values
        mock_celery_instance.conf.update.assert_called_once()
        config_args = mock_celery_instance.conf.update.call_args[1]

        assert config_args["task_serializer"] == "pickle"
        assert config_args["result_serializer"] == "pickle"
        assert config_args["accept_content"] == ["pickle", "json"]
        assert config_args["timezone"] == "US/Pacific"
        assert config_args["enable_utc"] is False
        assert config_args["task_track_started"] is False
        assert config_args["task_time_limit"] == 7200
        assert config_args["task_soft_time_limit"] == 6900
        assert config_args["worker_concurrency"] == 8

        assert result == mock_celery_instance

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_task_routing_configuration(
        self, mock_celery_class, mock_settings
    ):
        """Test that task routing is configured correctly."""
        # Setup minimal mock settings
        mock_settings.celery_broker_url = None
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_result_backend = None
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        create_celery_app()

        # Get the configuration that was passed to conf.update
        config_args = mock_celery_instance.conf.update.call_args[1]
        task_routes = config_args["task_routes"]

        # Verify analysis tasks are routed to analysis_queue
        analysis_tasks = [
            "analyze_filing",
            "analyze_filing_comprehensive",
            "batch_analyze_filings",
        ]
        for task_name in analysis_tasks:
            assert task_name in task_routes
            assert task_routes[task_name] == {"queue": "analysis_queue"}

        # Verify filing tasks are routed to filing_queue
        filing_tasks = [
            "fetch_company_filings",
            "process_filing",
            "process_pending_filings",
        ]
        for task_name in filing_tasks:
            assert task_name in task_routes
            assert task_routes[task_name] == {"queue": "filing_queue"}

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_worker_configuration(
        self, mock_celery_class, mock_settings
    ):
        """Test worker-specific configuration options."""
        # Setup mock settings
        mock_settings.celery_broker_url = None
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_result_backend = None
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        create_celery_app()

        # Get the configuration that was passed to conf.update
        config_args = mock_celery_instance.conf.update.call_args[1]

        # Verify worker configuration
        assert config_args["worker_concurrency"] == 4
        assert config_args["worker_prefetch_multiplier"] == 1
        assert config_args["task_acks_late"] is True
        assert config_args["worker_max_tasks_per_child"] == 1000

        # Verify monitoring configuration
        assert config_args["task_send_sent_event"] is True
        assert config_args["worker_send_task_events"] is True

        # Verify result expiration
        assert config_args["result_expires"] == 3600

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_includes_correct_modules(
        self, mock_celery_class, mock_settings
    ):
        """Test that the correct task modules are included."""
        # Setup minimal mock settings
        mock_settings.celery_broker_url = None
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_result_backend = None
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        create_celery_app()

        # Verify the include parameter contains the correct modules
        call_args = mock_celery_class.call_args
        assert call_args[1]["include"] == [
            "src.infrastructure.tasks.filing_tasks",
            "src.infrastructure.tasks.analysis_tasks",
        ]


class TestCeleryAppInstance:
    """Test cases for the celery_app instance."""

    def test_celery_app_configuration_flow(self):
        """Test the configuration flow that creates celery_app."""
        # Test that create_celery_app returns a properly configured app
        result = create_celery_app()
        
        # Verify it's a Celery instance
        assert hasattr(result, 'conf')
        assert hasattr(result, 'autodiscover_tasks')
        
        # Verify configuration was applied
        assert result.conf.task_serializer is not None
        
    def test_celery_app_has_required_methods(self):
        """Test that celery_app has all required methods and attributes."""
        app = create_celery_app()
        
        # Verify essential Celery methods exist
        assert hasattr(app, 'task')
        assert hasattr(app, 'autodiscover_tasks')
        assert hasattr(app, 'conf')
        
        # Verify configuration object has expected attributes
        assert hasattr(app.conf, 'task_routes')
        assert hasattr(app.conf, 'task_serializer')


class TestCeleryAppEdgeCases:
    """Test edge cases for Celery app configuration."""

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_with_empty_settings(
        self, mock_celery_class, mock_settings
    ):
        """Test creating Celery app when settings are empty/None."""
        # Setup mock settings with None/empty values
        mock_settings.celery_broker_url = ""
        mock_settings.redis_url = ""
        mock_settings.celery_result_backend = ""
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        result = create_celery_app()

        # Verify Celery was created with empty string fallbacks
        mock_celery_class.assert_called_once_with(
            "aperilex",
            broker="",  # Falls back to empty redis_url
            backend="",  # Falls back to empty redis_url
            include=[
                "src.infrastructure.tasks.filing_tasks",
                "src.infrastructure.tasks.analysis_tasks",
            ],
        )

        assert result == mock_celery_instance

    @patch('src.infrastructure.tasks.celery_app.settings')
    @patch('src.infrastructure.tasks.celery_app.Celery')
    def test_create_celery_app_configuration_completeness(
        self, mock_celery_class, mock_settings
    ):
        """Test that all required configuration options are set."""
        # Setup mock settings
        mock_settings.celery_broker_url = "redis://localhost:6379/0"
        mock_settings.celery_result_backend = "redis://localhost:6379/0"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.celery_task_serializer = "json"
        mock_settings.celery_result_serializer = "json"
        mock_settings.celery_accept_content = ["json"]
        mock_settings.celery_timezone = "UTC"
        mock_settings.celery_enable_utc = True
        mock_settings.celery_task_track_started = True
        mock_settings.celery_task_time_limit = 3600
        mock_settings.celery_task_soft_time_limit = 3300
        mock_settings.celery_worker_concurrency = 4

        # Setup mock Celery instance
        mock_celery_instance = Mock()
        mock_celery_class.return_value = mock_celery_instance

        # Execute function
        create_celery_app()

        # Get configuration
        config_args = mock_celery_instance.conf.update.call_args[1]

        # Verify all expected configuration keys are present
        expected_config_keys = [
            "task_serializer",
            "result_serializer",
            "accept_content",
            "timezone",
            "enable_utc",
            "task_track_started",
            "task_time_limit",
            "task_soft_time_limit",
            "worker_concurrency",
            "task_routes",
            "result_expires",
            "worker_prefetch_multiplier",
            "task_acks_late",
            "worker_max_tasks_per_child",
            "task_send_sent_event",
            "worker_send_task_events",
        ]

        for key in expected_config_keys:
            assert key in config_args, f"Configuration key '{key}' is missing"

        # Verify that all task queues are properly configured
        task_routes = config_args["task_routes"]
        expected_tasks = [
            "analyze_filing",
            "analyze_filing_comprehensive",
            "batch_analyze_filings",
            "fetch_company_filings",
            "process_filing",
            "process_pending_filings",
        ]

        for task in expected_tasks:
            assert task in task_routes, f"Task '{task}' not found in routes"
            assert "queue" in task_routes[task], f"Queue not specified for task '{task}'"