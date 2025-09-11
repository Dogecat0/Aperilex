"""
Database provider interface for abstracted database operations.
"""

from abc import abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from src.shared.enums import AnalysisStatus, TaskStatus
from src.shared.models import (
    AnalysisRecord,
    MetadataDict,
    TaskRecord,
)
from src.shared.types import AnalysisId, FilingId, TaskId, UserId

from .repositories import IRepositoryFactory

T = TypeVar("T", bound=BaseModel)


class AnalysisResultData(BaseModel):
    """Analysis result data structure."""

    schema_version: int = 1
    analysis_type: str
    summary: str
    insights: list[str] = []
    metrics: dict[str, float] = {}
    metadata: MetadataDict = {}


class TransactionContext(BaseModel):
    """Context for database transactions."""

    schema_version: int = 1
    transaction_id: str
    isolation_level: str = "READ_COMMITTED"
    read_only: bool = False
    timeout_seconds: int = 30


class QueryResult(BaseModel):
    """Result from a database query."""

    schema_version: int = 1
    rows_affected: int
    execution_time_ms: int
    has_more_results: bool = False
    cursor: str | None = None


class DatabaseHealth(BaseModel):
    """Database health status."""

    schema_version: int = 1
    is_healthy: bool
    connection_count: int
    active_connections: int
    idle_connections: int
    pending_queries: int
    replication_lag_ms: int | None = None
    disk_usage_percent: float | None = None
    cpu_usage_percent: float | None = None


@runtime_checkable
class IDatabaseProvider(Protocol):
    """Protocol for database provider implementations."""

    @abstractmethod
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

        Raises:
            DatabaseError: If save operation fails
            ValidationError: If data is invalid
        """
        ...

    @abstractmethod
    async def get_task(self, task_id: TaskId) -> TaskRecord:
        """
        Retrieve a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task record with all task data

        Raises:
            NotFoundError: If task not found
            DatabaseError: If retrieval fails
        """
        ...

    @abstractmethod
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

        Raises:
            NotFoundError: If task not found
            DatabaseError: If update fails
        """
        ...

    @abstractmethod
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

        Raises:
            DatabaseError: If save operation fails
            ValidationError: If data is invalid
        """
        ...

    @abstractmethod
    async def get_analysis(self, analysis_id: AnalysisId) -> AnalysisRecord:
        """
        Retrieve an analysis by ID.

        Args:
            analysis_id: Analysis identifier

        Returns:
            Analysis record with all analysis data

        Raises:
            NotFoundError: If analysis not found
            DatabaseError: If retrieval fails
        """
        ...

    @abstractmethod
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
            List of analysis data dictionaries

        Raises:
            DatabaseError: If query fails
        """
        ...

    @abstractmethod
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

        Raises:
            DatabaseError: If transaction cannot be started
        """
        ...

    @abstractmethod
    async def commit_transaction(self, context: TransactionContext) -> bool:
        """
        Commit a database transaction.

        Args:
            context: Transaction context

        Returns:
            True if committed successfully

        Raises:
            DatabaseError: If commit fails
            TransactionError: If transaction invalid
        """
        ...

    @abstractmethod
    async def rollback_transaction(self, context: TransactionContext) -> bool:
        """
        Rollback a database transaction.

        Args:
            context: Transaction context

        Returns:
            True if rolled back successfully

        Raises:
            DatabaseError: If rollback fails
            TransactionError: If transaction invalid
        """
        ...

    @abstractmethod
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

        Raises:
            DatabaseError: If query fails
            ValidationError: If query is invalid
        """
        ...

    @abstractmethod
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

        Raises:
            DatabaseError: If bulk insert fails
            ValidationError: If data is invalid
        """
        ...

    @abstractmethod
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

        Raises:
            DatabaseError: If index creation fails
            AlreadyExistsError: If index already exists
        """
        ...

    @abstractmethod
    def get_repository_factory(self) -> IRepositoryFactory:
        """
        Get the repository factory for creating repository instances.

        Returns:
            Repository factory instance

        Raises:
            DatabaseError: If factory cannot be created
        """
        ...

    @abstractmethod
    async def get_health(self) -> DatabaseHealth:
        """
        Get database health metrics.

        Returns:
            Database health status

        Raises:
            DatabaseError: If health check fails
        """
        ...

    @abstractmethod
    async def close(self) -> bool:
        """
        Close database connections.

        Returns:
            True if closed successfully

        Raises:
            DatabaseError: If close operation fails
        """
        ...
