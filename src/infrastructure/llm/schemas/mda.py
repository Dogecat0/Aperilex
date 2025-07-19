"""Management Discussion & Analysis section schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PerformanceDirection(str, Enum):
    """Direction of performance metrics."""

    INCREASED = "Increased"
    DECREASED = "Decreased"
    STABLE = "Stable"
    VOLATILE = "Volatile"


class OutlookSentiment(str, Enum):
    """Outlook sentiment classification."""

    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"
    CAUTIOUS = "Cautious"
    OPTIMISTIC = "Optimistic"


class FinancialMetric(BaseModel):
    """Key financial metric analysis."""

    metric_name: str
    current_value: str | None = Field(...)
    previous_value: str | None = Field(...)
    direction: PerformanceDirection
    percentage_change: str | None = Field(...)
    explanation: str
    significance: str


class RevenueAnalysis(BaseModel):
    """Revenue performance analysis."""

    total_revenue_performance: str
    revenue_drivers: list[str]
    revenue_headwinds: list[str] | None = Field(...)
    segment_performance: list[str] | None = Field(...)
    geographic_performance: list[str] | None = Field(...)
    recurring_vs_onetime: str | None = Field(...)


class ProfitabilityAnalysis(BaseModel):
    """Profitability metrics analysis."""

    gross_margin_analysis: str | None = Field(...)
    operating_margin_analysis: str | None = Field(...)
    net_margin_analysis: str | None = Field(...)
    cost_structure_changes: list[str] | None = Field(...)
    efficiency_improvements: list[str] | None = Field(...)


class LiquidityAnalysis(BaseModel):
    """Liquidity and capital analysis."""

    cash_position: str | None = Field(...)
    cash_flow_analysis: str
    working_capital: str | None = Field(...)
    debt_analysis: str | None = Field(...)
    credit_facilities: str | None = Field(...)
    capital_allocation: str | None = Field(...)


class OperationalHighlights(BaseModel):
    """Key operational performance highlights."""

    achievement: str
    impact: str
    strategic_significance: str | None = Field(...)


class MarketCondition(BaseModel):
    """Market and industry condition analysis."""

    market_description: str
    impact_on_business: str
    competitive_dynamics: str | None = Field(...)
    opportunity_threats: list[str] | None = Field(...)


class ForwardLookingStatement(BaseModel):
    """Forward-looking statement or guidance."""

    statement: str
    metric_area: str
    timeframe: str | None = Field(...)
    assumptions: list[str] | None = Field(...)
    risks_to_guidance: list[str] | None = Field(...)


class CriticalAccounting(BaseModel):
    """Critical accounting policy or estimate."""

    policy_name: str
    description: str
    judgment_areas: list[str]
    impact_on_results: str | None = Field(...)


class MDAAnalysisSection(BaseModel):
    """Comprehensive Management Discussion & Analysis."""

    executive_overview: str
    key_financial_metrics: list[FinancialMetric]
    revenue_analysis: RevenueAnalysis
    profitability_analysis: ProfitabilityAnalysis
    liquidity_analysis: LiquidityAnalysis
    operational_highlights: list[OperationalHighlights]
    market_conditions: list[MarketCondition]
    forward_looking_statements: list[ForwardLookingStatement] | None = Field(...)
    critical_accounting_policies: list[CriticalAccounting] | None = Field(...)
    outlook_summary: str
    outlook_sentiment: OutlookSentiment
    management_priorities: list[str] | None = Field(...)

    @field_validator(
        "key_financial_metrics", "operational_highlights", "market_conditions"
    )
    @classmethod
    def validate_required_lists(cls, v: list[Any]) -> list[Any]:
        """Require at least one item in key lists"""
        if len(v) < 1:
            raise ValueError("At least one item must be provided")
        return v
