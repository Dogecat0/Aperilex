"""
Task preparation utilities extracted from the monolithic WorkerService.

The builder converts an incoming `AnalyzeFilingCommand` plus optional context
into a fully populated `TaskData` instance. The implementation is a direct
lift from `WorkerService.prepare_analysis_task_data` so behaviour remains
unchanged while enabling unit-level coverage in isolation.
"""

from __future__ import annotations

import uuid
from typing import Final

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.interfaces.repositories import CompanyData, FilingData
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.types import Email, FilingId, TaskId, Ticker, UserId


class AnalysisTaskBuilder:
    """Construct `TaskData` instances for worker processing."""

    DEFAULT_PRIORITY: Final[TaskPriority] = TaskPriority.NORMAL
    DEFAULT_TIER: Final[UserTier] = UserTier.BASIC
    DEFAULT_FILING_TYPE: Final[FilingType] = FilingType.FORM_10K

    def build_task_data(
        self,
        command: AnalyzeFilingCommand,
        *,
        company: CompanyData | None = None,
        filing: FilingData | None = None,
        user_email: Email | None = None,
        user_id: UserId | None = None,
        user_tier: UserTier | None = None,
        priority: TaskPriority | None = None,
        source: str | None = "API",
        correlation_id: str | None = None,
        parent_task_id: TaskId | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TaskData:
        """
        Build `TaskData` for the worker pipeline.

        The logic mirrors the existing WorkerService implementation so we can
        migrate call sites incrementally in later phases.
        """

        resolved_user_id = self._resolve_user_id(command, user_id)
        resolved_email = self._resolve_user_email(resolved_user_id, user_email)
        ticker = self._resolve_ticker(command, company)
        filing_type = filing.filing_type if filing else self.DEFAULT_FILING_TYPE

        task_id = TaskId(uuid.uuid4())
        target_filing_id = filing.id if filing else FilingId(uuid.uuid4())
        task_correlation_id = correlation_id or str(uuid.uuid4())

        task_user_tier = user_tier or self.DEFAULT_TIER

        metadata = self._build_task_metadata(
            command=command,
            email=resolved_email,
            company=company,
            filing=filing,
            filing_id=target_filing_id,
        )
        metadata["user_tier"] = task_user_tier.value

        template_key = command.analysis_template.value
        task_priority = priority or self.DEFAULT_PRIORITY

        return TaskData(
            task_id=task_id,
            filing_id=target_filing_id,
            user_id=resolved_user_id,
            email=resolved_email,
            user_tier=task_user_tier,
            ticker=ticker,
            filing_type=filing_type,
            priority=task_priority,
            status=TaskStatus.PENDING,
            metadata=metadata,
            deduplication_id=f"{target_filing_id}:{template_key}:{resolved_email.value}",
            correlation_id=task_correlation_id,
            source=source,
            parent_task_id=parent_task_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    def _resolve_user_id(
        self,
        command: AnalyzeFilingCommand,
        explicit_user_id: UserId | None,
    ) -> UserId:
        if explicit_user_id is not None:
            return explicit_user_id

        if command.user_id:
            try:
                return UserId(uuid.UUID(command.user_id))
            except ValueError:
                # Fall back to a generated identifier while logging is handled upstream.
                pass

        return UserId(uuid.uuid4())

    def _resolve_user_email(
        self,
        user_id: UserId,
        explicit_email: Email | None,
    ) -> Email:
        if explicit_email is None:
            raise ValueError(f"Authenticated user email is required for {user_id}")
        return explicit_email

    def _resolve_ticker(
        self,
        command: AnalyzeFilingCommand,
        company: CompanyData | None,
    ) -> Ticker:
        if company and company.ticker is not None:
            return company.ticker

        fallback = "00001"
        if command.company_cik is not None:
            cik_value = str(command.company_cik.value).strip()
            if cik_value:
                fallback = cik_value[:5].upper()

        return Ticker(value=fallback)

    def _build_task_metadata(
        self,
        *,
        command: AnalyzeFilingCommand,
        email: Email,
        company: CompanyData | None,
        filing: FilingData | None,
        filing_id: FilingId,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {
            "analysis_template": command.analysis_template.value,
            "force_reprocess": str(command.force_reprocess),
            "requested_by": email.value,
            "filing_id": str(filing_id),
        }

        if command.company_cik is not None:
            cik_value = str(command.company_cik)
            metadata["company_cik"] = cik_value
            metadata["cik"] = cik_value

        if command.accession_number is not None:
            metadata["accession_number"] = str(command.accession_number)

        if company is not None:
            metadata["company_id"] = str(company.id)
            metadata["company_name"] = company.name

        if filing is not None:
            metadata["filing_type"] = filing.filing_type.value
            metadata["filing_date"] = filing.filing_date.isoformat()

        return metadata
