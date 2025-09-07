"""
Analysis request and result models for LLM processing.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.shared.enums.provider import LLMProvider
from src.shared.enums.status import AnalysisStatus
from src.shared.types.identifiers import AnalysisId, FilingId, TaskId, UserId


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""

    SUMMARY = "SUMMARY"
    KEY_METRICS = "KEY_METRICS"
    RISK_FACTORS = "RISK_FACTORS"
    FINANCIAL_HIGHLIGHTS = "FINANCIAL_HIGHLIGHTS"
    SENTIMENT = "SENTIMENT"
    COMPETITIVE_ANALYSIS = "COMPETITIVE_ANALYSIS"
    CUSTOM = "CUSTOM"


class ModelTier(str, Enum):
    """LLM model tier for cost/performance trade-offs."""

    ECONOMY = "ECONOMY"  # Cheapest, fastest, lower quality
    STANDARD = "STANDARD"  # Balanced cost/quality
    PREMIUM = "PREMIUM"  # High quality, higher cost
    ULTRA = "ULTRA"  # Best quality, highest cost


class AnalysisRequest(BaseModel):
    """
    Request model for initiating an analysis.

    Contains all parameters needed to perform an LLM analysis
    on a filing document.
    """

    schema_version: int = Field(
        default=1, description="Schema version for backward compatibility"
    )

    # Core identifiers
    analysis_id: AnalysisId = Field(description="Unique analysis identifier (UUID)")
    filing_id: FilingId = Field(description="Filing to analyze (UUID)")
    task_id: TaskId = Field(description="Associated task ID (UUID)")
    user_id: UserId = Field(description="User requesting analysis (UUID)")

    # Analysis parameters
    analysis_type: AnalysisType = Field(
        default=AnalysisType.SUMMARY, description="Type of analysis to perform"
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI, description="LLM provider to use"
    )
    model_tier: ModelTier = Field(
        default=ModelTier.STANDARD, description="Model tier for cost/quality trade-off"
    )

    # Model configuration
    model_name: str | None = Field(
        default=None, description="Specific model name override"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for response generation"
    )
    max_tokens: int | None = Field(
        default=None, description="Maximum tokens for response"
    )

    # Custom prompts (for CUSTOM analysis type)
    system_prompt: str | None = Field(
        default=None, description="System prompt override"
    )
    user_prompt: str | None = Field(
        default=None, description="User prompt for custom analysis"
    )

    # Response format
    response_format: str | None = Field(
        default=None, description="Desired response format (json, markdown, text)"
    )
    include_citations: bool = Field(
        default=False, description="Include source citations in response"
    )

    # Processing options
    streaming: bool = Field(default=False, description="Stream response tokens")
    timeout_seconds: int = Field(default=300, description="Request timeout in seconds")

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Request creation timestamp"
    )
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
        validate_assignment = True


class TokenUsage(BaseModel):
    """Token usage information for LLM processing."""

    prompt_tokens: int = Field(description="Number of tokens in the prompt")
    completion_tokens: int = Field(description="Number of tokens in the completion")
    total_tokens: int = Field(description="Total tokens used")

    @property
    def estimated_cost(self) -> float | None:
        """
        Estimate cost based on token usage.

        Note: This is a placeholder - actual pricing should be
        retrieved from provider configuration.
        """
        # Placeholder pricing per 1K tokens
        pricing = {
            "prompt": 0.01,  # $0.01 per 1K prompt tokens
            "completion": 0.03,  # $0.03 per 1K completion tokens
        }

        prompt_cost = (self.prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (self.completion_tokens / 1000) * pricing["completion"]

        return prompt_cost + completion_cost


class AnalysisResult(BaseModel):
    """
    Result model for completed analysis.

    Contains the LLM response and all associated metadata
    from the analysis process.
    """

    schema_version: int = Field(
        default=1, description="Schema version for backward compatibility"
    )

    # Core identifiers
    analysis_id: AnalysisId = Field(description="Unique analysis identifier (UUID)")
    filing_id: FilingId = Field(description="Analyzed filing ID (UUID)")
    task_id: TaskId = Field(description="Associated task ID (UUID)")
    user_id: UserId = Field(description="User who requested analysis (UUID)")

    # Analysis results
    content: str = Field(description="Main analysis content/response")
    summary: str | None = Field(default=None, description="Brief summary of analysis")
    key_findings: list[str] | None = Field(
        default=None, description="List of key findings"
    )

    # Structured data (if applicable)
    # Using Any for structured_data as it can contain arbitrary nested financial data from LLM
    structured_data: dict[str, Any] | None = Field(
        default=None, description="Structured extraction results"
    )
    # Citations have a known structure but can vary by source
    citations: list[dict[str, str | int]] | None = Field(
        default=None, description="Source citations from document"
    )

    # Analysis metadata
    analysis_type: AnalysisType = Field(description="Type of analysis performed")
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED, description="Analysis status"
    )

    # Model information
    llm_provider: LLMProvider = Field(description="LLM provider used")
    model_name: str = Field(description="Specific model used")
    model_version: str | None = Field(default=None, description="Model version")

    # Token usage and cost
    token_usage: TokenUsage = Field(description="Token usage statistics")
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    estimated_cost: float | None = Field(
        default=None, description="Estimated cost in USD"
    )

    # Quality metrics
    confidence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    quality_metrics: dict[str, float] | None = Field(
        default=None, description="Additional quality metrics"
    )

    # Timestamps
    created_at: datetime = Field(description="Result creation timestamp")
    completed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis completion timestamp"
    )
    expires_at: datetime | None = Field(
        default=None, description="Result expiration timestamp"
    )

    # Error information (if failed)
    error_message: str | None = Field(
        default=None, description="Error message if analysis failed"
    )
    error_code: str | None = Field(
        default=None, description="Error code for categorization"
    )

    # Additional metadata
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional result metadata"
    )

    @property
    def is_successful(self) -> bool:
        """Check if analysis was successful."""
        return self.status == AnalysisStatus.COMPLETED and not self.error_message

    @property
    def processing_time_seconds(self) -> float:
        """Get processing time in seconds."""
        return self.processing_time_ms / 1000.0

    def calculate_actual_cost(self) -> float:
        """
        Calculate actual cost based on token usage and provider pricing.

        Returns:
            Actual cost in USD
        """
        if self.estimated_cost is not None:
            return self.estimated_cost

        # Use token usage to calculate if available
        if self.token_usage:
            return self.token_usage.estimated_cost or 0.0

        return 0.0

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
        validate_assignment = True
