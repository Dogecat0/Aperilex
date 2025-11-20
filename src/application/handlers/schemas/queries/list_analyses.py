"""List Analyses Query for retrieving analyses with filtering and pagination."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from src.application.base.query import BaseQuery
from src.shared.enums import AnalysisStatus
from src.shared.types import CIK


class AnalysisSegment(str, Enum):
    """Dashboard-oriented segment filter for analyses."""

    ALL = "all"
    ATTENTION = "attention"
    READY_FOR_REVIEW = "ready_for_review"
    FLAGGED = "flagged"


class AnalysisSortField(str, Enum):
    """Fields available for ordering analysis results."""

    CREATED_AT = "created_at"
    CONFIDENCE_SCORE = "confidence_score"
    CRITICAL_FINDINGS = "insight_counts.critical_findings"
    FILING_DATE = "filing_date"


class SortDirection(str, Enum):
    """Sort direction options acknowledged by the API."""

    ASC = "asc"
    DESC = "desc"


class ListAnalysesQuery(BaseQuery):
    """Query DTO for the `/api/analyses` listing endpoint."""

    schema_version: int = Field(default=2, ge=2)
    company_cik: CIK | None = Field(
        default=None,
        description="Optional company CIK for scoping to a single issuer",
    )
    search: str | None = Field(
        default=None,
        description="Full-text search over company name, ticker, CIK, and filing type",
    )
    segment: AnalysisSegment = Field(
        default=AnalysisSegment.ALL,
        description="Dashboard segment to apply (all|attention|ready_for_review|flagged)",
    )
    statuses: list[AnalysisStatus] | None = Field(
        default=None,
        description="Optional list of statuses to include (intersection with segment)",
    )
    created_after: datetime | None = Field(
        default=None,
        description="Lower bound for analysis creation timestamp (inclusive)",
    )
    created_before: datetime | None = Field(
        default=None,
        description="Upper bound for analysis creation timestamp (inclusive)",
    )
    created_by: str | None = Field(
        default=None,
        description="Filter analyses initiated by a particular user identifier",
    )
    sort_by: AnalysisSortField = Field(
        default=AnalysisSortField.CREATED_AT,
        description="Field used to order the results",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Ordering direction for the sort field",
    )

    @field_validator("search")
    @classmethod
    def _trim_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized[:128]

    @field_validator("created_by")
    @classmethod
    def _normalize_created_by(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("statuses")
    @classmethod
    def _dedupe_statuses(
        cls, value: list[AnalysisStatus] | None
    ) -> list[AnalysisStatus] | None:
        if value is None:
            return None
        deduped: list[AnalysisStatus] = []
        seen: set[AnalysisStatus] = set()
        for status in value:
            if status not in seen:
                deduped.append(status)
                seen.add(status)
        return deduped or None

    @model_validator(mode="after")
    def _validate_chronology(self) -> ListAnalysesQuery:
        if (
            self.created_after is not None
            and self.created_before is not None
            and self.created_after > self.created_before
        ):
            raise ValueError("created_after cannot be later than created_before")
        return self

    @property
    def has_company_filter(self) -> bool:
        return self.company_cik is not None

    @property
    def has_status_filter(self) -> bool:
        return bool(self.statuses)

    @property
    def has_search(self) -> bool:
        return bool(self.search)

    @property
    def has_created_by_filter(self) -> bool:
        return bool(self.created_by)

    @property
    def has_date_range_filter(self) -> bool:
        return self.created_after is not None or self.created_before is not None

    @property
    def sort_requires_summary(self) -> bool:
        return self.sort_by is AnalysisSortField.CRITICAL_FINDINGS

    def status_names(self) -> list[str] | None:
        if not self.statuses:
            return None
        return [status.value for status in self.statuses]

    def as_sort_tuple(self) -> tuple[AnalysisSortField, SortDirection]:
        return self.sort_by, self.sort_direction
