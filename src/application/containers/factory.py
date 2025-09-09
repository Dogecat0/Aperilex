"""
Factory for creating provider implementations based on configuration.
"""

from dependency_injector import providers

from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.database import IDatabaseProvider
from src.application.interfaces.datasource import IDataSourceProvider
from src.application.interfaces.llm import ILLMProvider
from src.application.interfaces.queue import IQueueProvider
from src.application.interfaces.secret import ISecretManager
from src.application.interfaces.storage import IStorageProvider
from src.application.interfaces.worker import IWorkerProvider
from src.infrastructure.config import EnvironmentConfigProvider
from src.infrastructure.providers.storage import LocalStorageProvider, S3StorageProvider
from src.infrastructure.secret import LocalSecretManager
from src.shared.enums import (
    DatabaseProvider,
    DataSourceProvider,
    LLMProvider,
    QueueProvider,
    StorageProvider,
    WorkerProvider,
)


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
        if environment in ["development", "test"]:
            return providers.Singleton(
                EnvironmentConfigProvider,
                prefix="APERILEX",
            )
        else:
            # Production environments would use AWS Parameter Store or similar
            # For now, fall back to environment config
            return providers.Singleton(
                EnvironmentConfigProvider,
                prefix="APERILEX",
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
            # TODO: Implement async credential fetching or synchronous secret manager

            return providers.Singleton(
                S3StorageProvider,
                bucket_name=bucket_name,
                region=region,
                prefix=prefix,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        elif provider_type == StorageProvider.LOCAL:
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
            from src.infrastructure.providers.queue.sqs import (
                SQSConfig,
                SQSQueueProvider,
            )

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

            sqs_config = SQSConfig(
                queue_url=queue_url,
                region=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                use_fifo=use_fifo,
                message_group_id=message_group_id,
            )

            return providers.Singleton(
                SQSQueueProvider,
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
                LambdaWorkerConfig,
                LambdaWorkerProvider,
            )

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
                LambdaWorkerProvider,
                config=lambda_config,
            )
        elif provider_type == WorkerProvider.DOCKER:
            from src.infrastructure.providers.worker import (
                DockerWorkerConfig,
                DockerWorkerProvider,
            )

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
                DockerWorkerProvider,
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
            from src.application.interfaces.llm import LLMConfig
            from src.infrastructure.providers.llm import OpenAILLMProvider

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
            from src.application.interfaces.llm import LLMConfig
            from src.infrastructure.providers.llm import GoogleLLMProvider

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
            max_connections = config_provider.get(
                "database.aurora.max_connections", 50
            )
            min_connections = config_provider.get(
                "database.aurora.min_connections", 0
            )
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
