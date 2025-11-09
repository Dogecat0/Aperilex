"""
LLM-related metadata models.
"""

from pydantic import BaseModel


class LLMModelInfo(BaseModel):
    """Structured model information."""

    schema_version: int = 1
    model_name: str
    model_version: str
    provider: str
    supports_streaming: bool
    supports_functions: bool
    pricing_per_1k_tokens: float | None = None
    capabilities: list[str] = []
