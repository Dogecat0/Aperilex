"""Generic sub-section analysis schema for flexibility."""


from pydantic import BaseModel, Field


class GenericSubSectionAnalysis(BaseModel):
    """Generic sub-section analysis for sections without specific schemas."""

    sub_section_name: str = Field(..., description="Semantic name of the sub-section")
    summary: str = Field(..., description="Comprehensive summary of the sub-section")
    key_points: list[str] = Field(..., description="3-5 key points from the sub-section")
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score from -1 to 1")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score from 0 to 1")
    notable_metrics: list[str] | None = Field(default_factory=list, description="Important metrics mentioned")
    concerns: list[str] | None = Field(default_factory=list, description="Any concerns or risks identified")
    opportunities: list[str] | None = Field(default_factory=list, description="Growth opportunities mentioned")
    regulatory_mentions: list[str] | None = Field(default_factory=list, description="Regulatory references")
    strategic_implications: str | None = Field(None, description="Strategic implications for the business")
