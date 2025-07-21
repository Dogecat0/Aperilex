"""List Analyses Query for retrieving analyses with filtering and pagination."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.application.base.query import BaseQuery
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class AnalysisSortField(str, Enum):
    """Fields available for sorting analysis results."""

    CREATED_AT = "created_at"
    CONFIDENCE_SCORE = "confidence_score"
    FILING_DATE = "filing_date"
    COMPANY_NAME = "company_name"
    ANALYSIS_TYPE = "analysis_type"


class SortDirection(str, Enum):
    """Sort direction options."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class ListAnalysesQuery(BaseQuery):
    """Query to list analyses with filtering, sorting, and pagination.

    This query supports comprehensive filtering of analyses by various criteria
    such as company, analysis type, confidence levels, and date range.

    Attributes:
        company_cik: Filter by specific company CIK (optional)
        filing_id: Filter by specific filing ID (optional)
        analysis_types: Filter by analysis types (optional)
        created_from: Filter analyses created from this date (inclusive, optional)
        created_to: Filter analyses created to this date (inclusive, optional)
        min_confidence_score: Minimum confidence score filter (optional)
        max_confidence_score: Maximum confidence score filter (optional)
        created_by: Filter by analysis creator (optional)
        llm_provider: Filter by LLM provider used (optional)
        sort_by: Field to sort results by
        sort_direction: Sort direction (ascending or descending)
        include_summary_only: Whether to return only summary data (not full results)
    """

    company_cik: CIK | None = None
    filing_id: UUID | None = None
    analysis_types: list[AnalysisType] | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    min_confidence_score: float | None = None
    max_confidence_score: float | None = None
    created_by: str | None = None
    llm_provider: str | None = None
    sort_by: AnalysisSortField = AnalysisSortField.CREATED_AT
    sort_direction: SortDirection = SortDirection.DESC
    include_summary_only: bool = True

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate date range
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from cannot be later than created_to")

        # Validate confidence score range
        if self.min_confidence_score is not None:
            if not 0.0 <= self.min_confidence_score <= 1.0:
                raise ValueError("min_confidence_score must be between 0.0 and 1.0")

        if self.max_confidence_score is not None:
            if not 0.0 <= self.max_confidence_score <= 1.0:
                raise ValueError("max_confidence_score must be between 0.0 and 1.0")

        if (
            self.min_confidence_score is not None
            and self.max_confidence_score is not None
            and self.min_confidence_score > self.max_confidence_score
        ):
            raise ValueError(
                "min_confidence_score cannot be greater than max_confidence_score"
            )

        # Validate analysis types list
        if self.analysis_types is not None:
            if len(self.analysis_types) == 0:
                raise ValueError("analysis_types cannot be empty list")

            # Check for duplicates
            if len(set(self.analysis_types)) != len(self.analysis_types):
                raise ValueError("analysis_types contains duplicates")

        # Validate created_by
        if self.created_by is not None:
            if not self.created_by.strip():
                raise ValueError("created_by cannot be empty string")

        # Validate llm_provider
        if self.llm_provider is not None:
            if not self.llm_provider.strip():
                raise ValueError("llm_provider cannot be empty string")

    @property
    def has_company_filter(self) -> bool:
        """Check if query filters by specific company.

        Returns:
            True if company_cik filter is applied
        """
        return self.company_cik is not None

    @property
    def has_filing_filter(self) -> bool:
        """Check if query filters by specific filing.

        Returns:
            True if filing_id filter is applied
        """
        return self.filing_id is not None

    @property
    def has_date_range_filter(self) -> bool:
        """Check if query filters by date range.

        Returns:
            True if either created_from or created_to is set
        """
        return self.created_from is not None or self.created_to is not None

    @property
    def has_confidence_filter(self) -> bool:
        """Check if query filters by confidence score.

        Returns:
            True if min_confidence_score or max_confidence_score is set
        """
        return (
            self.min_confidence_score is not None
            or self.max_confidence_score is not None
        )

    @property
    def has_type_filter(self) -> bool:
        """Check if query filters by analysis type.

        Returns:
            True if analysis_types filter is applied
        """
        return self.analysis_types is not None

    @property
    def has_creator_filter(self) -> bool:
        """Check if query filters by creator.

        Returns:
            True if created_by filter is applied
        """
        return self.created_by is not None

    @property
    def has_provider_filter(self) -> bool:
        """Check if query filters by LLM provider.

        Returns:
            True if llm_provider filter is applied
        """
        return self.llm_provider is not None

    @property
    def filter_count(self) -> int:
        """Get the number of active filters.

        Returns:
            Count of active filter criteria
        """
        count = 0
        if self.has_company_filter:
            count += 1
        if self.has_filing_filter:
            count += 1
        if self.has_date_range_filter:
            count += 1
        if self.has_confidence_filter:
            count += 1
        if self.has_type_filter:
            count += 1
        if self.has_creator_filter:
            count += 1
        if self.has_provider_filter:
            count += 1
        return count

    def get_filter_summary(self) -> str:
        """Get a human-readable summary of active filters.

        Returns:
            String description of active filters
        """
        filters = []

        if self.has_company_filter:
            filters.append(f"company {self.company_cik}")

        if self.has_filing_filter:
            filters.append(f"filing {self.filing_id}")

        if self.has_type_filter and self.analysis_types:
            type_names = [t.value for t in self.analysis_types]
            if len(type_names) == 1:
                filters.append(f"type {type_names[0]}")
            else:
                filters.append(f"types {', '.join(type_names)}")

        if self.has_confidence_filter:
            conf_parts = []
            if self.min_confidence_score is not None:
                conf_parts.append(f"min {self.min_confidence_score:.2f}")
            if self.max_confidence_score is not None:
                conf_parts.append(f"max {self.max_confidence_score:.2f}")
            filters.append(f"confidence {' '.join(conf_parts)}")

        if self.has_date_range_filter:
            date_parts = []
            if self.created_from:
                date_parts.append(f"from {self.created_from.date()}")
            if self.created_to:
                date_parts.append(f"to {self.created_to.date()}")
            filters.append(" ".join(date_parts))

        if self.has_creator_filter:
            filters.append(f"creator {self.created_by}")

        if self.has_provider_filter:
            filters.append(f"provider {self.llm_provider}")

        if not filters:
            return "no filters"

        return ", ".join(filters)
