from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BalanceSheetTrend(str, Enum):
    """Balance sheet trend classification."""

    IMPROVING = "Improving"
    STABLE = "Stable"
    DECLINING = "Declining"
    VOLATILE = "Volatile"


class LiquidityPosition(str, Enum):
    """Liquidity position classification."""

    STRONG = "Strong"
    ADEQUATE = "Adequate"
    WEAK = "Weak"
    CRITICAL = "Critical"


class DebtLevel(str, Enum):
    """Debt level classification."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    EXCESSIVE = "Excessive"


class FinancialRatio(BaseModel):
    """Financial ratio analysis."""

    ratio_name: str
    current_value: float | None = Field(...)
    previous_value: float | None = Field(...)
    industry_benchmark: float | None = Field(...)
    interpretation: str


class AssetComposition(BaseModel):
    """Asset composition analysis."""

    current_assets_percentage: float | None = Field(...)
    non_current_assets_percentage: float | None = Field(...)
    key_asset_categories: list[str]
    asset_quality_assessment: str


class LiabilityStructure(BaseModel):
    """Liability structure analysis."""

    current_liabilities_percentage: float | None = Field(...)
    long_term_debt_percentage: float | None = Field(...)
    debt_maturity_profile: str
    liability_concerns: list[str]


class EquityAnalysis(BaseModel):
    """Equity analysis."""

    total_equity_change: str
    retained_earnings_trend: str
    share_capital_changes: str
    equity_quality_assessment: str


class BalanceSheetAnalysisSection(BaseModel):
    """Balance sheet analysis section."""

    section_summary: str
    period_covered: str
    total_assets: str | None = Field(...)
    total_liabilities: str | None = Field(...)
    total_equity: str | None = Field(...)

    # Financial Health Metrics
    liquidity_position: LiquidityPosition
    debt_level: DebtLevel
    overall_trend: BalanceSheetTrend

    # Detailed Analysis
    asset_composition: AssetComposition
    liability_structure: LiabilityStructure
    equity_analysis: EquityAnalysis

    # Financial Ratios
    key_ratios: list[FinancialRatio]

    # Insights
    strengths: list[str]
    concerns: list[str]
    year_over_year_changes: list[str]
    notable_items: list[str]
    management_commentary: str | None = Field(...)

    @field_validator(
        "key_ratios", "strengths", "concerns", "year_over_year_changes", "notable_items"
    )
    @classmethod
    def validate_required_lists(cls, v: list[Any]) -> list[Any]:
        """Require at least one item in key lists"""
        if not v:
            raise ValueError("List cannot be empty")
        return v
