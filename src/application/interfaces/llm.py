"""
LLM provider interface for abstracted large language model operations.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.enums import LLMProvider
from src.shared.models import LLMModelInfo
from src.shared.types import FilingId, RequestId


class FinancialAnalysisRequest(BaseModel):
    """Request for financial analysis."""

    schema_version: int = 1
    filing_id: FilingId
    analysis_type: str  # e.g., "fundamental", "technical", "sentiment"
    filing_content: str
    additional_context: dict[str, str] = {}
    parameters: dict[str, float | int | str] = {}


class FinancialAnalysisResponse(BaseModel):
    """Response from financial analysis."""

    schema_version: int = 1
    filing_id: FilingId
    analysis_type: str
    summary: str
    insights: list[str] = []
    metrics: dict[str, float] = {}
    confidence_score: float = 0.0
    processing_time_ms: int = 0


class LLMPrompt(BaseModel):
    """Structured prompt for LLM interaction."""

    schema_version: int = 1
    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: list[str] = []


class LLMResponse(BaseModel):
    """Response from LLM interaction."""

    schema_version: int = 1
    content: str
    model: str
    provider: LLMProvider
    usage_tokens: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    timestamp: datetime
    request_id: RequestId


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    schema_version: int = 1
    provider: LLMProvider
    model_name: str
    api_key_secret_name: str
    api_endpoint: str | None = None
    retry_attempts: int = 3
    timeout_seconds: int = 60
    rate_limit_per_minute: int = 60


@runtime_checkable
class ILLMProvider(Protocol):
    """Protocol for LLM provider implementations."""

    @abstractmethod
    async def analyze_filing(
        self,
        request: FinancialAnalysisRequest,
    ) -> FinancialAnalysisResponse:
        """
        Analyze a financial filing using LLM.

        Args:
            request: Financial analysis request

        Returns:
            Financial analysis response

        Raises:
            LLMError: If analysis fails
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
        """
        ...

    @abstractmethod
    async def generate_completion(
        self,
        prompt: LLMPrompt,
        request_id: RequestId | None = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: Structured prompt for the LLM
            request_id: Optional request ID for tracking

        Returns:
            LLM response with completion

        Raises:
            LLMError: If generation fails
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
        """
        ...

    @abstractmethod
    async def stream_completion(
        self,
        prompt: LLMPrompt,
        request_id: RequestId | None = None,
    ) -> None:
        """
        Stream a completion from the LLM.

        Args:
            prompt: Structured prompt for the LLM
            request_id: Optional request ID for tracking

        Yields:
            Chunks of completion text

        Raises:
            LLMError: If streaming fails
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
        """
        ...

    @abstractmethod
    async def validate_prompt(self, prompt: LLMPrompt) -> bool:
        """
        Validate a prompt before sending to LLM.

        Args:
            prompt: Prompt to validate

        Returns:
            True if prompt is valid

        Raises:
            ValidationError: If prompt is invalid
        """
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens

        Raises:
            LLMError: If token counting fails
        """
        ...

    @abstractmethod
    async def get_model_info(self) -> LLMModelInfo:
        """
        Get information about the current model.

        Returns:
            Model information

        Raises:
            LLMError: If info retrieval fails
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM provider is healthy.

        Returns:
            True if provider is healthy

        Raises:
            LLMError: If health check fails
        """
        ...
