from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CashFlowTrend(str, Enum):
    """Cash flow trend classification."""

    IMPROVING = "Improving"
    STABLE = "Stable"
    DECLINING = "Declining"
    VOLATILE = "Volatile"


class CashPosition(str, Enum):
    """Cash position classification."""

    STRONG = "Strong"
    ADEQUATE = "Adequate"
    TIGHT = "Tight"
    CRITICAL = "Critical"


class CashFlowQuality(str, Enum):
    """Cash flow quality classification."""

    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    POOR = "Poor"


class OperatingCashFlow(BaseModel):
    """Operating cash flow analysis."""

    net_cash_from_operations: str | None = Field(...)
    cash_conversion_ratio: float | None = Field(...)
    working_capital_impact: str
    quality_assessment: str


class InvestingCashFlow(BaseModel):
    """Investing cash flow analysis."""

    net_cash_from_investing: str | None = Field(...)
    capital_expenditures: str | None = Field(...)
    asset_acquisitions: str | None = Field(...)
    investment_strategy_commentary: str


class FinancingCashFlow(BaseModel):
    """Financing cash flow analysis."""

    net_cash_from_financing: str | None = Field(...)
    debt_changes: str | None = Field(...)
    dividend_payments: str | None = Field(...)
    share_repurchases: str | None = Field(...)
    financing_strategy_commentary: str


class CashFlowRatio(BaseModel):
    """Cash flow ratio analysis."""

    ratio_name: str
    current_value: float | None = Field(...)
    previous_value: float | None = Field(...)
    interpretation: str


class CashFlowAnalysisSection(BaseModel):
    """Cash flow statement analysis section."""

    section_summary: str
    period_covered: str
    beginning_cash: str | None = Field(...)
    ending_cash: str | None = Field(...)
    net_change_in_cash: str | None = Field(...)

    # Cash Flow Health
    cash_flow_trend: CashFlowTrend
    cash_position: CashPosition
    cash_flow_quality: CashFlowQuality

    # Detailed Analysis by Category
    operating_cash_flow: OperatingCashFlow
    investing_cash_flow: InvestingCashFlow
    financing_cash_flow: FinancingCashFlow

    # Cash Flow Ratios
    cash_flow_ratios: list[CashFlowRatio]

    # Free Cash Flow Analysis
    free_cash_flow: str | None = Field(...)
    free_cash_flow_yield: float | None = Field(...)
    free_cash_flow_growth: str | None = Field(...)

    # Liquidity Analysis
    cash_runway_assessment: str
    debt_service_coverage: str | None = Field(...)
    capital_allocation_priorities: list[str]

    # Insights
    cash_flow_strengths: list[str]
    cash_flow_concerns: list[str]
    seasonal_patterns: list[str]
    management_commentary: str | None = Field(...)

    @field_validator(
        "cash_flow_ratios",
        "capital_allocation_priorities",
        "cash_flow_strengths",
        "cash_flow_concerns",
    )
    @classmethod
    def validate_required_lists(cls, v: list[Any]) -> list[Any]:
        """Require at least one item in key lists"""
        if not v:
            raise ValueError("List cannot be empty")
        return v
