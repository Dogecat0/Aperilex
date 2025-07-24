"""Integration tests for OpenAI provider error handling and retry logic.

These tests simulate various error scenarios to ensure robust error handling.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
import json

from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.infrastructure.llm.base import ComprehensiveAnalysisResponse, SectionAnalysisResponse
from src.infrastructure.edgar.schemas.filing_data import FilingData


class TestOpenAIProviderErrorHandling:
    """Test error handling and resilience of OpenAI provider."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider for testing."""
        return OpenAIProvider()

    @pytest.fixture
    def sample_filing_data(self):
        """Create sample filing data for testing."""
        return FilingData(
            accession_number="0000320193-23-000077",
            filing_type="10-K",
            filing_date="2023-11-03",
            company_name="Apple Inc.",
            cik="0000320193",
            content_text="Sample filing content for testing...",
            sections={
                "business": "Apple Inc. designs, manufactures and markets smartphones...",
                "risk_factors": "The Company's business is subject to various risks...",
                "mda": "Management's Discussion and Analysis of financial condition..."
            }
        )

    def test_rate_limit_error_handling(self, provider, sample_filing_data):
        """Test handling of OpenAI rate limit errors."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # Simulate rate limit error on first call, success on retry
            mock_create.side_effect = [
                RateLimitError("Rate limit exceeded", response=Mock(), body=None),
                Mock(choices=[Mock(message=Mock(content=json.dumps({
                    "executive_summary": "Test summary",
                    "key_insights": ["Insight 1"],
                    "financial_highlights": ["Highlight 1"],
                    "risk_factors": ["Risk 1"],
                    "growth_opportunities": ["Opportunity 1"],
                    "sentiment_score": 0.7
                })))])
            ]
            
            # Should retry and succeed
            result = provider.analyze_filing(sample_filing_data)
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert mock_create.call_count == 2

    def test_api_connection_error_handling(self, provider, sample_filing_data):
        """Test handling of API connection errors."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = APIConnectionError("Connection failed")
            
            with pytest.raises(Exception, match="OpenAI API error"):
                provider.analyze_filing(sample_filing_data)

    def test_api_timeout_error_handling(self, provider, sample_filing_data):
        """Test handling of API timeout errors."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # Simulate timeout on first call, success on retry
            mock_create.side_effect = [
                APITimeoutError("Request timeout"),
                Mock(choices=[Mock(message=Mock(content=json.dumps({
                    "executive_summary": "Test summary",
                    "key_insights": ["Insight 1"],
                    "financial_highlights": ["Highlight 1"],
                    "risk_factors": ["Risk 1"],
                    "growth_opportunities": ["Opportunity 1"],
                    "sentiment_score": 0.7
                })))])
            ]
            
            result = provider.analyze_filing(sample_filing_data)
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert mock_create.call_count == 2

    def test_invalid_json_response_handling(self, provider, sample_filing_data):
        """Test handling of invalid JSON responses from OpenAI."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content="Invalid JSON response"))]
            )
            
            with pytest.raises(Exception, match="Failed to parse OpenAI response"):
                provider.analyze_filing(sample_filing_data)

    def test_partial_json_response_handling(self, provider, sample_filing_data):
        """Test handling of partial/incomplete JSON responses."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # Return JSON with missing required fields
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content=json.dumps({
                    "executive_summary": "Test summary",
                    # Missing other required fields
                })))]
            )
            
            with pytest.raises(Exception):
                provider.analyze_filing(sample_filing_data)

    def test_empty_response_handling(self, provider, sample_filing_data):
        """Test handling of empty responses from OpenAI."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[])
            
            with pytest.raises(Exception, match="No response choices"):
                provider.analyze_filing(sample_filing_data)

    def test_concurrent_request_error_handling(self, provider, sample_filing_data):
        """Test error handling during concurrent section processing."""
        sections = ["business", "risk_factors", "mda"]
        
        with patch.object(provider, '_analyze_section') as mock_analyze:
            # Simulate error in one section, success in others
            mock_analyze.side_effect = [
                SectionAnalysisResponse(
                    section_name="business",
                    key_insights=["Business insight"],
                    summary="Business summary",
                    sentiment_score=0.7
                ),
                Exception("Analysis failed for risk_factors"),
                SectionAnalysisResponse(
                    section_name="mda",
                    key_insights=["MDA insight"],
                    summary="MDA summary",
                    sentiment_score=0.6
                )
            ]
            
            # Should handle partial failures gracefully
            with pytest.raises(Exception):
                provider._analyze_sections_concurrently(
                    {section: f"Content for {section}" for section in sections},
                    template="COMPREHENSIVE"
                )

    def test_retry_mechanism_exhaustion(self, provider, sample_filing_data):
        """Test behavior when retry mechanism is exhausted."""
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # Always return rate limit error
            mock_create.side_effect = RateLimitError(
                "Rate limit exceeded", response=Mock(), body=None
            )
            
            with pytest.raises(Exception):
                provider.analyze_filing(sample_filing_data)
            
            # Should have attempted multiple retries
            assert mock_create.call_count > 1

    def test_section_analysis_error_recovery(self, provider):
        """Test error recovery in section-specific analysis."""
        section_content = "Test content for analysis"
        
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            # First call fails, second succeeds
            mock_create.side_effect = [
                APIConnectionError("Connection failed"),
                Mock(choices=[Mock(message=Mock(content=json.dumps({
                    "key_insights": ["Recovered insight"],
                    "summary": "Recovered summary",
                    "sentiment_score": 0.5
                })))])
            ]
            
            result = provider._analyze_section(
                section_content, "business", "Test schema"
            )
            
            assert result.key_insights == ["Recovered insight"]
            assert mock_create.call_count == 2

    def test_large_content_truncation_handling(self, provider):
        """Test handling of content that exceeds token limits."""
        # Create very large content
        large_content = "Large content " * 10000
        filing_data = FilingData(
            accession_number="test",
            form_type="10-K",
            filing_date="2023-01-01",
            company_name="Test Company",
            sections={"business": large_content}
        )
        
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content=json.dumps({
                    "executive_summary": "Test summary",
                    "key_insights": ["Insight 1"],
                    "financial_highlights": ["Highlight 1"],
                    "risk_factors": ["Risk 1"],
                    "growth_opportunities": ["Opportunity 1"],
                    "sentiment_score": 0.7
                })))]
            )
            
            # Should handle large content without errors
            result = provider.analyze_filing(filing_data)
            assert isinstance(result, ComprehensiveAnalysisResponse)

    def test_schema_validation_error_handling(self, provider, sample_filing_data):
        """Test handling of schema validation errors."""
        with patch.object(provider, '_get_section_schema_mapping') as mock_schema:
            mock_schema.side_effect = Exception("Schema validation failed")
            
            with pytest.raises(Exception, match="Schema validation failed"):
                provider.analyze_filing(sample_filing_data)

    def test_missing_openai_credentials(self):
        """Test handling of missing OpenAI credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.shared.config.settings.openai_api_key', None):
                with pytest.raises(Exception):
                    OpenAIProvider()

    def test_invalid_template_handling(self, provider, sample_filing_data):
        """Test handling of invalid analysis templates."""
        with pytest.raises(ValueError, match="Invalid template"):
            provider.analyze_filing(sample_filing_data, template="INVALID_TEMPLATE")

    def test_concurrent_analysis_resource_management(self, provider, sample_filing_data):
        """Test resource management during concurrent analysis."""
        # Create filing with many sections
        large_filing = FilingData(
            accession_number="test",
            form_type="10-K",  
            filing_date="2023-01-01",
            company_name="Test Company",
            sections={f"section_{i}": f"Content {i}" for i in range(20)}
        )
        
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content=json.dumps({
                    "executive_summary": "Test summary",
                    "key_insights": ["Insight 1"],
                    "financial_highlights": ["Highlight 1"],
                    "risk_factors": ["Risk 1"],
                    "growth_opportunities": ["Opportunity 1"],
                    "sentiment_score": 0.7
                })))]
            )
            
            # Should handle many concurrent requests without resource exhaustion
            result = provider.analyze_filing(large_filing)
            assert isinstance(result, ComprehensiveAnalysisResponse)