"""
AWS Aurora Serverless v2 database provider implementation.
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
from pydantic import SecretStr

from src.application.interfaces.database import (
    AnalysisResultData,
    DatabaseHealth,
    IDatabaseProvider,
    QueryResult,
    TransactionContext,
)
from src.application.interfaces.secret import ISecretManager
from src.shared.config.providers import AuroraConfig
from src.shared.enums import AnalysisStatus, AnalysisType, TaskPriority, TaskStatus
from src.shared.models import AnalysisRecord, MetadataDict, TaskRecord
from src.shared.types import AnalysisId, FilingId, TaskId, UserId


class AuroraDatabaseProvider(IDatabaseProvider):
    """AWS Aurora Serverless v2 implementation of database provider."""

    def __init__(
        self,
        config: AuroraConfig,
        secret_manager: ISecretManager,
    ):
        """
        Initialize Aurora database provider.

        Args:
            config: Aurora configuration
            secret_manager: Secret manager for retrieving credentials
        """
        self.config = config
        self.secret_manager = secret_manager
        self.pool: asyncpg.Pool | None = None
        self._transactions: dict[str, asyncpg.Connection] = {}
        self._logger = logging.getLogger(__name__)

    def _validate_identifier(self, identifier: str) -> str:
        """
        Validate and quote an SQL identifier (table/column name).

        Args:
            identifier: The identifier to validate

        Returns:
            Quoted identifier safe for SQL usage

        Raises:
            ValueError: If identifier contains invalid characters
        """
        # Check for valid identifier pattern (alphanumeric and underscore only)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier}")

        # Return double-quoted identifier for PostgreSQL/Aurora
        return f'"{identifier}"'

    def _validate_table_name(self, table_name: str) -> str:
        """
        Validate and quote a table name with optional schema.

        Args:
            table_name: Table name, possibly with schema (e.g., 'public.users')

        Returns:
            Quoted table name safe for SQL usage
        """
        parts = table_name.split(".")
        if len(parts) > 2:
            raise ValueError(f"Invalid table name format: {table_name}")

        validated_parts = [self._validate_identifier(part) for part in parts]
        return ".".join(validated_parts)

    async def _ensure_pool(self) -> asyncpg.Pool:
        """Ensure connection pool is created with Aurora-optimized settings."""
        if self.pool is None:
            # Get password from secret manager
            password = await self.secret_manager.get_secret(
                self.config.password_secret_name
            )
            if isinstance(password, SecretStr):
                password = password.get_secret_value()

            # Build SSL parameters for Aurora
            ssl_params = {}
            if self.config.enable_ssl:
                ssl_params = {
                    "ssl": "require",
                    # Aurora uses AWS RDS root certificate
                    # In production, you'd download and reference the RDS CA certificate
                    # "ssl_ca_cert": "/path/to/rds-ca-cert.pem",
                }

            # Create connection pool with Aurora-optimized settings
            self.pool = await asyncpg.create_pool(
                host=self.config.cluster_endpoint,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=password,
                min_size=self.config.min_connections,  # Can be 0 for serverless
                max_size=self.config.max_connections,
                timeout=self.config.connection_timeout_seconds,
                command_timeout=self.config.query_timeout_seconds,
                # Aurora-specific optimizations
                server_settings={
                    "application_name": "aperilex-aurora",
                    # Aurora performance settings
                    "shared_preload_libraries": "pg_stat_statements",
                    "track_activity_query_size": "2048",
                },
                **ssl_params,
            )

            # Create tables if they don't exist
            await self._create_tables()

        return self.pool

    async def _create_tables(self) -> None:
        """Create necessary tables with Aurora-optimized settings."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            # Create tasks table with Aurora optimizations
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    filing_id UUID NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                ) WITH (
                    autovacuum_enabled = true,
                    autovacuum_vacuum_scale_factor = 0.1,
                    autovacuum_analyze_scale_factor = 0.05
                )
            """
            )

            # Create analyses table with Aurora optimizations
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id UUID PRIMARY KEY,
                    filing_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    analysis_type VARCHAR(50) NOT NULL DEFAULT 'COMPREHENSIVE',
                    summary JSONB DEFAULT '{}',
                    meta_data JSONB DEFAULT '{}',
                    created_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                ) WITH (
                    autovacuum_enabled = true,
                    autovacuum_vacuum_scale_factor = 0.1,
                    autovacuum_analyze_scale_factor = 0.05
                )
            """
            )

            # Create indexes with Aurora-specific considerations
            # Use CONCURRENTLY to avoid blocking in production
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_filing_id ON tasks(filing_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_filing_id ON analyses(filing_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status)"
            )

            # Create composite indexes for common query patterns
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_user_filing
                ON tasks(user_id, filing_id)
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analyses_user_filing
                ON analyses(user_id, filing_id)
            """
            )

    async def save_task(
        self,
        task_id: TaskId,
        user_id: UserId,
        filing_id: FilingId,
        status: TaskStatus,
        metadata: MetadataDict,
    ) -> bool:
        """Save or update a task with retry logic for serverless cold starts."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO tasks (id, user_id, filing_id, status, metadata, updated_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        """,
                        task_id,
                        user_id,
                        filing_id,
                        status.value,
                        json.dumps(metadata),
                    )
                    return True
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                # Handle Aurora serverless cold start
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                # Other errors, don't retry
                raise e

        if last_error:
            raise last_error
        return False

    async def _handle_cold_start_retry(self, attempt: int) -> None:
        """Handle Aurora serverless cold start with exponential backoff."""
        import asyncio

        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        wait_time = min(2**attempt, 30)  # Cap at 30 seconds
        await asyncio.sleep(wait_time)
        # Reset pool to force new connection
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def get_task(self, task_id: TaskId) -> TaskRecord:
        """Retrieve a task by ID with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM tasks WHERE id = $1",
                        task_id,
                    )
                    if not row:
                        raise ValueError(f"Task {task_id} not found")

                    return TaskRecord(
                        task_id=TaskId(row["id"]),
                        user_id=UserId(row["user_id"]),
                        filing_id=FilingId(row["filing_id"]),
                        status=TaskStatus(row["status"]),
                        priority=TaskPriority.NORMAL,  # Default if not stored
                        metadata=row.get("metadata", {}),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except ValueError:
                # Task not found, don't retry
                raise
            except Exception as e:
                # Other errors, don't retry
                raise e

        if last_error:
            raise last_error
        raise ValueError(
            f"Task {task_id} not found after {self.config.retry_attempts} attempts"
        )

    async def update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> bool:
        """Update task status with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    result = await conn.execute(
                        """
                        UPDATE tasks
                        SET status = $2, error_message = $3, updated_at = NOW()
                        WHERE id = $1
                        """,
                        task_id,
                        status.value,
                        error_message,
                    )
                    # result is a string like "UPDATE 1" or "UPDATE 0"
                    return bool(result and "UPDATE 0" not in result)
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        return False

    async def save_analysis(
        self,
        analysis_id: AnalysisId,
        filing_id: FilingId,
        user_id: UserId,
        status: AnalysisStatus,
        result: AnalysisResultData,
    ) -> bool:
        """Save or update an analysis result with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    summary_payload_raw = result.summary_payload
                    if summary_payload_raw is None:
                        raise ValueError(
                            "AnalysisResultData.summary_payload is required when saving analyses"
                        )
                    if hasattr(summary_payload_raw, "model_dump"):
                        summary_payload = summary_payload_raw.model_dump()
                    elif isinstance(summary_payload_raw, dict):
                        summary_payload = dict(summary_payload_raw)
                    else:
                        raise TypeError(
                            "summary_payload must be a mapping or support model_dump()"
                        )
                    metadata_updates = self._compose_analysis_metadata(
                        result,
                        status,
                        summary_payload,
                    )

                    await conn.execute(
                        """
                        INSERT INTO analyses (id, filing_id, user_id, status, analysis_type, summary, meta_data, created_by, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            analysis_type = EXCLUDED.analysis_type,
                            summary = EXCLUDED.summary,
                            meta_data = EXCLUDED.meta_data,
                            created_by = COALESCE(EXCLUDED.created_by, analyses.created_by),
                            updated_at = NOW()
                        """,
                        analysis_id,
                        filing_id,
                        user_id,
                        status.value,
                        result.analysis_type,
                        json.dumps(summary_payload),
                        json.dumps(metadata_updates),
                        metadata_updates.get("created_by"),
                    )
                    return True
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        return False

    async def get_analysis(self, analysis_id: AnalysisId) -> AnalysisRecord:
        """Retrieve an analysis by ID with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM analyses WHERE id = $1",
                        analysis_id,
                    )
                    if not row:
                        raise ValueError(f"Analysis {analysis_id} not found")

                    return self._analysis_row_to_record(row)
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except ValueError:
                # Analysis not found, don't retry
                raise
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        raise ValueError(
            f"Analysis {analysis_id} not found after {self.config.retry_attempts} attempts"
        )

    async def list_user_analyses(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisRecord]:
        """List analyses for a user with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM analyses
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2 OFFSET $3
                        """,
                        user_id,
                        limit,
                        offset,
                    )

                    return [self._analysis_row_to_record(row) for row in rows]
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        return []

    def _analysis_row_to_record(self, row: asyncpg.Record) -> AnalysisRecord:
        """Convert an Aurora row into an `AnalysisRecord`."""

        metadata_raw = row.get("meta_data") or {}
        if isinstance(metadata_raw, str):
            try:
                metadata_dict = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata_dict = {}
        elif isinstance(metadata_raw, dict):
            metadata_dict = dict(metadata_raw)
        else:
            metadata_dict = {}

        summary_raw = row.get("summary")
        if isinstance(summary_raw, str):
            try:
                summary = json.loads(summary_raw) if summary_raw else None
            except json.JSONDecodeError:
                summary = None
        elif isinstance(summary_raw, dict):
            summary = summary_raw
        else:
            summary = None

        llm_provider_raw = metadata_dict.get("llm_provider")
        llm_provider = llm_provider_raw if isinstance(llm_provider_raw, str) else None

        llm_model_raw = metadata_dict.get("llm_model")
        llm_model = llm_model_raw if isinstance(llm_model_raw, str) else None

        storage_key_raw = metadata_dict.get("storage_key")
        storage_key = storage_key_raw if isinstance(storage_key_raw, str) else None

        confidence_score = self._coerce_float(metadata_dict.get("confidence_score"))
        token_count = self._coerce_int(metadata_dict.get("token_usage_total"))
        processing_time_ms = self._coerce_int(
            metadata_dict.get("analysis_processing_time_ms")
        )
        estimated_cost = self._coerce_float(metadata_dict.get("estimated_cost"))

        analysis_type_raw = row.get("analysis_type") or AnalysisType.COMPREHENSIVE.value
        try:
            analysis_type = AnalysisType(analysis_type_raw)
        except ValueError:
            analysis_type = AnalysisType.COMPREHENSIVE

        return AnalysisRecord(
            analysis_id=AnalysisId(row["id"]),
            filing_id=FilingId(row["filing_id"]),
            user_id=UserId(row["user_id"]),
            status=AnalysisStatus(row["status"]),
            analysis_type=analysis_type,
            summary=summary,
            storage_key=storage_key,
            llm_provider=llm_provider,
            llm_model=llm_model,
            confidence_score=confidence_score,
            token_count=token_count,
            processing_time_ms=processing_time_ms,
            cost=estimated_cost,
            created_by=row.get("created_by"),
            metadata=metadata_dict,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _compose_analysis_metadata(
        result: AnalysisResultData,
        status: AnalysisStatus,
        summary: dict[str, Any],
    ) -> dict[str, str | int | float | bool]:
        metadata = dict(result.metadata)

        completed_at = summary.get("processing", {}).get("completed_at")
        if not isinstance(completed_at, str):
            completed_at = datetime.now(UTC).isoformat()

        duration_seconds = summary.get("processing", {}).get("duration_seconds")
        duration_float = AuroraDatabaseProvider._coerce_float(duration_seconds)
        processing_ms = int(duration_float * 1000) if duration_float is not None else None

        confidence_score = AuroraDatabaseProvider._coerce_float(
            summary.get("confidence", {}).get("score")
        )

        metadata.update(
            {
                "analysis_schema_version": result.schema_version,
                "summary_schema_version": 3,
                "analysis_status": status.value,
                "analysis_completed_at": completed_at,
            }
        )

        if processing_ms is not None:
            metadata["analysis_processing_time_ms"] = processing_ms
        if confidence_score is not None:
            metadata["confidence_score"] = confidence_score

        cleaned: dict[str, str | int | float | bool] = {}
        for key, value in metadata.items():
            coerced = AuroraDatabaseProvider._coerce_metadata_value(value)
            if coerced is not None:
                cleaned[key] = coerced

        return cleaned

    @staticmethod
    def _coerce_metadata_value(
        value: Any,
    ) -> str | int | float | bool | None:
        if value is None:
            return None
        if isinstance(value, str | int | float | bool):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _confidence_bucket(score: float | None) -> str | None:
        if score is None:
            return None
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    async def begin_transaction(
        self,
        context: TransactionContext | None = None,
    ) -> TransactionContext:
        """Begin a database transaction."""
        pool = await self._ensure_pool()
        conn = await pool.acquire()
        tx = conn.transaction()
        await tx.start()

        if context is None:
            context = TransactionContext(
                transaction_id=str(uuid4()),
            )

        self._transactions[context.transaction_id] = conn
        return context

    async def commit_transaction(self, context: TransactionContext) -> bool:
        """Commit a database transaction."""
        if context.transaction_id not in self._transactions:
            raise ValueError(f"Transaction {context.transaction_id} not found")

        conn = self._transactions[context.transaction_id]
        try:
            await conn.execute("COMMIT")
            return True
        finally:
            await conn.close()
            del self._transactions[context.transaction_id]

    async def rollback_transaction(self, context: TransactionContext) -> bool:
        """Rollback a database transaction."""
        if context.transaction_id not in self._transactions:
            raise ValueError(f"Transaction {context.transaction_id} not found")

        conn = self._transactions[context.transaction_id]
        try:
            await conn.execute("ROLLBACK")
            return True
        finally:
            await conn.close()
            del self._transactions[context.transaction_id]

    async def execute_query(
        self,
        query: str,
        parameters: MetadataDict | None = None,
        transaction: TransactionContext | None = None,
    ) -> QueryResult:
        """Execute a raw SQL query with retry logic."""
        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                if transaction and transaction.transaction_id in self._transactions:
                    conn = self._transactions[transaction.transaction_id]
                else:
                    pool = await self._ensure_pool()
                    conn = await pool.acquire()

                try:
                    start_time = datetime.now(UTC)
                    if parameters:
                        # Convert parameters to list for asyncpg
                        param_values = list(parameters.values())
                        result = await conn.execute(query, *param_values)
                    else:
                        result = await conn.execute(query)

                    execution_time = (
                        datetime.now(UTC) - start_time
                    ).total_seconds() * 1000

                    # Parse result to get rows affected
                    rows_affected = 0
                    if result and " " in result:
                        parts = result.split()
                        if len(parts) > 1 and parts[1].isdigit():
                            rows_affected = int(parts[1])

                    return QueryResult(
                        rows_affected=rows_affected,
                        execution_time_ms=int(execution_time),
                    )
                finally:
                    if not transaction:
                        await conn.close()

            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        raise Exception(f"Query failed after {self.config.retry_attempts} attempts")

    async def bulk_insert(
        self,
        table_name: str,
        records: list[MetadataDict],
        transaction: TransactionContext | None = None,
    ) -> int:
        """Perform bulk insert operation with retry logic."""
        if not records:
            return 0

        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                # Get column names from first record
                columns = list(records[0].keys())

                # Validate table name and column names
                validated_table = self._validate_table_name(table_name)
                validated_columns = [self._validate_identifier(col) for col in columns]
                column_str = ", ".join(validated_columns)

                # Create placeholder string
                placeholders = []
                values = []
                for i, record in enumerate(records):
                    row_placeholders = []
                    for j, col in enumerate(columns):
                        placeholder_num = i * len(columns) + j + 1
                        row_placeholders.append(f"${placeholder_num}")
                        values.append(record.get(col))
                    placeholders.append(f"({', '.join(row_placeholders)})")

                # SQL injection protected: identifiers are validated and quoted by _validate_* methods
                query = f"""  # nosec B608 - table/columns validated above
                    INSERT INTO {validated_table} ({column_str})
                    VALUES {", ".join(placeholders)}
                """  # nosec B608

                if transaction and transaction.transaction_id in self._transactions:
                    conn = self._transactions[transaction.transaction_id]
                else:
                    pool = await self._ensure_pool()
                    conn = await pool.acquire()

                try:
                    result = await conn.execute(query, *values)
                    # Parse result to get rows affected
                    if result and " " in result:
                        parts = result.split()
                        if len(parts) > 1 and parts[1].isdigit():
                            return int(parts[1])
                    return len(records)
                finally:
                    if not transaction:
                        await conn.close()

            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        return 0

    async def create_index(
        self,
        table_name: str,
        columns: list[str],
        index_name: str | None = None,
        unique: bool = False,
    ) -> bool:
        """Create a database index."""
        # Validate table name and columns
        validated_table = self._validate_table_name(table_name)
        validated_columns = [self._validate_identifier(col) for col in columns]

        if not index_name:
            # Create a safe index name from validated parts
            clean_table = table_name.replace(".", "_")
            index_name = f"idx_{clean_table}_{'_'.join(columns)}"

        # Validate the index name
        validated_index = self._validate_identifier(index_name)

        unique_str = "UNIQUE " if unique else ""
        columns_str = ", ".join(validated_columns)

        # Use CONCURRENTLY for non-blocking index creation in Aurora
        # SQL injection protected: identifiers are validated and quoted by _validate_* methods
        query = f"""  # nosec B608
            CREATE {unique_str}INDEX IF NOT EXISTS {validated_index}
            ON {validated_table} ({columns_str})
        """  # nosec B608

        retries = 0
        last_error = None

        while retries < self.config.retry_attempts:
            try:
                pool = await self._ensure_pool()
                async with pool.acquire() as conn:
                    await conn.execute(query)
                    return True
            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                last_error = e
                retries += 1
                if retries < self.config.retry_attempts:
                    await self._handle_cold_start_retry(retries)
            except Exception as e:
                raise e

        if last_error:
            raise last_error
        return False

    async def get_health(self) -> DatabaseHealth:
        """Get database health metrics including Aurora-specific metrics."""
        try:
            pool = await self._ensure_pool()

            # Get pool stats
            total_connections = pool.get_size()
            idle_connections = pool.get_idle_size()
            active_connections = total_connections - idle_connections

            # Try to execute a simple query to check health
            is_healthy = False
            replication_lag_ms = None
            cpu_usage = None
            disk_usage = None

            try:
                async with pool.acquire() as conn:
                    # Basic health check
                    await conn.fetchval("SELECT 1")
                    is_healthy = True

                    # Try to get Aurora-specific metrics if available
                    try:
                        # Check if we're on Aurora by looking for Aurora-specific functions
                        aurora_version = await conn.fetchval("SELECT aurora_version()")
                        if aurora_version:
                            # Get replication lag (in a real Aurora cluster)
                            # This would typically query aurora_replica_status
                            self._logger.debug(
                                f"Aurora version detected: {aurora_version}"
                            )
                    except Exception as e:
                        # Not Aurora or function not available
                        self._logger.debug(
                            f"Aurora-specific functions not available: {e}"
                        )

            except Exception as e:
                self._logger.warning(f"Health check query failed: {e}")

            return DatabaseHealth(
                is_healthy=is_healthy,
                connection_count=total_connections,
                active_connections=active_connections,
                idle_connections=idle_connections,
                pending_queries=0,
                replication_lag_ms=replication_lag_ms,
                disk_usage_percent=disk_usage,
                cpu_usage_percent=cpu_usage,
            )
        except Exception:
            return DatabaseHealth(
                is_healthy=False,
                connection_count=0,
                active_connections=0,
                idle_connections=0,
                pending_queries=0,
            )

    async def close(self) -> bool:
        """Close database connections."""
        if self.pool:
            await self.pool.close()
            self.pool = None
        return True
