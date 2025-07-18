from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RevenueTrend(str, Enum):
    """Revenue trend classification."""

    GROWING = "Growing"
    STABLE = "Stable"
    DECLINING = "Declining"
    VOLATILE = "Volatile"


class ProfitabilityLevel(str, Enum):
    """Profitability level classification."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"


class ExpenseControl(str, Enum):
    """Expense control classification."""

    WELL_CONTROLLED = "Well Controlled"
    ADEQUATELY_MANAGED = "Adequately Managed"
    CONCERNING = "Concerning"
    DETERIORATING = "Deteriorating"


class RevenueSegment(BaseModel):
    """Revenue segment analysis."""

    segment_name: str
    revenue_amount: str | None = Field(...)
    growth_rate: str | None = Field(...)
    percentage_of_total: float | None = Field(...)
    performance_commentary: str


class ExpenseCategory(BaseModel):
    """Expense category analysis."""

    category_name: str
    amount: str | None = Field(...)
    percentage_of_revenue: float | None = Field(...)
    year_over_year_change: str | None = Field(...)
    efficiency_assessment: str


class ProfitabilityMetric(BaseModel):
    """Profitability metric analysis."""

    metric_name: str
    current_value: str | None = Field(...)
    previous_value: str | None = Field(...)
    margin_percentage: float | None = Field(...)
    trend_analysis: str


class IncomeStatementAnalysisSection(BaseModel):
    """Income statement analysis section."""

    section_summary: str
    period_covered: str
    total_revenue: str | None = Field(...)
    net_income: str | None = Field(...)
    earnings_per_share: str | None = Field(...)

    # Performance Metrics
    revenue_trend: RevenueTrend
    profitability_level: ProfitabilityLevel
    expense_control: ExpenseControl

    # Detailed Analysis
    revenue_segments: list[RevenueSegment]
    expense_categories: list[ExpenseCategory]
    profitability_metrics: list[ProfitabilityMetric]

    # Growth Analysis
    revenue_growth_rate: str | None = Field(...)
    operating_income_growth: str | None = Field(...)
    net_income_growth: str | None = Field(...)

    # Margin Analysis
    gross_margin: float | None = Field(...)
    operating_margin: float | None = Field(...)
    net_margin: float | None = Field(...)

    # Insights
    performance_highlights: list[str]
    areas_of_concern: list[str]
    competitive_advantages: list[str]
    seasonal_factors: list[str]
    one_time_items: list[str]
    management_commentary: str | None = Field(...)

    @field_validator(
        "revenue_segments",
        "expense_categories",
        "profitability_metrics",
        "performance_highlights",
        "areas_of_concern",
    )
    @classmethod
    def validate_required_lists(cls, v: list[Any]) -> list[Any]:
        """Require at least one item in key lists"""
        if not v:
            raise ValueError("List cannot be empty")
        return v
