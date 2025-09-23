"""Factory for creating provider implementations based on configuration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dependency_injector import providers

from src.application.interfaces.worker import IWorkerProvider
from src.shared.enums import (
    DatabaseProvider,
    DataSourceProvider,
    LLMProvider,
    QueueProvider,
    StorageProvider,
    WorkerProvider,
)


class _MissingWorkerProvider(IWorkerProvider):
    """Fallback worker provider used when optional dependencies are missing."""

    def __init__(self, message: str) -> None:
        self._message = message

    async def execute_task(
        self,
        task_message: TaskMessage,
        context: WorkerContext,
    ) -> WorkerResult:
        raise RuntimeError(self._message)

    async def health_check(self) -> WorkerHealthStatus:
        raise RuntimeError(self._message)

    async def get_metrics(self) -> WorkerMetrics:
        raise RuntimeError(self._message)

    async def warm_up(self) -> bool:
        raise RuntimeError(self._message)

    async def shutdown(self, graceful: bool = True) -> bool:
        raise RuntimeError(self._message)

    async def scale(self, instances: int) -> bool:
        raise RuntimeError(self._message)

    async def get_logs(
        self,
        task_id: TaskId | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[WorkerLogEntry]:
        raise RuntimeError(self._message)

    async def retry_task(
        self,
        task_id: TaskId,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> WorkerResult:
        raise RuntimeError(self._message)

    async def cancel_task(self, task_id: TaskId) -> bool:
        raise RuntimeError(self._message)


if TYPE_CHECKING:
    from src.application.interfaces import (
        IAuthenticationProvider,
        IConfigProvider,
        IDatabaseProvider,
        IDataSourceProvider,
        IEventPublisher,
        IEventStore,
        ILLMProvider,
        IQueueProvider,
        ISecretManager,
        ISSEProvider,
        IStorageProvider,
        IWorkerProvider,
    )
    from src.application.interfaces.worker import (
        WorkerContext,
        WorkerHealthStatus,
        WorkerLogEntry,
        WorkerMetrics,
        WorkerResult,
    )
    from src.shared.models.queue import TaskMessage
    from src.shared.types import TaskId


class ProviderFactory:
    """Factory for creating provider implementations based on configuration."""

    @staticmethod
    def create_config_provider(environment: str) -> providers.Provider[IConfigProvider]:
        """
        Create configuration provider based on environment.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Provider instance for configuration
        """
        from src.infrastructure.config import EnvironmentConfigProvider
        from src.infrastructure.config.composite_config_provider import (
            CompositeConfigProvider,
        )
        from src.infrastructure.config.json_config_provider import JSONConfigProvider

        config_sources: list[providers.Provider[IConfigProvider]] = []

        # Environment variables always take precedence
        config_sources.append(
            providers.Singleton(
                EnvironmentConfigProvider,
                prefix="APERILEX",
            )
        )

        config_dir = Path("config")
        if config_dir.exists():
            env_config_path = config_dir / f"{environment}.json"
            default_config_path = config_dir / "default.json"

            if env_config_path.exists():
                config_sources.append(
                    providers.Singleton(
                        JSONConfigProvider,
                        file_path=str(env_config_path),
                    )
                )

            if default_config_path.exists():
                config_sources.append(
                    providers.Singleton(
                        JSONConfigProvider,
                        file_path=str(default_config_path),
                    )
                )

        if len(config_sources) == 1:
            return config_sources[0]

        return providers.Singleton(
            CompositeConfigProvider,
            providers=providers.List(*config_sources),
        )

    @staticmethod
    def create_secret_manager(environment: str) -> providers.Provider[ISecretManager]:
        """
        Create secret manager based on environment.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Provider instance for secret management
        """
        from src.infrastructure.secret import LocalSecretManager

        if environment in ["development", "test"]:
            return providers.Singleton(
                LocalSecretManager,
                secrets_file=".secrets/local_secrets.json",
            )
        else:
            # Production environments would use AWS Secrets Manager
            # For now, fall back to local implementation
            return providers.Singleton(
                LocalSecretManager,
                secrets_file=".secrets/local_secrets.json",
            )

    @staticmethod
    def create_authentication_provider(
        environment: str,
    ) -> providers.Provider[IAuthenticationProvider]:
        """Create authentication provider based on environment."""

        from src.infrastructure.providers.authentication import (
            MockAuthenticationProvider,
        )

        # For development/test environments use mock implementation.
        # Production provider wiring will be introduced in a later stage.
        return providers.Singleton(MockAuthenticationProvider)

    @staticmethod
    def create_sse_provider(environment: str) -> providers.Provider[ISSEProvider]:
        """Create SSE provider based on environment."""

        from src.infrastructure.providers.sse import InMemorySSEProvider

        # Default to in-memory SSE provider for local development/testing.
        return providers.Singleton(InMemorySSEProvider)

    @staticmethod
    def create_event_publisher(
        environment: str,
        sse_provider: providers.Provider[ISSEProvider],
    ) -> providers.Provider[IEventPublisher]:
        """Create event publisher based on environment."""

        from src.infrastructure.providers.events import (
            CompositeEventPublisher,
            LoggingEventPublisher,
            SSEEventPublisher,
        )

        # Start with SSE-based event publishing. Additional publishers
        # (SNS, Webhooks, etc.) will be added in later stages.
        sse_event_publisher = providers.Singleton(
            SSEEventPublisher,
            sse_provider=sse_provider,
        )

        logging_event_publisher = providers.Singleton(LoggingEventPublisher)

        return providers.Singleton(
            CompositeEventPublisher,
            publishers=providers.List(
                sse_event_publisher,
                logging_event_publisher,
            ),
        )

    @staticmethod
    def create_event_store(
        environment: str,
    ) -> providers.Provider[IEventStore]:
        """Create event store implementation based on environment."""

        from src.infrastructure.providers.events import InMemoryEventStore

        # In-memory store is sufficient for development/testing. Persistent options
        # can be added in later stages (e.g., DynamoDB, Postgres).
        return providers.Singleton(InMemoryEventStore)

    @staticmethod
    def create_storage_provider(
        provider_type: StorageProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[IStorageProvider]:
        """
        Create storage provider based on type.

        Args:
            provider_type: Type of storage provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for storage
        """
        if provider_type == StorageProvider.S3:
            from src.infrastructure.providers.storage import S3StorageProvider

            # Get S3 configuration from config provider
            bucket_name = config_provider.get(
                "storage.s3.bucket_name", "aperilex-storage"
            )
            region = config_provider.get("storage.s3.region", "us-east-2")
            prefix = config_provider.get("storage.s3.prefix", "")

            # Get AWS credentials from secret manager if configured
            # Note: Credentials will be fetched when needed, not during initialization
            aws_access_key_id = None
            aws_secret_access_key = None

            return providers.Singleton(
                S3StorageProvider,
                bucket_name=bucket_name,
                region=region,
                prefix=prefix,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        elif provider_type == StorageProvider.LOCAL:
            from src.infrastructure.providers.storage import LocalStorageProvider

            # Get local storage configuration
            base_path = config_provider.get("storage.local.base_path", "./data/storage")

            return providers.Singleton(
                LocalStorageProvider,
                base_path=base_path,
            )
        else:
            raise ValueError(f"Unknown storage provider type: {provider_type}")

    @staticmethod
    def create_queue_provider(
        provider_type: QueueProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[IQueueProvider]:
        """
        Create queue provider based on type.

        Args:
            provider_type: Type of queue provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for queue
        """
        if provider_type == QueueProvider.SQS:
            from src.infrastructure.providers.queue import (
                load_sqs_config,
                load_sqs_queue_provider,
            )

            try:
                sqs_provider_cls = load_sqs_queue_provider()
                sqs_config_cls = load_sqs_config()
            except ModuleNotFoundError as error:
                raise RuntimeError(
                    "SQS queue provider selected but optional dependency 'aioboto3' is not installed."
                ) from error

            # Get SQS configuration
            queue_url = config_provider.get("queue.sqs.queue_url", "")
            region = config_provider.get("queue.sqs.region", "us-east-2")
            use_fifo = config_provider.get("queue.sqs.use_fifo", True)
            message_group_id = config_provider.get(
                "queue.sqs.message_group_id", "default"
            )

            # Get AWS credentials from secret manager if configured
            # Note: Credentials will be fetched when needed, not during initialization
            aws_access_key_id = None
            aws_secret_access_key = None
            # TODO: Implement async credential fetching or synchronous secret manager

            sqs_config = sqs_config_cls(
                queue_url=queue_url,
                region=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                use_fifo=use_fifo,
                message_group_id=message_group_id,
            )

            return providers.Singleton(
                sqs_provider_cls,
                config=sqs_config,
            )
        elif provider_type == QueueProvider.RABBITMQ:
            from src.infrastructure.providers.queue.rabbitmq import (
                RabbitMQConfig,
                RabbitMQQueueProvider,
            )

            # Get RabbitMQ configuration
            connection_url = config_provider.get(
                "queue.rabbitmq.connection_url", "amqp://guest:guest@localhost:5672/"
            )
            exchange_name = config_provider.get(
                "queue.rabbitmq.exchange_name", "aperilex"
            )
            queue_name = config_provider.get("queue.rabbitmq.queue_name", "tasks")
            routing_key = config_provider.get("queue.rabbitmq.routing_key", "task")

            rabbitmq_config = RabbitMQConfig(
                connection_url=connection_url,
                exchange_name=exchange_name,
                queue_name=queue_name,
                routing_key=routing_key,
            )

            return providers.Singleton(
                RabbitMQQueueProvider,
                config=rabbitmq_config,
            )
        else:
            raise ValueError(f"Unknown queue provider type: {provider_type}")

    @staticmethod
    def create_worker_provider(
        provider_type: WorkerProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[IWorkerProvider]:
        """
        Create worker provider based on type.

        Args:
            provider_type: Type of worker provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for worker
        """
        if provider_type == WorkerProvider.LAMBDA:
            from src.infrastructure.providers.worker import (
                load_lambda_worker_provider,
            )

            try:
                lambda_worker_cls = load_lambda_worker_provider()
            except ModuleNotFoundError:
                return providers.Singleton(
                    _MissingWorkerProvider,
                    "Lambda worker provider requires the optional 'aioboto3' dependency.",
                )
            from src.shared.config.providers import LambdaWorkerConfig

            # Get Lambda configuration
            function_name = config_provider.get(
                "worker.lambda.function_name", "aperilex-worker"
            )
            region = config_provider.get("worker.lambda.region", "us-east-2")
            qualifier = config_provider.get("worker.lambda.qualifier", "$LATEST")
            timeout_seconds = config_provider.get("worker.lambda.timeout_seconds", 900)
            memory_mb = config_provider.get("worker.lambda.memory_mb", 1024)

            # Get AWS credentials from secret manager if configured
            # Note: Credentials will be fetched when needed, not during initialization
            aws_access_key_id = None
            aws_secret_access_key = None
            # TODO: Implement async credential fetching or synchronous secret manager

            lambda_config = LambdaWorkerConfig(
                function_name=function_name,
                region=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                qualifier=qualifier,
                timeout_seconds=timeout_seconds,
                memory_mb=memory_mb,
            )

            return providers.Singleton(
                lambda_worker_cls,
                config=lambda_config,
            )
        elif provider_type == WorkerProvider.DOCKER:
            from src.infrastructure.providers.worker import (
                load_docker_worker_provider,
            )

            try:
                docker_worker_cls = load_docker_worker_provider()
            except ModuleNotFoundError:
                return providers.Singleton(
                    _MissingWorkerProvider,
                    "Docker worker provider requires the optional 'aiodocker' dependency.",
                )
            from src.shared.config.providers import DockerWorkerConfig

            # Get Docker configuration
            image_name = config_provider.get(
                "worker.docker.image_name", "aperilex-worker:latest"
            )
            container_prefix = config_provider.get(
                "worker.docker.container_prefix", "aperilex-worker"
            )
            network_name = config_provider.get(
                "worker.docker.network_name", "aperilex-network"
            )
            max_concurrent_tasks = config_provider.get(
                "worker.docker.max_concurrent_tasks", 5
            )
            cpu_limit = config_provider.get("worker.docker.cpu_limit", 1.0)
            memory_limit = config_provider.get("worker.docker.memory_limit", 512)

            docker_config = DockerWorkerConfig(
                image_name=image_name,
                container_prefix=container_prefix,
                network_name=network_name,
                max_concurrent_tasks=max_concurrent_tasks,
                cpu_limit=cpu_limit,
                memory_limit=memory_limit,
            )

            return providers.Singleton(
                docker_worker_cls,
                config=docker_config,
            )
        else:
            raise ValueError(f"Unknown worker provider type: {provider_type}")

    @staticmethod
    def create_llm_provider(
        provider_type: LLMProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[ILLMProvider]:
        """
        Create LLM provider based on type.

        Args:
            provider_type: Type of LLM provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for LLM
        """
        if provider_type == LLMProvider.OPENAI:
            from src.infrastructure.providers.llm import OpenAILLMProvider
            from src.shared.config.providers import LLMConfig

            # Get OpenAI configuration
            model_name = config_provider.get("llm.openai.model", "gpt-4o")
            api_key_secret = config_provider.get(
                "llm.openai.api_key_secret", "openai_api_key"
            )
            api_endpoint = config_provider.get(
                "llm.openai.api_endpoint", "https://api.openai.com/v1"
            )
            retry_attempts = config_provider.get("llm.openai.retry_attempts", 3)
            timeout_seconds = config_provider.get("llm.openai.timeout_seconds", 60)
            rate_limit = config_provider.get("llm.openai.rate_limit_per_minute", 60)

            openai_config = LLMConfig(
                schema_version=1,
                provider=LLMProvider.OPENAI,
                model_name=model_name,
                api_key_secret_name=api_key_secret,
                api_endpoint=api_endpoint,
                retry_attempts=retry_attempts,
                timeout_seconds=timeout_seconds,
                rate_limit_per_minute=rate_limit,
            )

            return providers.Singleton(
                OpenAILLMProvider,
                config=openai_config,
                secret_manager=secret_manager,
                base_url=api_endpoint,
            )
        elif provider_type == LLMProvider.GOOGLE:
            from src.infrastructure.providers.llm import GoogleLLMProvider
            from src.shared.config.providers import LLMConfig

            # Get Google configuration
            model_name = config_provider.get("llm.google.model", "gemini-1.5-flash")
            api_key_secret = config_provider.get(
                "llm.google.api_key_secret", "google_api_key"
            )
            retry_attempts = config_provider.get("llm.google.retry_attempts", 3)
            timeout_seconds = config_provider.get("llm.google.timeout_seconds", 60)
            rate_limit = config_provider.get("llm.google.rate_limit_per_minute", 60)

            google_config = LLMConfig(
                schema_version=1,
                provider=LLMProvider.GOOGLE,
                model_name=model_name,
                api_key_secret_name=api_key_secret,
                api_endpoint=None,  # Google doesn't use custom endpoints
                retry_attempts=retry_attempts,
                timeout_seconds=timeout_seconds,
                rate_limit_per_minute=rate_limit,
            )

            return providers.Singleton(
                GoogleLLMProvider,
                config=google_config,
                secret_manager=secret_manager,
            )
        elif provider_type == LLMProvider.BEDROCK:
            # TODO: Implement BedrockLLMProvider
            raise NotImplementedError("Bedrock LLM provider not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

    @staticmethod
    def create_datasource_provider(
        provider_type: DataSourceProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[IDataSourceProvider]:
        """
        Create data source provider based on type.

        Args:
            provider_type: Type of data source provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for data source
        """
        if provider_type == DataSourceProvider.EDGAR:
            from src.infrastructure.providers.datasource import EDGARDataSourceProvider

            # Get EDGAR configuration
            user_agent = config_provider.get(
                "datasource.edgar.user_agent", "Aperilex/1.0 (support@aperilex.com)"
            )
            rate_limit = config_provider.get(
                "datasource.edgar.rate_limit_per_second", 10
            )

            return providers.Singleton(
                EDGARDataSourceProvider,
                user_agent=user_agent,
                rate_limit_per_second=rate_limit,
            )
        else:
            raise ValueError(f"Unknown data source provider type: {provider_type}")

    @staticmethod
    def create_database_provider(
        provider_type: DatabaseProvider,
        config_provider: IConfigProvider,
        secret_manager: ISecretManager,
    ) -> providers.Provider[IDatabaseProvider]:
        """
        Create database provider based on type.

        Args:
            provider_type: Type of database provider
            config_provider: Configuration provider instance
            secret_manager: Secret manager instance

        Returns:
            Provider instance for database
        """
        if provider_type == DatabaseProvider.POSTGRES:
            from src.infrastructure.database.postgres import (
                PostgresConfig,
                PostgresDatabaseProvider,
            )

            # Get PostgreSQL configuration
            host = config_provider.get("database.postgres.host", "localhost")
            port = config_provider.get("database.postgres.port", 5432)
            database = config_provider.get("database.postgres.database", "aperilex")
            username = config_provider.get("database.postgres.username", "postgres")
            password_secret = config_provider.get(
                "database.postgres.password_secret", "postgres_password"
            )
            max_connections = config_provider.get(
                "database.postgres.max_connections", 10
            )
            min_connections = config_provider.get(
                "database.postgres.min_connections", 2
            )
            connection_timeout = config_provider.get(
                "database.postgres.connection_timeout_seconds", 30
            )
            query_timeout = config_provider.get(
                "database.postgres.query_timeout_seconds", 30
            )
            enable_ssl = config_provider.get("database.postgres.enable_ssl", False)
            enable_pooling = config_provider.get(
                "database.postgres.enable_connection_pooling", True
            )

            postgres_config = PostgresConfig(
                host=host,
                port=port,
                database=database,
                username=username,
                password_secret_name=password_secret,
                max_connections=max_connections,
                min_connections=min_connections,
                connection_timeout_seconds=connection_timeout,
                query_timeout_seconds=query_timeout,
                enable_ssl=enable_ssl,
                enable_connection_pooling=enable_pooling,
            )

            return providers.Singleton(
                PostgresDatabaseProvider,
                config=postgres_config,
                secret_manager=secret_manager,
            )
        elif provider_type == DatabaseProvider.AURORA:
            from src.infrastructure.database.aurora import (
                AuroraConfig,
                AuroraDatabaseProvider,
            )

            # Get Aurora configuration
            cluster_endpoint = config_provider.get(
                "database.aurora.cluster_endpoint", ""
            )
            database = config_provider.get("database.aurora.database", "aperilex")
            username = config_provider.get("database.aurora.username", "postgres")
            password_secret = config_provider.get(
                "database.aurora.password_secret", "aurora_password"
            )
            port = config_provider.get("database.aurora.port", 5432)
            region = config_provider.get("database.aurora.region", "us-east-2")
            min_acu = config_provider.get("database.aurora.min_acu", 0)
            max_acu = config_provider.get("database.aurora.max_acu", 16)
            max_connections = config_provider.get("database.aurora.max_connections", 50)
            min_connections = config_provider.get("database.aurora.min_connections", 0)
            connection_timeout = config_provider.get(
                "database.aurora.connection_timeout_seconds", 60
            )
            query_timeout = config_provider.get(
                "database.aurora.query_timeout_seconds", 30
            )
            enable_iam_auth = config_provider.get(
                "database.aurora.enable_iam_auth", False
            )

            aurora_config = AuroraConfig(
                cluster_endpoint=cluster_endpoint,
                database=database,
                username=username,
                password_secret_name=password_secret,
                port=port,
                region=region,
                min_acu=min_acu,
                max_acu=max_acu,
                max_connections=max_connections,
                min_connections=min_connections,
                connection_timeout_seconds=connection_timeout,
                query_timeout_seconds=query_timeout,
                enable_iam_auth=enable_iam_auth,
            )

            return providers.Singleton(
                AuroraDatabaseProvider,
                config=aurora_config,
                secret_manager=secret_manager,
            )
        elif provider_type == DatabaseProvider.COCKROACHDB:
            # TODO: Implement CockroachDBDatabaseProvider
            raise NotImplementedError(
                "CockroachDB database provider not yet implemented"
            )
        else:
            raise ValueError(f"Unknown database provider type: {provider_type}")
