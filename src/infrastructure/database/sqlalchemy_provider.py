"""
Base SQLAlchemy database provider implementation.

This module provides a unified SQLAlchemy-based database provider that implements
the IDatabaseProvider protocol and manages repository access.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.interfaces.database import (
    AnalysisResultData,
    DatabaseHealth,
    IDatabaseProvider,
    QueryResult,
    TransactionContext,
)
from src.application.interfaces.repositories import IRepositoryFactory
from src.infrastructure.database.cache import CacheManager
from src.shared.enums import AnalysisStatus, AnalysisType, TaskPriority, TaskStatus
from src.shared.models import AnalysisRecord, MetadataDict, TaskRecord
from src.shared.types import AnalysisId, FilingId, TaskId, UserId

logger = logging.getLogger(__name__)


class SQLAlchemyDatabaseProvider(IDatabaseProvider):
    """Base SQLAlchemy database provider implementation."""

    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        cache_manager: CacheManager | None = None,
    ) -> None:
        """
        Initialize SQLAlchemy database provider.

        Args:
            engine: AsyncEngine instance for database connections
            session_factory: Factory for creating async sessions
            cache_manager: Optional cache manager for query caching
        """
        self._engine = engine
        self._session_factory = session_factory
        self._cache_manager = cache_manager
        self._repository_factory: IRepositoryFactory | None = None
        self._active_transaction: TransactionContext | None = None
        self._active_session: AsyncSession | None = None
        logger.info("Initialized SQLAlchemyDatabaseProvider")

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

        # Return double-quoted identifier for PostgreSQL/MySQL
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

    def get_repository_factory(self) -> IRepositoryFactory:
        """
        Get the repository factory for creating repository instances.

        Returns:
            Repository factory instance

        Raises:
            RuntimeError: If factory cannot be created
        """
        if self._repository_factory is None:
            # Import here to avoid circular dependencies
            from .repository_factory import RepositoryFactory

            self._repository_factory = RepositoryFactory(
                session_factory=self._session_factory,
                cache_manager=self._cache_manager,
            )
        return self._repository_factory

    async def save_task(
        self,
        task_id: TaskId,
        user_id: UserId,
        filing_id: FilingId,
        status: TaskStatus,
        metadata: MetadataDict,
    ) -> bool:
        """
        Save or update a task in the database.

        Args:
            task_id: Unique task identifier
            user_id: User who created the task
            filing_id: Associated filing ID
            status: Current task status
            metadata: Task metadata

        Returns:
            True if saved successfully
        """
        async with self._session_factory() as session:
            try:
                # Import here to avoid circular dependencies
                from .models.task import Task

                # Check if task exists
                existing = await session.get(Task, task_id)

                if existing:
                    # Update existing task
                    existing.user_id = user_id
                    existing.filing_id = filing_id
                    existing.status = status.value
                    existing.task_metadata = metadata
                else:
                    # Create new task
                    task = Task(
                        id=task_id,
                        user_id=user_id,
                        filing_id=filing_id,
                        status=status.value,
                        metadata=metadata,
                    )
                    session.add(task)

                await session.commit()
                logger.debug(f"Saved task {task_id} with status {status}")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save task {task_id}: {e}")
                raise

    async def get_task(self, task_id: TaskId) -> TaskRecord:
        """
        Retrieve a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task record with all task data
        """
        async with self._session_factory() as session:
            from .models.task import Task

            task = await session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            return TaskRecord(
                task_id=TaskId(task.id),
                user_id=UserId(task.user_id),
                filing_id=FilingId(task.filing_id),
                status=TaskStatus(task.status),
                priority=TaskPriority.NORMAL,  # Default if not stored
                metadata=task.task_metadata or {},
                created_at=task.created_at,
                updated_at=task.updated_at,
            )

    async def update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> bool:
        """
        Update task status.

        Args:
            task_id: Task identifier
            status: New status
            error_message: Optional error message

        Returns:
            True if updated successfully
        """
        async with self._session_factory() as session:
            from .models.task import Task

            task = await session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = status.value
            if error_message:
                if task.task_metadata is None:
                    task.task_metadata = {}
                task.task_metadata["error_message"] = error_message

            await session.commit()
            logger.debug(f"Updated task {task_id} status to {status}")
            return True

    async def save_analysis(
        self,
        analysis_id: AnalysisId,
        filing_id: FilingId,
        user_id: UserId,
        status: AnalysisStatus,
        result: AnalysisResultData,
    ) -> bool:
        """
        Save or update an analysis result.

        Args:
            analysis_id: Unique analysis identifier
            filing_id: Associated filing ID
            user_id: User who requested analysis
            status: Current analysis status
            result: Analysis result data

        Returns:
            True if saved successfully
        """
        async with self._session_factory() as session:
            try:
                from .models.analysis import Analysis

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

                existing = await session.get(Analysis, analysis_id)

                if existing:
                    existing.filing_id = filing_id
                    existing.user_id = user_id
                    existing.status = status.value
                    existing.analysis_type = result.analysis_type
                    existing.summary = summary_payload
                    existing.meta_data = metadata_updates
                    if metadata_updates.get("created_by"):
                        existing.created_by = str(metadata_updates.get("created_by"))
                else:
                    analysis = Analysis(
                        id=analysis_id,
                        filing_id=filing_id,
                        user_id=user_id,
                        status=status.value,
                        analysis_type=result.analysis_type,
                        summary=summary_payload,
                        meta_data=metadata_updates,
                        created_by=(
                            str(metadata_updates.get("created_by"))
                            if metadata_updates.get("created_by")
                            else str(user_id)
                        ),
                    )
                    session.add(analysis)

                await session.commit()
                logger.debug(f"Saved analysis {analysis_id} with status {status}")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save analysis {analysis_id}: {e}")
                raise

    async def get_analysis(self, analysis_id: AnalysisId) -> AnalysisRecord:
        """
        Retrieve an analysis by ID.

        Args:
            analysis_id: Analysis identifier

        Returns:
            Analysis record with all analysis data
        """
        async with self._session_factory() as session:
            from .models.analysis import Analysis

            analysis = await session.get(Analysis, analysis_id)
            if not analysis:
                raise ValueError(f"Analysis {analysis_id} not found")

            return self._analysis_model_to_record(analysis)

    async def list_user_analyses(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisRecord]:
        """
        List analyses for a user.

        Args:
            user_id: User identifier
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of analysis records
        """
        async with self._session_factory() as session:
            from sqlalchemy import select

            from .models.analysis import Analysis

            stmt = (
                select(Analysis)
                .where(Analysis.user_id == user_id)
                .order_by(Analysis.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)
            analyses = result.scalars().all()

            return [self._analysis_model_to_record(analysis) for analysis in analyses]

    def _analysis_model_to_record(self, analysis: Any) -> AnalysisRecord:
        """Convert a SQLAlchemy Analysis model into an `AnalysisRecord`."""

        metadata_raw = getattr(analysis, "meta_data", {})
        metadata_dict = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}

        summary_raw = getattr(analysis, "summary", None)
        summary = summary_raw if isinstance(summary_raw, dict) else None

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

        record_metadata = metadata_dict

        return AnalysisRecord(
            analysis_id=AnalysisId(analysis.id),
            filing_id=FilingId(analysis.filing_id),
            user_id=UserId(analysis.user_id),
            status=AnalysisStatus(analysis.status),
            analysis_type=AnalysisType(analysis.analysis_type),
            summary=summary,
            storage_key=storage_key,
            llm_provider=llm_provider,
            llm_model=llm_model,
            confidence_score=confidence_score,
            token_count=token_count,
            processing_time_ms=processing_time_ms,
            cost=estimated_cost,
            created_by=getattr(analysis, "created_by", None),
            metadata=record_metadata,
            created_at=analysis.created_at,
            updated_at=analysis.created_at,
        )

    @staticmethod
    def _compose_analysis_metadata(
        result: AnalysisResultData,
        status: AnalysisStatus,
        summary: dict[str, Any],
    ) -> dict[str, str | int | float | bool]:
        """Prepare metadata dictionary aligned with summary persistence."""

        metadata = dict(result.metadata)

        completed_at = summary.get("processing", {}).get("completed_at")
        if not isinstance(completed_at, str):
            completed_at = datetime.now(UTC).isoformat()

        duration_seconds = summary.get("processing", {}).get("duration_seconds")
        duration_float = SQLAlchemyDatabaseProvider._coerce_float(duration_seconds)
        processing_ms = (
            int(duration_float * 1000) if duration_float is not None else None
        )

        confidence_score = SQLAlchemyDatabaseProvider._coerce_float(
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
            coerced = SQLAlchemyDatabaseProvider._coerce_metadata_value(value)
            if coerced is not None:
                cleaned[key] = coerced

        return cleaned

    @staticmethod
    def _coerce_metadata_value(
        value: Any,
    ) -> str | int | float | bool | None:
        """Normalize metadata values to primitives accepted by the schema."""

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
        """
        Begin a database transaction.

        Args:
            context: Optional transaction context

        Returns:
            Transaction context
        """
        if self._active_transaction:
            raise RuntimeError("Transaction already in progress")

        import uuid

        if context is None:
            context = TransactionContext(
                transaction_id=str(uuid.uuid4()),
            )

        self._active_session = self._session_factory()
        await self._active_session.__aenter__()
        self._active_transaction = context

        logger.debug(f"Started transaction {context.transaction_id}")
        return context

    async def commit_transaction(self, context: TransactionContext) -> bool:
        """
        Commit a database transaction.

        Args:
            context: Transaction context

        Returns:
            True if committed successfully
        """
        if (
            not self._active_transaction
            or self._active_transaction.transaction_id != context.transaction_id
        ):
            raise RuntimeError(f"Invalid transaction context: {context.transaction_id}")

        if not self._active_session:
            raise RuntimeError("No active session for transaction")

        try:
            await self._active_session.commit()
            logger.debug(f"Committed transaction {context.transaction_id}")
            return True
        finally:
            await self._active_session.__aexit__(None, None, None)
            self._active_session = None
            self._active_transaction = None

    async def rollback_transaction(self, context: TransactionContext) -> bool:
        """
        Rollback a database transaction.

        Args:
            context: Transaction context

        Returns:
            True if rolled back successfully
        """
        if (
            not self._active_transaction
            or self._active_transaction.transaction_id != context.transaction_id
        ):
            raise RuntimeError(f"Invalid transaction context: {context.transaction_id}")

        if not self._active_session:
            raise RuntimeError("No active session for transaction")

        try:
            await self._active_session.rollback()
            logger.debug(f"Rolled back transaction {context.transaction_id}")
            return True
        finally:
            await self._active_session.__aexit__(None, None, None)
            self._active_session = None
            self._active_transaction = None

    async def execute_query(
        self,
        query: str,
        parameters: MetadataDict | None = None,
        transaction: TransactionContext | None = None,
    ) -> QueryResult:
        """
        Execute a raw SQL query.

        Args:
            query: SQL query string
            parameters: Query parameters
            transaction: Optional transaction context

        Returns:
            Query execution result
        """
        import time

        from sqlalchemy import text

        start_time = time.time()

        # Use active session if in transaction, otherwise create new one
        if transaction and self._active_session:
            session = self._active_session
            should_close = False
        else:
            session = self._session_factory()
            await session.__aenter__()
            should_close = True

        try:
            result = await session.execute(text(query), parameters or {})
            rows_affected = result.rowcount if hasattr(result, "rowcount") else 0

            if not transaction:
                await session.commit()

            execution_time_ms = int((time.time() - start_time) * 1000)

            return QueryResult(
                rows_affected=rows_affected,
                execution_time_ms=execution_time_ms,
            )
        finally:
            if should_close:
                await session.__aexit__(None, None, None)

    async def bulk_insert(
        self,
        table_name: str,
        records: list[MetadataDict],
        transaction: TransactionContext | None = None,
    ) -> int:
        """
        Perform bulk insert operation.

        Args:
            table_name: Target table name
            records: List of records to insert
            transaction: Optional transaction context

        Returns:
            Number of records inserted
        """
        if not records:
            return 0

        from sqlalchemy import text

        # Use active session if in transaction, otherwise create new one
        if transaction and self._active_session:
            session = self._active_session
            should_close = False
        else:
            session = self._session_factory()
            await session.__aenter__()
            should_close = True

        try:
            # Build insert statement
            columns = list(records[0].keys())

            # Validate table name and column names
            validated_table = self._validate_table_name(table_name)
            validated_columns = [self._validate_identifier(col) for col in columns]
            columns_str = ", ".join(validated_columns)

            # Create placeholders for values (these are safe as they use named parameters)
            placeholders = ", ".join([f":{col}" for col in columns])

            # SQL injection protected: identifiers are validated and quoted by _validate_* methods
            insert_stmt = text(  # nosec B608
                f"INSERT INTO {validated_table} ({columns_str}) VALUES ({placeholders})"  # nosec B608
            )

            # Execute bulk insert
            for record in records:
                await session.execute(insert_stmt, record)

            if not transaction:
                await session.commit()

            logger.debug(f"Bulk inserted {len(records)} records into {table_name}")
            return len(records)
        finally:
            if should_close:
                await session.__aexit__(None, None, None)

    async def create_index(
        self,
        table_name: str,
        columns: list[str],
        index_name: str | None = None,
        unique: bool = False,
    ) -> bool:
        """
        Create a database index.

        Args:
            table_name: Table to index
            columns: Columns to include in index
            index_name: Optional index name
            unique: Whether index should be unique

        Returns:
            True if index created successfully
        """
        from sqlalchemy import text

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

        # SQL injection protected: identifiers are validated and quoted by _validate_* methods
        create_index_stmt = text(  # nosec B608
            f"CREATE {unique_str}INDEX IF NOT EXISTS {validated_index} "  # nosec B608
            f"ON {validated_table} ({columns_str})"  # nosec B608
        )

        async with self._session_factory() as session:
            await session.execute(create_index_stmt)
            await session.commit()
            logger.info(f"Created index {index_name} on {table_name}")
            return True

    async def get_health(self) -> DatabaseHealth:
        """
        Get database health metrics.

        Returns:
            Database health status
        """
        from sqlalchemy import text

        try:
            async with self._session_factory() as session:
                # Simple health check query
                result = await session.execute(text("SELECT 1"))
                result.scalar()

                # Get connection pool stats
                pool = self._engine.pool

                return DatabaseHealth(
                    is_healthy=True,
                    connection_count=pool.size() if hasattr(pool, "size") else 0,
                    active_connections=(
                        pool.checked_in_connections()
                        if hasattr(pool, "checked_in_connections")
                        else 0
                    ),
                    idle_connections=(
                        pool.checked_out_connections()
                        if hasattr(pool, "checked_out_connections")
                        else 0
                    ),
                    pending_queries=0,  # Not easily available in SQLAlchemy
                )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return DatabaseHealth(
                is_healthy=False,
                connection_count=0,
                active_connections=0,
                idle_connections=0,
                pending_queries=0,
            )

    async def close(self) -> bool:
        """
        Close database connections.

        Returns:
            True if closed successfully
        """
        try:
            await self._engine.dispose()
            logger.info("Closed database connections")
            return True
        except Exception as e:
            logger.error(f"Failed to close database connections: {e}")
            return False
