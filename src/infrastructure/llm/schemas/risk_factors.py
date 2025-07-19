"""Risk Factors section analysis schemas."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RiskCategory(str, Enum):
    """Categories of business risks."""

    OPERATIONAL = "Operational"
    FINANCIAL = "Financial"
    MARKET = "Market"
    REGULATORY = "Regulatory"
    TECHNOLOGY = "Technology"
    CYBER_SECURITY = "Cyber Security"
    SUPPLY_CHAIN = "Supply Chain"
    CREDIT = "Credit"
    LIQUIDITY = "Liquidity"
    COMPETITIVE = "Competitive"
    REPUTATION = "Reputation"
    ENVIRONMENTAL = "Environmental"
    GEOPOLITICAL = "Geopolitical"
    PANDEMIC = "Pandemic"
    CLIMATE = "Climate"
    LEGAL = "Legal"
    STRATEGIC = "Strategic"
    HUMAN_CAPITAL = "Human Capital"


class RiskSeverity(str, Enum):
    """Risk severity levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskFactor(BaseModel):
    """Individual risk factor analysis."""

    risk_name: str
    category: RiskCategory
    description: str
    severity: RiskSeverity
    probability: str | None = Field(...)
    potential_impact: str
    mitigation_measures: list[str] | None = Field(...)
    timeline: str | None = Field(...)


class IndustryRisk(BaseModel):
    """Industry-specific risk analysis."""

    industry_trends: str
    competitive_pressures: list[str]
    market_volatility: str | None = Field(...)
    disruption_threats: list[str] | None = Field(...)


class RegulatoryRisk(BaseModel):
    """Regulatory and compliance risk analysis."""

    regulatory_environment: str
    compliance_requirements: list[str]
    regulatory_changes: str | None = Field(...)
    enforcement_risks: str | None = Field(...)


class FinancialRisk(BaseModel):
    """Financial risk analysis."""

    credit_risk: str | None = Field(...)
    liquidity_risk: str | None = Field(...)
    market_risk: str | None = Field(...)
    interest_rate_risk: str | None = Field(...)
    currency_risk: str | None = Field(...)


class OperationalRisk(BaseModel):
    """Operational risk analysis."""

    key_personnel_dependence: str | None = Field(...)
    supply_chain_disruption: str | None = Field(...)
    technology_failures: str | None = Field(...)
    quality_control: str | None = Field(...)
    capacity_constraints: str | None = Field(...)


class ESGRisk(BaseModel):
    """Environmental, Social, and Governance risks."""

    environmental_risks: list[str] | None = Field(...)
    social_responsibility: str | None = Field(...)
    governance_concerns: list[str] | None = Field(...)
    sustainability_challenges: str | None = Field(...)


class RiskFactorsAnalysisSection(BaseModel):
    """Comprehensive risk factors analysis."""

    executive_summary: str
    risk_factors: list[RiskFactor]
    industry_risks: IndustryRisk
    regulatory_risks: RegulatoryRisk
    financial_risks: FinancialRisk
    operational_risks: OperationalRisk
    esg_risks: ESGRisk | None = Field(...)
    risk_management_framework: str | None = Field(...)
    overall_risk_assessment: str

    @field_validator("risk_factors")
    @classmethod
    def validate_risk_factors(cls, v: list[RiskFactor]) -> list[RiskFactor]:
        """Require at least one risk factor"""
        if len(v) < 1:
            raise ValueError("At least one risk factor must be provided")
        return v
