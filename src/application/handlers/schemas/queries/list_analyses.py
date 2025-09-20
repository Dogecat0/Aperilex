"""List Analyses Query for retrieving analyses with filtering and pagination."""

from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from src.application.base.query import BaseQuery
from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.shared.enums import AnalysisType
from src.shared.types import CIK


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


class ListAnalysesQuery(BaseQuery):
    """Query to list analyses with basic filtering, sorting, and pagination.

    This query supports essential filtering for the planned API endpoints.

    Attributes:
        company_cik: Filter by specific company CIK (optional)
        analysis_types: Filter by analysis types (optional)
        analysis_template: Filter by analysis template (optional)
        created_from: Filter analyses created from this date (inclusive, optional)
        created_to: Filter analyses created to this date (inclusive, optional)
        min_confidence_score: Filter by minimum confidence score (optional)
        offset: Number of results to skip for pagination (optional)
        limit: Maximum number of results to return (optional)
        sort_by: Field to sort results by
        sort_direction: Sort direction (ascending or descending)
    """

    company_cik: CIK | None = Field(
        default=None,
        description="Filter by specific company CIK",
    )
    analysis_types: list[AnalysisType] | None = Field(
        default=None,
        description="Filter by analysis types",
    )
    analysis_template: AnalysisTemplate | None = Field(
        default=None,
        description="Filter by analysis template",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Filter analyses created from this date",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Filter analyses created to this date",
    )
    min_confidence_score: float | None = Field(
        default=None,
        description="Filter by minimum confidence score (0.0-1.0)",
    )
    sort_by: AnalysisSortField = Field(
        default=AnalysisSortField.CREATED_AT,
        description="Field to sort results by",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sort direction",
    )

    @model_validator(mode="after")
    def _validate(self) -> "ListAnalysesQuery":
        """Validate date ranges, filters, and confidence scores."""
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from cannot be later than created_to")

        if self.analysis_types is not None:
            if len(self.analysis_types) == 0:
                raise ValueError("analysis_types cannot be empty list")
            if len(set(self.analysis_types)) != len(self.analysis_types):
                raise ValueError("analysis_types contains duplicates")

        if self.min_confidence_score is not None:
            if not (0.0 <= self.min_confidence_score <= 1.0):
                raise ValueError("min_confidence_score must be between 0.0 and 1.0")

        return self

    @property
    def has_company_filter(self) -> bool:
        """Check if query filters by specific company.

        Returns:
            True if company_cik filter is applied
        """
        return self.company_cik is not None

    @property
    def has_date_range_filter(self) -> bool:
        """Check if query filters by date range.

        Returns:
            True if either created_from or created_to is set
        """
        return self.created_from is not None or self.created_to is not None

    @property
    def has_type_filter(self) -> bool:
        """Check if query filters by analysis type.

        Returns:
            True if analysis_types filter is applied
        """
        return self.analysis_types is not None

    @property
    def has_template_filter(self) -> bool:
        """Check if query filters by analysis template.

        Returns:
            True if analysis_template filter is applied
        """
        return self.analysis_template is not None

    def get_analysis_types_for_template(self) -> list[AnalysisType] | None:
        """Map analysis template to corresponding analysis types.

        This method provides intelligent mapping between analysis templates and database analysis types.
        Templates are logical groupings that can map to multiple database analysis types.

        Returns:
            List of analysis types that correspond to the template, or None if no template filter
        """
        if not self.has_template_filter:
            return None

        # Map analysis templates to database analysis types
        # Each template can potentially match multiple analysis types stored in the database
        template_to_types_mapping = {
            # Comprehensive template includes all types of analysis
            AnalysisTemplate.COMPREHENSIVE: [
                AnalysisType.FILING_ANALYSIS,
                AnalysisType.COMPREHENSIVE,
                AnalysisType.CUSTOM_QUERY,  # May include comprehensive custom queries
            ],
            # Financial focused template should match analyses focused on financial data
            AnalysisTemplate.FINANCIAL_FOCUSED: [
                AnalysisType.FILING_ANALYSIS,  # Filing analysis includes financial sections
                AnalysisType.COMPREHENSIVE,  # Comprehensive analysis includes financial data
                AnalysisType.CUSTOM_QUERY,  # Custom queries may be financial-focused
            ],
            # Risk focused template for risk assessment analyses
            AnalysisTemplate.RISK_FOCUSED: [
                AnalysisType.FILING_ANALYSIS,  # Filing analysis includes risk sections
                AnalysisType.COMPREHENSIVE,  # Comprehensive analysis includes risk analysis
                AnalysisType.CUSTOM_QUERY,  # Custom queries may be risk-focused
            ],
            # Business focused template for strategic and operational analyses
            AnalysisTemplate.BUSINESS_FOCUSED: [
                AnalysisType.FILING_ANALYSIS,  # Filing analysis includes business sections
                AnalysisType.COMPREHENSIVE,  # Comprehensive analysis includes business analysis
                AnalysisType.CUSTOM_QUERY,  # Custom queries may be business-focused
            ],
        }

        return (
            template_to_types_mapping.get(self.analysis_template)
            if self.analysis_template
            else None
        )
