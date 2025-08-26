"""Comprehensive tests for Analysis entity."""

import uuid
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.entities.analysis import Analysis, AnalysisType


@pytest.mark.unit
class TestAnalysisConstruction:
    """Test Analysis entity construction and parameter handling."""

    def test_create_with_required_parameters(self):
        """Test creating analysis with only required parameters."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert analysis.id == analysis_id
        assert analysis.filing_id == filing_id
        assert analysis.analysis_type == AnalysisType.FILING_ANALYSIS
        assert analysis.created_by == "test-user"
        assert analysis.llm_provider is None
        assert analysis.llm_model is None
        assert analysis.confidence_score is None
        assert analysis.metadata == {}
        assert isinstance(analysis.created_at, datetime)

    def test_create_with_all_parameters(self):
        """Test creating analysis with all parameters specified."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()
        created_at = datetime(2023, 12, 31, 12, 0, 0, tzinfo=UTC)
        metadata = {"model": "gpt-4", "tokens": 1000}

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="api-key-123",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            confidence_score=0.95,
            metadata=metadata,
            created_at=created_at,
        )

        assert analysis.id == analysis_id
        assert analysis.filing_id == filing_id
        assert analysis.analysis_type == AnalysisType.COMPREHENSIVE
        assert analysis.created_by == "api-key-123"
        assert analysis.llm_provider == "openai"
        assert analysis.llm_model == "gpt-4-turbo"
        assert analysis.confidence_score == 0.95
        assert analysis.metadata == metadata
        assert analysis.created_at == created_at

    def test_create_with_none_created_by(self):
        """Test creating analysis with None created_by."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by=None,
        )

        assert analysis.created_by is None

    def test_create_with_none_metadata_defaults_to_empty_dict(self):
        """Test that None metadata defaults to empty dictionary."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=None,
        )

        assert analysis.metadata == {}

    def test_create_with_none_created_at_defaults_to_now(self):
        """Test that None created_at defaults to current time."""
        before = datetime.now(UTC)

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            created_at=None,
        )

        after = datetime.now(UTC)

        assert before <= analysis.created_at <= after

    def test_properties_are_immutable(self):
        """Test that analysis properties are read-only."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        # Properties should not be settable
        with pytest.raises(AttributeError):
            analysis.id = uuid.uuid4()

        with pytest.raises(AttributeError):
            analysis.filing_id = uuid.uuid4()

        with pytest.raises(AttributeError):
            analysis.analysis_type = AnalysisType.CUSTOM_QUERY


@pytest.mark.unit
class TestAnalysisConfidenceScore:
    """Test Analysis confidence score validation and methods."""

    def test_confidence_score_valid_range(self):
        """Test that confidence scores in valid range are accepted."""
        valid_scores = [0.0, 0.1, 0.5, 0.8, 0.95, 1.0]

        for score in valid_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )
            assert analysis.confidence_score == score

    def test_confidence_score_below_zero_raises_error(self):
        """Test that confidence score below 0.0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=-0.1,
            )

    def test_confidence_score_above_one_raises_error(self):
        """Test that confidence score above 1.0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=1.1,
            )

    def test_update_confidence_score_valid(self):
        """Test updating confidence score with valid values."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.5,
        )

        analysis.update_confidence_score(0.9)
        assert analysis.confidence_score == 0.9

        analysis.update_confidence_score(0.0)
        assert analysis.confidence_score == 0.0

        analysis.update_confidence_score(1.0)
        assert analysis.confidence_score == 1.0

    def test_update_confidence_score_invalid_raises_error(self):
        """Test updating confidence score with invalid values raises error."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.5,
        )

        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            analysis.update_confidence_score(-0.1)

        with pytest.raises(
            ValueError, match="Confidence score must be between 0.0 and 1.0"
        ):
            analysis.update_confidence_score(1.1)

        # Original score should remain unchanged
        assert analysis.confidence_score == 0.5

    @given(score=st.floats(min_value=0.0, max_value=1.0))
    def test_confidence_score_property_based(self, score):
        """Property-based test for valid confidence scores."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=score,
        )

        assert analysis.confidence_score == score
        assert 0.0 <= analysis.confidence_score <= 1.0


@pytest.mark.unit
class TestAnalysisBusinessMethods:
    """Test Analysis business logic methods."""

    def test_is_filing_analysis_with_filing_analysis_type(self):
        """Test is_filing_analysis returns True for FILING_ANALYSIS type."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert analysis.is_filing_analysis() is True

    def test_is_filing_analysis_with_comprehensive_type(self):
        """Test is_filing_analysis returns True for COMPREHENSIVE type."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="test-user",
        )

        assert analysis.is_filing_analysis() is True

    def test_is_filing_analysis_with_other_types(self):
        """Test is_filing_analysis returns False for other analysis types."""
        other_types = [
            AnalysisType.CUSTOM_QUERY,
            AnalysisType.COMPARISON,
            AnalysisType.HISTORICAL_TREND,
        ]

        for analysis_type in other_types:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=analysis_type,
                created_by="test-user",
            )

            assert analysis.is_filing_analysis() is False

    def test_is_high_confidence_with_high_scores(self):
        """Test is_high_confidence returns True for scores >= 0.8."""
        high_scores = [0.8, 0.85, 0.9, 0.95, 1.0]

        for score in high_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_high_confidence() is True

    def test_is_high_confidence_with_medium_and_low_scores(self):
        """Test is_high_confidence returns False for scores < 0.8."""
        lower_scores = [0.0, 0.3, 0.5, 0.7, 0.79]

        for score in lower_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_high_confidence() is False

    def test_is_high_confidence_with_none_score(self):
        """Test is_high_confidence returns False when confidence score is None."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=None,
        )

        assert analysis.is_high_confidence() is False

    def test_is_medium_confidence_with_medium_scores(self):
        """Test is_medium_confidence returns True for scores 0.5 <= score < 0.8."""
        medium_scores = [0.5, 0.6, 0.7, 0.75, 0.79]

        for score in medium_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_medium_confidence() is True

    def test_is_medium_confidence_with_high_and_low_scores(self):
        """Test is_medium_confidence returns False for scores outside medium range."""
        non_medium_scores = [0.0, 0.2, 0.4, 0.49, 0.8, 0.9, 1.0]

        for score in non_medium_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_medium_confidence() is False

    def test_is_medium_confidence_with_none_score(self):
        """Test is_medium_confidence returns False when confidence score is None."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=None,
        )

        assert analysis.is_medium_confidence() is False

    def test_is_low_confidence_with_low_scores(self):
        """Test is_low_confidence returns True for scores < 0.5."""
        low_scores = [0.0, 0.1, 0.2, 0.3, 0.4, 0.49]

        for score in low_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_low_confidence() is True

    def test_is_low_confidence_with_medium_and_high_scores(self):
        """Test is_low_confidence returns False for scores >= 0.5."""
        higher_scores = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        for score in higher_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.is_low_confidence() is False

    def test_is_low_confidence_with_none_score(self):
        """Test is_low_confidence returns True when confidence score is None."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=None,
        )

        assert analysis.is_low_confidence() is True

    def test_is_llm_generated_with_provider(self):
        """Test is_llm_generated returns True when LLM provider is specified."""
        providers = ["openai", "anthropic", "google", "custom-provider"]

        for provider in providers:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                llm_provider=provider,
            )

            assert analysis.is_llm_generated() is True

    def test_is_llm_generated_without_provider(self):
        """Test is_llm_generated returns False when LLM provider is None."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            llm_provider=None,
        )

        assert analysis.is_llm_generated() is False

    def test_confidence_classification_consistency(self):
        """Test that confidence classification methods are mutually exclusive."""
        test_scores = [None, 0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0]

        for score in test_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            # Exactly one classification should be True
            classifications = [
                analysis.is_high_confidence(),
                analysis.is_medium_confidence(),
                analysis.is_low_confidence(),
            ]

            assert (
                sum(classifications) == 1
            ), f"Score {score} should have exactly one classification"


@pytest.mark.unit
class TestAnalysisProcessingTime:
    """Test Analysis processing time validation and metadata integration."""

    def test_get_processing_time_when_not_set(self):
        """Test get_processing_time returns None when not set."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert analysis.get_processing_time() is None

    def test_get_processing_time_when_set_in_metadata(self):
        """Test get_processing_time returns value from metadata."""
        processing_time = 123.45

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata={"processing_time_seconds": processing_time},
        )

        assert analysis.get_processing_time() == processing_time

    def test_set_processing_time_valid_values(self):
        """Test setting processing time with valid non-negative values."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        valid_times = [0.0, 0.1, 1.0, 60.5, 3600.0]

        for time_value in valid_times:
            analysis.set_processing_time(time_value)
            assert analysis.get_processing_time() == time_value

    def test_set_processing_time_negative_raises_error(self):
        """Test setting negative processing time raises ValueError."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            analysis.set_processing_time(-1.0)

        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            analysis.set_processing_time(-0.1)

    def test_set_processing_time_updates_metadata(self):
        """Test that setting processing time updates metadata correctly."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata={"existing_key": "existing_value"},
        )

        analysis.set_processing_time(100.5)

        # Should preserve existing metadata
        assert analysis.metadata["existing_key"] == "existing_value"
        # Should add processing time
        assert analysis.metadata["processing_time_seconds"] == 100.5

    @given(time_value=st.floats(min_value=0.0, max_value=86400.0))
    def test_processing_time_property_based(self, time_value):
        """Property-based test for valid processing times."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        analysis.set_processing_time(time_value)
        assert analysis.get_processing_time() == time_value
        assert analysis.get_processing_time() >= 0.0


@pytest.mark.unit
class TestAnalysisMetadata:
    """Test Analysis metadata operations and defensive copying."""

    def test_metadata_defensive_copy(self):
        """Test that metadata property returns a defensive copy."""
        original_metadata = {"key1": "value1", "key2": "value2"}

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=original_metadata,
        )

        # Get metadata copy
        metadata_copy = analysis.metadata

        # Modify the copy
        metadata_copy["key3"] = "value3"
        metadata_copy["key1"] = "modified"

        # Original should be unchanged
        assert analysis.metadata == original_metadata
        assert "key3" not in analysis.metadata
        assert analysis.metadata["key1"] == "value1"

    def test_metadata_with_nested_structures(self):
        """Test metadata with nested dictionaries and lists."""
        nested_metadata = {
            "llm_config": {
                "model": "gpt-4",
                "temperature": 0.1,
                "parameters": ["param1", "param2"],
            },
            "analysis_sections": ["intro", "body", "conclusion"],
            "processing_time_seconds": 150.75,
        }

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=nested_metadata,
        )

        # Should be able to access nested values
        retrieved_metadata = analysis.metadata
        assert retrieved_metadata["llm_config"]["model"] == "gpt-4"
        assert retrieved_metadata["analysis_sections"] == [
            "intro",
            "body",
            "conclusion",
        ]
        assert analysis.get_processing_time() == 150.75

    def test_metadata_special_fields_integration(self):
        """Test that special metadata fields integrate with entity methods."""
        metadata = {
            "processing_time_seconds": 95.5,
            "custom_field": "custom_value",
            "tokens_used": 2500,
        }

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=metadata,
        )

        # Processing time should be accessible via method
        assert analysis.get_processing_time() == 95.5

        # Other fields should be in metadata
        assert analysis.metadata["custom_field"] == "custom_value"
        assert analysis.metadata["tokens_used"] == 2500

    def test_metadata_modification_through_processing_time(self):
        """Test that metadata is modified correctly through processing time methods."""
        initial_metadata = {"initial_key": "initial_value"}

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=initial_metadata.copy(),
        )

        # Set processing time
        analysis.set_processing_time(200.0)

        # Should have both original and new metadata
        expected_metadata = {
            "initial_key": "initial_value",
            "processing_time_seconds": 200.0,
        }
        assert analysis.metadata == expected_metadata


@pytest.mark.unit
class TestAnalysisAPIFormatting:
    """Test Analysis API response formatting methods."""

    def test_to_api_response_without_results(self):
        """Test to_api_response with entity data only."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()
        created_at = datetime(2023, 12, 31, 12, 0, 0, tzinfo=UTC)

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="api-key-123",
            llm_provider="openai",
            llm_model="gpt-4",
            confidence_score=0.9,
            metadata={"custom": "value"},
            created_at=created_at,
        )

        response = analysis.to_api_response()

        expected = {
            "id": str(analysis_id),
            "filing_id": str(filing_id),
            "analysis_type": "filing_analysis",
            "created_by": "api-key-123",
            "created_at": created_at.isoformat(),
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "confidence_score": 0.9,
            "metadata": {"custom": "value", "processing_time_seconds": None},
        }

        assert response == expected

    def test_to_api_response_with_filing_analysis_results(self):
        """Test to_api_response with filing analysis results."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.85,
        )

        results = {
            "filing_summary": "Company showed strong performance",
            "key_insights": ["Insight 1", "Insight 2"],
            "risk_factors": ["Risk 1"],
            "section_analyses": [{"section": "MD&A"}],
        }

        response = analysis.to_api_response(results)

        # Should include all entity fields plus results
        assert response["analysis_type"] == "filing_analysis"
        assert response["confidence_score"] == 0.85
        assert response["filing_summary"] == "Company showed strong performance"
        assert response["key_insights"] == ["Insight 1", "Insight 2"]
        assert response["risk_factors"] == ["Risk 1"]
        assert response["section_analyses"] == [{"section": "MD&A"}]

    def test_to_api_response_with_custom_query_results(self):
        """Test to_api_response with custom query results."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="test-user",
            confidence_score=0.75,
        )

        results = {
            "answer": "Custom analysis result",
            "source_sections": ["10-K Item 1"],
        }

        response = analysis.to_api_response(results)

        # Should include entity fields and results under "results" key
        assert response["analysis_type"] == "custom_query"
        assert response["confidence_score"] == 0.75
        assert response["results"] == results

    def test_to_api_response_with_processing_time(self):
        """Test to_api_response includes processing time in metadata."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        analysis.set_processing_time(125.5)

        response = analysis.to_api_response()

        assert response["metadata"]["processing_time_seconds"] == 125.5

    def test_get_summary_for_api_filing_analysis(self):
        """Test get_summary_for_api for filing analysis."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()
        created_at = datetime(2023, 12, 31, 12, 0, 0, tzinfo=UTC)

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="test-user",
            confidence_score=0.9,
            created_at=created_at,
        )

        results = {
            "filing_summary": "Strong quarterly performance",
            "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
            "risk_factors": ["Risk 1", "Risk 2"],
            "opportunities": ["Opportunity 1"],
            "section_analyses": [{"section": "MD&A"}, {"section": "Item 1"}],
        }

        summary = analysis.get_summary_for_api(results)

        expected = {
            "id": str(analysis_id),
            "filing_id": str(filing_id),
            "analysis_type": "comprehensive",
            "created_at": created_at.isoformat(),
            "confidence_score": 0.9,
            "filing_summary": "Strong quarterly performance",
            "key_insights_count": 3,
            "risk_factors_count": 2,
            "opportunities_count": 1,
            "sections_analyzed": 2,
        }

        assert summary == expected

    def test_get_summary_for_api_custom_query(self):
        """Test get_summary_for_api for custom query analysis."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="test-user",
            confidence_score=0.8,
            created_at=datetime(2023, 12, 31, tzinfo=UTC),
        )

        results = {"summary": "Custom analysis summary", "answer": "Detailed answer"}

        summary = analysis.get_summary_for_api(results)

        # Should include basic fields plus summary
        assert summary["analysis_type"] == "custom_query"
        assert summary["confidence_score"] == 0.8
        assert summary["summary"] == "Custom analysis summary"

    def test_get_summary_for_api_without_results(self):
        """Test get_summary_for_api without results data."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.7,
            created_at=datetime(2023, 12, 31, tzinfo=UTC),
        )

        summary = analysis.get_summary_for_api()

        # Should include only basic entity data
        assert "filing_summary" not in summary
        assert "key_insights_count" not in summary
        assert summary["confidence_score"] == 0.7


@pytest.mark.unit
class TestAnalysisDomainInvariants:
    """Test Analysis domain invariants and constraints."""

    def test_confidence_score_range_invariant(self):
        """Test that confidence score range invariant is enforced."""
        # Valid construction
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.5,
        )

        # Valid updates
        analysis.update_confidence_score(0.0)
        analysis.update_confidence_score(1.0)

        # Invalid updates should fail
        with pytest.raises(ValueError):
            analysis.update_confidence_score(-0.1)

        with pytest.raises(ValueError):
            analysis.update_confidence_score(1.1)

    def test_processing_time_non_negative_invariant(self):
        """Test that processing time non-negative invariant is enforced."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        # Valid processing times
        analysis.set_processing_time(0.0)
        analysis.set_processing_time(100.5)

        # Invalid processing time should fail
        with pytest.raises(ValueError):
            analysis.set_processing_time(-1.0)

    def test_id_immutability_invariant(self):
        """Test that analysis ID cannot be changed after construction."""
        original_id = uuid.uuid4()

        analysis = Analysis(
            id=original_id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        # ID should remain constant
        assert analysis.id == original_id

        # Should not be able to set ID
        with pytest.raises(AttributeError):
            analysis.id = uuid.uuid4()

    def test_analysis_type_immutability_invariant(self):
        """Test that analysis type cannot be changed after construction."""
        original_type = AnalysisType.FILING_ANALYSIS

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=original_type,
            created_by="test-user",
        )

        # Type should remain constant
        assert analysis.analysis_type == original_type

        # Should not be able to set type
        with pytest.raises(AttributeError):
            analysis.analysis_type = AnalysisType.CUSTOM_QUERY


@pytest.mark.unit
class TestAnalysisEquality:
    """Test Analysis equality and hashing based on UUID."""

    def test_equality_same_id(self):
        """Test equality with same UUID."""
        analysis_id = uuid.uuid4()

        analysis1 = Analysis(
            id=analysis_id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
        )

        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="user2",
        )

        assert analysis1 == analysis2
        assert analysis2 == analysis1

    def test_equality_different_ids(self):
        """Test inequality with different UUIDs."""
        analysis1 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        analysis2 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert analysis1 != analysis2
        assert analysis2 != analysis1

    def test_equality_with_non_analysis_objects(self):
        """Test inequality with non-Analysis objects."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert analysis != "not an analysis"
        assert analysis is not None
        assert analysis != []
        assert analysis != {}
        assert analysis != 123
        assert analysis != uuid.uuid4()

    def test_hash_consistency_same_id(self):
        """Test that objects with same ID have same hash."""
        analysis_id = uuid.uuid4()

        analysis1 = Analysis(
            id=analysis_id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
        )

        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="user2",
        )

        assert hash(analysis1) == hash(analysis2)

    def test_hash_different_ids(self):
        """Test that objects with different IDs have different hashes."""
        analysis1 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        analysis2 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        assert hash(analysis1) != hash(analysis2)

    def test_analysis_in_set(self):
        """Test using Analysis objects in sets."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        analysis1a = Analysis(
            id=id1,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
        )
        analysis1b = Analysis(
            id=id1,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="user2",
        )  # Same ID
        analysis2 = Analysis(
            id=id2,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
        )

        analysis_set = {analysis1a, analysis1b, analysis2}

        # Should only have 2 unique analyses (same ID = same analysis)
        assert len(analysis_set) == 2

        # Test membership
        assert (
            Analysis(
                id=id1,
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.COMPARISON,
                created_by="user3",
            )
            in analysis_set
        )
        assert (
            Analysis(
                id=id2,
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.COMPARISON,
                created_by="user3",
            )
            in analysis_set
        )
        assert (
            Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="user1",
            )
            not in analysis_set
        )

    def test_analysis_as_dict_key(self):
        """Test using Analysis objects as dictionary keys."""
        analysis1 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
        )
        analysis2 = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="user2",
        )

        analysis_dict = {analysis1: "Analysis 1 Data", analysis2: "Analysis 2 Data"}

        # Should be able to access with equivalent objects
        equivalent_analysis1 = Analysis(
            id=analysis1.id,
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.COMPARISON,
            created_by="different",
        )
        assert analysis_dict[equivalent_analysis1] == "Analysis 1 Data"


@pytest.mark.unit
class TestAnalysisEdgeCases:
    """Test Analysis edge cases and boundary conditions."""

    def test_boundary_confidence_scores(self):
        """Test boundary confidence score values."""
        # Exact boundaries
        boundary_scores = [0.0, 0.5, 0.8, 1.0]

        for score in boundary_scores:
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=uuid.uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                confidence_score=score,
            )

            assert analysis.confidence_score == score

            # Test classification boundaries
            if score >= 0.8:
                assert analysis.is_high_confidence()
                assert not analysis.is_medium_confidence()
                assert not analysis.is_low_confidence()
            elif score >= 0.5:
                assert not analysis.is_high_confidence()
                assert analysis.is_medium_confidence()
                assert not analysis.is_low_confidence()
            else:
                assert not analysis.is_high_confidence()
                assert not analysis.is_medium_confidence()
                assert analysis.is_low_confidence()

    def test_zero_processing_time(self):
        """Test zero processing time is valid."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        analysis.set_processing_time(0.0)
        assert analysis.get_processing_time() == 0.0

    def test_very_large_processing_time(self):
        """Test very large processing times are handled correctly."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        large_time = 86400.0  # 24 hours in seconds
        analysis.set_processing_time(large_time)
        assert analysis.get_processing_time() == large_time

    def test_empty_string_created_by(self):
        """Test empty string created_by is handled correctly."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="",
        )

        assert analysis.created_by == ""

    def test_very_long_created_by_string(self):
        """Test very long created_by string is handled correctly."""
        long_created_by = "a" * 1000  # Very long string

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=long_created_by,
        )

        assert analysis.created_by == long_created_by

    def test_unicode_in_string_fields(self):
        """Test unicode characters in string fields."""
        unicode_created_by = "用户-测试-🔍"
        unicode_provider = "公司-AI"
        unicode_model = "模型-GPT-4"

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=unicode_created_by,
            llm_provider=unicode_provider,
            llm_model=unicode_model,
        )

        assert analysis.created_by == unicode_created_by
        assert analysis.llm_provider == unicode_provider
        assert analysis.llm_model == unicode_model

    def test_large_metadata_structure(self):
        """Test with large, complex metadata structure."""
        large_metadata = {
            "processing_details": {
                "steps": [f"step_{i}" for i in range(100)],
                "timings": {f"step_{i}": i * 0.1 for i in range(100)},
                "errors": [],
            },
            "llm_details": {
                "model_config": {"temperature": 0.1, "max_tokens": 4000, "top_p": 0.9},
                "prompt_versions": [f"v{i}" for i in range(10)],
            },
            "processing_time_seconds": 300.5,
        }

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            metadata=large_metadata,
        )

        # Should handle large metadata correctly
        assert len(analysis.metadata["processing_details"]["steps"]) == 100
        assert analysis.get_processing_time() == 300.5

    def test_string_representations(self):
        """Test string and repr representations."""
        analysis_id = uuid.uuid4()
        filing_id = uuid.uuid4()
        created_at = datetime(2023, 12, 31, tzinfo=UTC)

        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=0.85,
            created_at=created_at,
        )

        # Test __str__
        str_repr = str(analysis)
        assert "filing_analysis" in str_repr
        assert "0.85" in str_repr
        assert "2023-12-31" in str_repr

        # Test __repr__
        repr_str = repr(analysis)
        assert f"Analysis(id={analysis_id}" in repr_str
        assert f"filing_id={filing_id}" in repr_str
        assert "type=AnalysisType.FILING_ANALYSIS" in repr_str

    def test_analysis_depth_classification(self):
        """Test analysis depth classification for filing analyses."""
        filing_analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
        )

        # Should return "shallow" since no sections are analyzed (results are in storage)
        assert filing_analysis.get_analysis_depth() == "shallow"

        custom_analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="test-user",
        )

        # Custom queries should return "custom"
        assert custom_analysis.get_analysis_depth() == "custom"

    @given(
        confidence=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)),
        processing_time=st.floats(min_value=0.0, max_value=86400.0),
    )
    def test_property_based_analysis_construction(self, confidence, processing_time):
        """Property-based test for analysis construction with various inputs."""
        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=uuid.uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            confidence_score=confidence,
        )

        if processing_time is not None:
            analysis.set_processing_time(processing_time)

        # Invariants should hold
        if confidence is not None:
            assert 0.0 <= analysis.confidence_score <= 1.0
        else:
            assert analysis.confidence_score is None

        if processing_time is not None:
            assert analysis.get_processing_time() >= 0.0
