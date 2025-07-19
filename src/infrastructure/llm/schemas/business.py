"""Business section analysis schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Region(str, Enum):
    """Geographic regions for business segmentation."""

    NORTH_AMERICA = "North America"
    EUROPE = "Europe"
    ASIA = "Asia"
    SOUTH_AMERICA = "South America"
    AFRICA = "Africa"
    OCEANIA = "Oceania"
    MIDDLE_EAST = "Middle East"


class BusinessSegment(str, Enum):
    """Common business segment classification."""

    TECHNOLOGY = "Technology"
    FINANCIAL_SERVICES = "Financial Services"
    HEALTHCARE = "Healthcare"
    CONSUMER_GOODS = "Consumer Goods"
    INDUSTRIALS = "Industrials"
    ENERGY = "Energy"
    MANUFACTURING = "Manufacturing"
    RETAIL = "Retail"
    TELECOMMUNICATIONS = "Telecommunications"
    MEDIA = "Media"
    TRANSPORTATION = "Transportation"
    REAL_ESTATE = "Real Estate"
    HOSPITALITY = "Hospitality"
    EDUCATION = "Education"
    AGRICULTURE = "Agriculture"
    MINING = "Mining"
    AUTOMOTIVE = "Automotive"
    AEROSPACE = "Aerospace"
    PHARMACEUTICALS = "Pharmaceuticals"
    UTILITIES = "Utilities"
    ENTERTAINMENT = "Entertainment"
    CONSTRUCTION = "Construction"
    LOGISTICS = "Logistics"
    INSURANCE = "Insurance"
    SOFTWARE = "Software"
    HARDWARE = "Hardware"
    BIOTECHNOLOGY = "Biotechnology"
    FOOD_BEVERAGE = "Food & Beverage"
    PROFESSIONAL_SERVICES = "Professional Services"
    E_COMMERCE = "E-Commerce"
    SOCIAL_MEDIA = "Social Media"


# --- Business Components ---
class OperationalOverview(BaseModel):
    """Core business operations description."""

    description: str
    industry_classification: str
    primary_markets: list[BusinessSegment]
    target_customers: str | None = Field(...)
    business_model: str | None = Field(...)

    @field_validator("primary_markets")
    @classmethod
    def validate_markets(cls, v: list[BusinessSegment]) -> list[BusinessSegment]:
        """Require at least one primary market"""
        if len(v) < 1:
            raise ValueError("At least one primary market must be provided")
        return v


class KeyProduct(BaseModel):
    """Revenue-generation product or service."""

    name: str
    description: str
    significance: str | None = Field(...)


class CompetitiveAdvantage(BaseModel):
    """Sustainable competitive advantage."""

    advantage: str
    description: str
    competitors: list[str] | None = Field(...)
    sustainability: str | None = Field(...)

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: list[str] | None) -> list[str] | None:
        """Require at least one competitor"""
        if v and len(v) < 1:
            raise ValueError("At least one competitor must be provided")
        return v


class StrategicInitiative(BaseModel):
    """Strategic business initiative."""

    name: str
    description: str
    impact: str
    timeframe: str | None = Field(...)
    resource_allocation: str | None = Field(...)


# --- Additional Business Elements ---
class SupplyChain(BaseModel):
    """Supply chain information for the business."""

    description: str
    key_suppliers: list[str] | None = Field(...)
    sourcing_strategy: str | None = Field(...)
    risks: str | None = Field(...)


class Partnership(BaseModel):
    """Strategic partnership or distribution channel."""

    name: str
    description: str
    partnership_type: str
    strategic_value: str | None = Field(...)


# --- Segment Models ---
class BaseSegment(BaseModel):
    """Base class for business segment analysis."""

    name: str
    description: str
    strategic_importance: str | None = Field(...)
    market_position: str | None = Field(...)
    growth_outlook: str | None = Field(...)
    key_competitors: list[str] | None = Field(...)
    relative_size: str | None = Field(...)


class BusinessSegmentAnalysis(BaseSegment):
    """Business unit segment analysis."""

    segment_type: BusinessSegment
    market_trends: str | None = Field(...)
    product_differentiation: str | None = Field(...)


class GeographicSegmentAnalysis(BaseSegment):
    """Geographic segment analysis."""

    region: Region
    market_characteristics: str | None = Field(...)
    regulatory_environment: str | None = Field(...)
    expansion_strategy: str | None = Field(...)


# --- Business Analysis Model ---
class BusinessAnalysisSection(BaseModel):
    """Comprehensive business analysis."""

    operational_overview: OperationalOverview
    key_products: list[KeyProduct]
    competitive_advantages: list[CompetitiveAdvantage]
    strategic_initiatives: list[StrategicInitiative]
    business_segments: list[BusinessSegmentAnalysis]
    geographic_segments: list[GeographicSegmentAnalysis]
    supply_chain: SupplyChain | None = Field(...)
    partnerships: list[Partnership] | None = Field(...)

    @field_validator(
        "key_products",
        "competitive_advantages",
        "strategic_initiatives",
        "business_segments",
        "geographic_segments",
    )
    @classmethod
    def validate_segments(cls, v: list[Any]) -> list[Any]:
        """Require at least one segment for each category"""
        if len(v) < 1:
            raise ValueError("At least one segment must be provided")
        return v
