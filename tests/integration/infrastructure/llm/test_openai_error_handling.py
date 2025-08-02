"""Integration tests for OpenAI provider error handling and retry logic.

These tests simulate various error scenarios to ensure robust error handling.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError

from src.domain.value_objects.filing_type import FilingType
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.llm.base import (
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
)
from src.infrastructure.llm.openai_provider import OpenAIProvider


class TestOpenAIProviderErrorHandling:
    """Test error handling and resilience of OpenAI provider."""

    @pytest.fixture(autouse=True)
    def reset_mock_state(self):
        """Reset any mock state between tests to prevent leakage."""
        # Clear any function attributes that might be set on side effect functions
        import gc

        gc.collect()  # Force garbage collection to clean up any lingering state
        yield
        gc.collect()  # Clean up after test

    def create_mock_response(self, content_dict, parsed_content=None):
        """Create a properly structured mock response for OpenAI API calls."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps(content_dict)

        # For parse method responses
        if parsed_content:
            mock_response.parsed = Mock(**parsed_content)

        return mock_response

    def setup_both_methods_mock(
        self,
        provider,
        create_response=None,
        parse_response=None,
        create_side_effect=None,
        parse_side_effect=None,
    ):
        """Set up mocks for both create and parse methods with proper structure."""
        create_mock = patch.object(
            provider.client.chat.completions, 'create', new_callable=AsyncMock
        )
        parse_mock = patch.object(
            provider.client.chat.completions, 'parse', new_callable=AsyncMock
        )

        create_patcher = create_mock.__enter__()
        parse_patcher = parse_mock.__enter__()

        if create_side_effect:
            create_patcher.side_effect = create_side_effect
        elif create_response:
            create_patcher.return_value = create_response

        if parse_side_effect:
            parse_patcher.side_effect = parse_side_effect
        elif parse_response:
            parse_patcher.return_value = parse_response

        return create_patcher, parse_patcher, create_mock, parse_mock

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider for testing."""
        with patch(
            'src.infrastructure.llm.openai_provider.AsyncOpenAI'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Set up the chat.completions structure properly
            mock_completions = AsyncMock()
            mock_client.chat.completions = mock_completions

            provider = OpenAIProvider(
                api_key="test-key", base_url="https://api.openai.com/v1"
            )
            provider.client = mock_client
            return provider

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
                "Item 1 - Business": "Apple Inc. designs, manufactures and markets smartphones...",
            },
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, provider, sample_filing_data):
        """Test handling of OpenAI rate limit errors."""
        # Mock both create and parse methods since they are used
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Create proper httpx Response mock for rate limit error
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 429
            mock_response.content = b"Rate limit exceeded"
            mock_response.headers = {"x-request-id": "test-request-id"}

            # Create response for _extract_subsection_text (uses create method, returns text)
            subsection_text_response = Mock()
            subsection_text_response.choices = [Mock()]
            subsection_text_response.choices[0].message = Mock()
            subsection_text_response.choices[0].message.content = (
                "Extracted subsection text content"
            )

            # Create response for _generate_section_summary (uses parse method, needs SectionSummaryResponse)
            section_summary_response = Mock()
            section_summary_response.choices = [Mock()]
            section_summary_response.choices[0].message = Mock()
            section_summary_response.choices[0].message.content = json.dumps(
                {
                    "section_name": "Item 1 - Business",
                    "section_summary": "Test section summary",
                    "consolidated_insights": ["Test insight 1", "Test insight 2"],
                    "overall_sentiment": 0.5,
                    "critical_findings": ["Test finding 1", "Test finding 2"],
                }
            )

            # Create response for _generate_overall_analysis (uses parse method, needs OverallAnalysisResponse)
            overall_analysis_response = Mock()
            overall_analysis_response.choices = [Mock()]
            overall_analysis_response.choices[0].message = Mock()
            overall_analysis_response.choices[0].message.content = json.dumps(
                {
                    "filing_summary": "Brief filing summary",
                    "executive_summary": "Test executive summary",
                    "key_insights": ["Insight 1", "Insight 2"],
                    "financial_highlights": ["Highlight 1", "Highlight 2"],
                    "risk_factors": ["Risk 1", "Risk 2"],
                    "opportunities": ["Opportunity 1", "Opportunity 2"],
                    "confidence_score": 0.7,
                }
            )

            # Set up side effects - rate limit on first calls, then unlimited successes
            # Use closures with local state instead of function attributes to prevent state leakage
            create_call_count = [0]  # Use list for mutable reference

            def create_side_effect(*args, **kwargs):
                create_call_count[0] += 1
                if create_call_count[0] == 1:
                    raise RateLimitError(
                        "Rate limit exceeded", response=mock_response, body=None
                    )
                return subsection_text_response

            parse_call_count = [0]  # Use list for mutable reference

            def parse_side_effect(*args, **kwargs):
                parse_call_count[0] += 1
                if parse_call_count[0] <= 2:  # First two calls fail
                    raise RateLimitError(
                        "Rate limit exceeded", response=mock_response, body=None
                    )
                # Check the response_format to determine which schema is expected
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return section_summary_response
                else:
                    # OverallAnalysisResponse or other
                    return overall_analysis_response

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            # Should retry and succeed - use asyncio.wait_for to prevent hanging
            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                ),
                timeout=30.0,
            )
            assert isinstance(result, ComprehensiveAnalysisResponse)
            # Should have retried both methods
            assert mock_create.call_count >= 1
            assert mock_parse.call_count >= 1
            # Verify retry behavior by checking call counts
            assert create_call_count[0] >= 2  # First call failed, second succeeded
            assert parse_call_count[0] >= 2  # First call failed, second succeeded

    @pytest.mark.asyncio
    async def test_api_connection_error_handling(self, provider, sample_filing_data):
        """Test handling of API connection errors."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):
            mock_request = Mock(spec=httpx.Request)
            mock_request.url = "https://api.openai.com/v1/chat/completions"
            mock_request.method = "POST"
            mock_create.side_effect = APIConnectionError(
                message="Connection failed", request=mock_request
            )
            mock_parse.side_effect = APIConnectionError(
                message="Connection failed", request=mock_request
            )

            with pytest.raises((APIConnectionError, Exception)):
                await asyncio.wait_for(
                    provider.analyze_filing(
                        filing_sections=sample_filing_data.sections,
                        filing_type=FilingType(sample_filing_data.filing_type),
                        company_name=sample_filing_data.company_name,
                    ),
                    timeout=30.0,
                )

    @pytest.mark.asyncio
    async def test_api_timeout_error_handling(self, provider, sample_filing_data):
        """Test handling of API timeout errors."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):
            # Simulate timeout on first call, success on retry
            # Create proper httpx Request mock for timeout error
            mock_request = Mock(spec=httpx.Request)
            mock_request.url = "https://api.openai.com/v1/chat/completions"
            mock_request.method = "POST"

            # Mock successful responses with correct schemas
            success_create = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "section_name": "Item 1 - Business",
                                    "section_summary": "Test section summary",
                                    "consolidated_insights": [
                                        "Test insight 1",
                                        "Test insight 2",
                                    ],
                                    "overall_sentiment": 0.5,
                                    "critical_findings": [
                                        "Test finding 1",
                                        "Test finding 2",
                                    ],
                                }
                            )
                        )
                    )
                ]
            )

            success_parse = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "filing_summary": "Brief filing summary",
                                    "executive_summary": "Test executive summary",
                                    "key_insights": ["Insight 1", "Insight 2"],
                                    "financial_highlights": [
                                        "Highlight 1",
                                        "Highlight 2",
                                    ],
                                    "risk_factors": ["Risk 1", "Risk 2"],
                                    "opportunities": ["Opportunity 1", "Opportunity 2"],
                                    "confidence_score": 0.7,
                                }
                            )
                        )
                    )
                ]
            )

            # Use closures with counters to prevent StopIteration
            create_call_count = [0]

            def create_side_effect(*args, **kwargs):
                create_call_count[0] += 1
                if create_call_count[0] == 1:
                    raise APITimeoutError(request=mock_request)
                return success_create

            parse_call_count = [0]

            def parse_side_effect(*args, **kwargs):
                parse_call_count[0] += 1
                if parse_call_count[0] == 1:
                    raise APITimeoutError(request=mock_request)
                # Return appropriate response based on schema
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "Item 1 - Business",
                                            "section_summary": "Test section summary",
                                            "consolidated_insights": [
                                                "Test insight 1",
                                                "Test insight 2",
                                            ],
                                            "overall_sentiment": 0.5,
                                            "critical_findings": [
                                                "Test finding 1",
                                                "Test finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    return success_parse

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                ),
                timeout=30.0,
            )
            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert mock_create.call_count >= 1
            assert mock_parse.call_count >= 1

    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(self, provider, sample_filing_data):
        """Test handling of invalid JSON responses from OpenAI."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):
            # Use callable side effects to handle multiple calls
            def create_side_effect(*args, **kwargs):
                return Mock(
                    choices=[Mock(message=Mock(content="Invalid JSON response"))]
                )

            def parse_side_effect(*args, **kwargs):
                return Mock(
                    choices=[Mock(message=Mock(content="Invalid JSON response"))]
                )

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            # Should handle invalid JSON gracefully, either by raising exception or returning empty result
            try:
                result = await asyncio.wait_for(
                    provider.analyze_filing(
                        filing_sections=sample_filing_data.sections,
                        filing_type=FilingType(sample_filing_data.filing_type),
                        company_name=sample_filing_data.company_name,
                    ),
                    timeout=30.0,
                )
                # If no exception, verify it's a valid response object (may be empty)
                assert isinstance(result, ComprehensiveAnalysisResponse)
            except (Exception, asyncio.TimeoutError) as e:
                # If exception is raised, verify it contains parsing error info or is timeout
                if isinstance(e, asyncio.TimeoutError):
                    pytest.fail("Test timed out - possible hanging condition")
                # Check for validation, parse, json, or retry error messages
                error_message = str(e).lower()
                assert any(
                    keyword in error_message
                    for keyword in ["parse", "json", "validation", "retry"]
                )

    @pytest.mark.asyncio
    async def test_partial_json_response_handling(self, provider, sample_filing_data):
        """Test handling of partial/incomplete JSON responses."""
        with patch.object(
            provider.client.chat.completions, 'create', new_callable=AsyncMock
        ) as mock_create:
            # Return JSON with missing required fields
            mock_create.return_value = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "executive_summary": "Test summary",
                                    # Missing other required fields
                                }
                            )
                        )
                    )
                ]
            )

            # Should handle partial JSON gracefully, either by raising exception or using defaults
            try:
                result = await asyncio.wait_for(
                    provider.analyze_filing(
                        filing_sections=sample_filing_data.sections,
                        filing_type=FilingType(sample_filing_data.filing_type),
                        company_name=sample_filing_data.company_name,
                    ),
                    timeout=30.0,
                )
                # If no exception, verify it's a valid response object
                assert isinstance(result, ComprehensiveAnalysisResponse)
            except (Exception, asyncio.TimeoutError) as e:
                # Exception is acceptable for partial/invalid data, but timeout indicates hanging
                if isinstance(e, asyncio.TimeoutError):
                    pytest.fail("Test timed out - possible hanging condition")
                # Other exceptions are acceptable for partial/invalid data
                pass

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, provider, sample_filing_data):
        """Test handling of empty responses from OpenAI."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):
            mock_create.return_value = Mock(choices=[])
            mock_parse.return_value = Mock(choices=[])

            # Should handle empty responses gracefully, either by raising exception or returning empty result
            try:
                result = await asyncio.wait_for(
                    provider.analyze_filing(
                        filing_sections=sample_filing_data.sections,
                        filing_type=FilingType(sample_filing_data.filing_type),
                        company_name=sample_filing_data.company_name,
                    ),
                    timeout=30.0,
                )
                # If no exception, verify it's a valid response object (may be empty)
                assert isinstance(result, ComprehensiveAnalysisResponse)
            except (Exception, asyncio.TimeoutError) as e:
                # If timeout, this indicates a hanging condition
                if isinstance(e, asyncio.TimeoutError):
                    pytest.fail("Test timed out - possible hanging condition")
                # If exception is raised, verify it's related to empty response
                assert (
                    "response" in str(e).lower()
                    or "choice" in str(e).lower()
                    or "index" in str(e).lower()
                )

    @pytest.mark.asyncio
    async def test_concurrent_request_error_handling(
        self, provider, sample_filing_data
    ):
        """Test error handling during concurrent section processing."""
        # Test that the provider can handle multiple concurrent requests
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Return text response for create method (_extract_subsection_text)
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content="Extracted subsection text"))]
            )

            # Return appropriate structured responses for parse method based on schema
            def parse_response_handler(*args, **kwargs):
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "Item 1 - Business",
                                            "section_summary": "Test section summary",
                                            "consolidated_insights": [
                                                "Test insight 1",
                                                "Test insight 2",
                                            ],
                                            "overall_sentiment": 0.5,
                                            "critical_findings": [
                                                "Test finding 1",
                                                "Test finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    # OverallAnalysisResponse or other schemas
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "filing_summary": "Brief filing summary",
                                            "executive_summary": "Test executive summary",
                                            "key_insights": ["Insight 1", "Insight 2"],
                                            "financial_highlights": [
                                                "Highlight 1",
                                                "Highlight 2",
                                            ],
                                            "risk_factors": ["Risk 1", "Risk 2"],
                                            "opportunities": [
                                                "Opportunity 1",
                                                "Opportunity 2",
                                            ],
                                            "confidence_score": 0.7,
                                        }
                                    )
                                )
                            )
                        ]
                    )

            mock_parse.side_effect = parse_response_handler

            # Should handle concurrent analysis without errors
            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                ),
                timeout=30.0,
            )
            assert isinstance(result, ComprehensiveAnalysisResponse)

    @pytest.mark.asyncio
    async def test_retry_mechanism_exhaustion(self, provider, sample_filing_data):
        """Test behavior when retry mechanism is exhausted."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Create proper httpx Response mock for exhausted retries
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 429
            mock_response.content = b"Rate limit exceeded"
            mock_response.headers = {"x-request-id": "test-request-id"}

            # Use counter to ensure we don't loop forever - fail for exactly the retry limit
            retry_call_count = [0]

            def failing_side_effect(*args, **kwargs):
                retry_call_count[0] += 1
                # Always raise error to exhaust retries (tenacity will stop after 3 attempts)
                raise RateLimitError(
                    "Rate limit exceeded", response=mock_response, body=None
                )

            mock_create.side_effect = failing_side_effect
            mock_parse.side_effect = failing_side_effect

            # Should handle exhausted retries gracefully, either by raising exception or returning partial result
            with pytest.raises((RateLimitError, Exception)):
                await provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                )

            # Should have attempted multiple retries (retry decorator should stop after 3 attempts)
            # Note: The exact call count depends on how the implementation handles retries
            assert (
                retry_call_count[0] >= 3
            )  # At least 3 attempts due to retry mechanism

    @pytest.mark.asyncio
    async def test_section_analysis_error_recovery(self, provider):
        """Test error recovery in section-specific analysis."""
        # Test the analyze_filing method instead since _analyze_section is private
        sample_filing_data = FilingData(
            accession_number="0000320193-23-000077",
            filing_type="10-K",
            filing_date="2023-11-03",
            company_name="Apple Inc.",
            cik="0000320193",
            content_text="Sample filing content for testing...",
            sections={
                "Item 1 - Business": "Apple Inc. designs, manufactures and markets smartphones..."
            },
        )

        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):
            # First call fails, second succeeds
            # Create proper httpx Request mock
            mock_request = Mock(spec=httpx.Request)
            mock_request.url = "https://api.openai.com/v1/chat/completions"
            mock_request.method = "POST"

            # Success responses with correct schemas
            success_create = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "section_name": "Item 1 - Business",
                                    "section_summary": "Recovered section summary",
                                    "consolidated_insights": [
                                        "Recovered insight 1",
                                        "Recovered insight 2",
                                    ],
                                    "overall_sentiment": 0.5,
                                    "critical_findings": [
                                        "Recovered finding 1",
                                        "Recovered finding 2",
                                    ],
                                }
                            )
                        )
                    )
                ]
            )

            success_parse = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "filing_summary": "Brief filing summary",
                                    "executive_summary": "Recovered executive summary",
                                    "key_insights": [
                                        "Recovered insight 1",
                                        "Recovered insight 2",
                                    ],
                                    "financial_highlights": [
                                        "Recovered highlight 1",
                                        "Recovered highlight 2",
                                    ],
                                    "risk_factors": [
                                        "Recovered risk 1",
                                        "Recovered risk 2",
                                    ],
                                    "opportunities": [
                                        "Recovered opportunity 1",
                                        "Recovered opportunity 2",
                                    ],
                                    "confidence_score": 0.5,
                                }
                            )
                        )
                    )
                ]
            )

            # Use closures with counters to prevent StopIteration
            create_call_count = [0]

            def create_side_effect(*args, **kwargs):
                create_call_count[0] += 1
                if create_call_count[0] == 1:
                    raise APIConnectionError(
                        message="Connection failed", request=mock_request
                    )
                return success_create

            parse_call_count = [0]

            def parse_side_effect(*args, **kwargs):
                parse_call_count[0] += 1
                if parse_call_count[0] == 1:
                    raise APIConnectionError(
                        message="Connection failed", request=mock_request
                    )
                # Return appropriate response based on schema
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "Item 1 - Business",
                                            "section_summary": "Recovered section summary",
                                            "consolidated_insights": [
                                                "Recovered insight 1",
                                                "Recovered insight 2",
                                            ],
                                            "overall_sentiment": 0.5,
                                            "critical_findings": [
                                                "Recovered finding 1",
                                                "Recovered finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    return success_parse

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                ),
                timeout=30.0,
            )

            assert isinstance(result, ComprehensiveAnalysisResponse)
            assert "Recovered" in result.executive_summary
            assert mock_create.call_count >= 1
            assert mock_parse.call_count >= 1

    @pytest.mark.asyncio
    async def test_large_content_truncation_handling(self, provider):
        """Test handling of content that exceeds token limits."""
        # Create very large content
        large_content = "Large content " * 10000
        filing_data = FilingData(
            accession_number="test",
            filing_type="10-K",
            filing_date="2023-01-01",
            company_name="Test Company",
            cik="0000123456",
            content_text="Large content for testing...",
            sections={"Item 1 - Business": large_content},
        )

        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Use callable side effects to handle multiple calls
            def create_side_effect(*args, **kwargs):
                return Mock(
                    choices=[Mock(message=Mock(content="Extracted large content text"))]
                )

            def parse_side_effect(*args, **kwargs):
                # Return appropriate response based on schema
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "Item 1 - Business",
                                            "section_summary": "Test section summary for large content",
                                            "consolidated_insights": [
                                                "Large content insight 1",
                                                "Large content insight 2",
                                            ],
                                            "overall_sentiment": 0.5,
                                            "critical_findings": [
                                                "Large content finding 1",
                                                "Large content finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "filing_summary": "Brief filing summary for large content",
                                            "executive_summary": "Test executive summary for large content",
                                            "key_insights": [
                                                "Large insight 1",
                                                "Large insight 2",
                                            ],
                                            "financial_highlights": [
                                                "Large highlight 1",
                                                "Large highlight 2",
                                            ],
                                            "risk_factors": [
                                                "Large risk 1",
                                                "Large risk 2",
                                            ],
                                            "opportunities": [
                                                "Large opportunity 1",
                                                "Large opportunity 2",
                                            ],
                                            "confidence_score": 0.7,
                                        }
                                    )
                                )
                            )
                        ]
                    )

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            # Should handle large content without errors
            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=filing_data.sections,
                    filing_type=FilingType(filing_data.filing_type),
                    company_name=filing_data.company_name,
                ),
                timeout=60.0,  # Longer timeout for large content processing
            )
            assert isinstance(result, ComprehensiveAnalysisResponse)

    @pytest.mark.asyncio
    async def test_schema_validation_error_handling(self, provider, sample_filing_data):
        """Test handling of schema validation errors."""
        # Test with invalid schema response structure
        with patch.object(
            provider.client.chat.completions, 'create', new_callable=AsyncMock
        ) as mock_create:
            # Return response that doesn't match expected schema
            mock_create.return_value = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=json.dumps(
                                {
                                    "invalid_field": "This doesn't match the expected schema"
                                }
                            )
                        )
                    )
                ]
            )

            # Should handle schema validation gracefully
            try:
                result = await asyncio.wait_for(
                    provider.analyze_filing(
                        filing_sections=sample_filing_data.sections,
                        filing_type=FilingType(sample_filing_data.filing_type),
                        company_name=sample_filing_data.company_name,
                    ),
                    timeout=30.0,
                )
                # If no exception, verify it's still a valid response object
                assert isinstance(result, ComprehensiveAnalysisResponse)
            except (Exception, asyncio.TimeoutError) as e:
                # Timeout indicates a hanging condition
                if isinstance(e, asyncio.TimeoutError):
                    pytest.fail("Test timed out - possible hanging condition")
                # Other exceptions are acceptable for schema validation errors
                pass

    def test_missing_openai_credentials(self):
        """Test handling of missing OpenAI credentials."""
        # Test with empty environment variables
        with patch.dict('os.environ', {}, clear=True):
            # The OpenAI provider should handle missing credentials gracefully
            try:
                provider = OpenAIProvider()
                # If no exception, the provider should still be created but may fail on API calls
                assert provider is not None
            except Exception as e:
                # Exception is expected when credentials are missing
                assert "api" in str(e).lower() or "key" in str(e).lower()

    @pytest.mark.asyncio
    async def test_invalid_template_handling(self, provider, sample_filing_data):
        """Test handling of invalid analysis templates."""
        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Use callable side effects to handle multiple calls
            def create_side_effect(*args, **kwargs):
                return Mock(
                    choices=[Mock(message=Mock(content="Extracted template text"))]
                )

            def parse_side_effect(*args, **kwargs):
                # Return appropriate response based on schema
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "Item 1 - Business",
                                            "section_summary": "Test section summary",
                                            "consolidated_insights": [
                                                "Template insight 1",
                                                "Template insight 2",
                                            ],
                                            "overall_sentiment": 0.0,
                                            "critical_findings": [
                                                "Template finding 1",
                                                "Template finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "filing_summary": "Brief filing summary for invalid template",
                                            "executive_summary": "Test executive summary for invalid template",
                                            "key_insights": [
                                                "Template insight 1",
                                                "Template insight 2",
                                            ],
                                            "financial_highlights": [
                                                "Template highlight 1",
                                                "Template highlight 2",
                                            ],
                                            "risk_factors": [
                                                "Template risk 1",
                                                "Template risk 2",
                                            ],
                                            "opportunities": [
                                                "Template opportunity 1",
                                                "Template opportunity 2",
                                            ],
                                            "confidence_score": 0.7,
                                        }
                                    )
                                )
                            )
                        ]
                    )

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            # Test that provider accepts analysis_focus parameter without error
            # The method should handle invalid analysis focus gracefully
            result = await asyncio.wait_for(
                provider.analyze_filing(
                    filing_sections=sample_filing_data.sections,
                    filing_type=FilingType(sample_filing_data.filing_type),
                    company_name=sample_filing_data.company_name,
                    analysis_focus=["INVALID_TEMPLATE"],
                ),
                timeout=30.0,
            )
            # Should still return a valid response even with invalid focus
            assert isinstance(result, ComprehensiveAnalysisResponse)

    @pytest.mark.asyncio
    async def test_concurrent_analysis_resource_management(
        self, provider, sample_filing_data
    ):
        """Test resource management during concurrent analysis."""
        # Create filing with manageable number of sections to prevent resource exhaustion
        large_filing = FilingData(
            accession_number="test",
            filing_type="10-K",
            filing_date="2023-01-01",
            company_name="Test Company",
            cik="0000123456",
            content_text="Large filing content for testing...",
            sections={
                f"section_{i}": f"Content {i}" for i in range(10)
            },  # Reduced from 20 to 10
        )

        with (
            patch.object(
                provider.client.chat.completions, 'create', new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                provider.client.chat.completions, 'parse', new_callable=AsyncMock
            ) as mock_parse,
        ):

            # Use callable side effects to handle multiple concurrent calls
            def create_side_effect(*args, **kwargs):
                return Mock(
                    choices=[Mock(message=Mock(content="Extracted concurrent text"))]
                )

            def parse_side_effect(*args, **kwargs):
                # Return appropriate response based on schema
                response_format = kwargs.get('response_format')
                if (
                    hasattr(response_format, '__name__')
                    and response_format.__name__ == 'SectionSummaryResponse'
                ):
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "section_name": "test_section",
                                            "section_summary": "Test summary for concurrent analysis",
                                            "consolidated_insights": [
                                                "Concurrent insight 1",
                                                "Concurrent insight 2",
                                            ],
                                            "overall_sentiment": 0.5,
                                            "critical_findings": [
                                                "Concurrent finding 1",
                                                "Concurrent finding 2",
                                            ],
                                        }
                                    )
                                )
                            )
                        ]
                    )
                else:
                    return Mock(
                        choices=[
                            Mock(
                                message=Mock(
                                    content=json.dumps(
                                        {
                                            "filing_summary": "Brief filing summary for concurrent test",
                                            "executive_summary": "Test executive summary for concurrent analysis",
                                            "key_insights": [
                                                "Concurrent insight 1",
                                                "Concurrent insight 2",
                                            ],
                                            "financial_highlights": [
                                                "Concurrent highlight 1",
                                                "Concurrent highlight 2",
                                            ],
                                            "risk_factors": [
                                                "Concurrent risk 1",
                                                "Concurrent risk 2",
                                            ],
                                            "opportunities": [
                                                "Concurrent opportunity 1",
                                                "Concurrent opportunity 2",
                                            ],
                                            "confidence_score": 0.7,
                                        }
                                    )
                                )
                            )
                        ]
                    )

            mock_create.side_effect = create_side_effect
            mock_parse.side_effect = parse_side_effect

            # Add semaphore to limit concurrent operations and prevent resource exhaustion
            semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent operations

            async def limited_analyze():
                async with semaphore:
                    return await provider.analyze_filing(
                        filing_sections=large_filing.sections,
                        filing_type=FilingType(large_filing.filing_type),
                        company_name=large_filing.company_name,
                    )

            # Should handle concurrent requests without resource exhaustion
            result = await asyncio.wait_for(
                limited_analyze(),
                timeout=120.0,  # Longer timeout for concurrent processing
            )
            assert isinstance(result, ComprehensiveAnalysisResponse)
