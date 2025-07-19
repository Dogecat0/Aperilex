"""Tests for Analysis entity."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.analysis import Analysis, AnalysisType


class TestAnalysisType:
    """Test cases for AnalysisType enum."""

    def test_analysis_type_values(self):
        """Test that all analysis types have correct values."""
        assert AnalysisType.FILING_ANALYSIS.value == "filing_analysis"
        assert AnalysisType.CUSTOM_QUERY.value == "custom_query"
        assert AnalysisType.COMPARISON.value == "comparison"
        assert AnalysisType.HISTORICAL_TREND.value == "historical_trend"

    def test_analysis_type_creation(self):
        """Test creating AnalysisType from string."""
        analysis_type = AnalysisType("filing_analysis")
        assert analysis_type == AnalysisType.FILING_ANALYSIS


class TestAnalysis:
    """Test cases for Analysis entity."""

    def test_init_with_required_params(self):
        """Test Analysis initialization with required parameters."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        
        assert analysis.id == analysis_id
        assert analysis.filing_id == filing_id
        assert analysis.analysis_type == analysis_type
        assert analysis.created_by == created_by
        assert analysis.results == {}
        assert analysis.llm_provider is None
        assert analysis.llm_model is None
        assert analysis.confidence_score is None
        assert analysis.metadata == {}
        assert isinstance(analysis.created_at, datetime)

    def test_init_with_all_params(self):
        """Test Analysis initialization with all parameters."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.CUSTOM_QUERY
        results = {"summary": "Test summary", "key_findings": ["Finding 1", "Finding 2"]}
        llm_provider = "openai"
        llm_model = "gpt-4"
        confidence_score = 0.85
        metadata = {"processing_time": 45.2}
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by,
            results=results,
            llm_provider=llm_provider,
            llm_model=llm_model,
            confidence_score=confidence_score,
            metadata=metadata,
            created_at=created_at
        )
        
        assert analysis.results == results
        assert analysis.llm_provider == llm_provider
        assert analysis.llm_model == llm_model
        assert analysis.confidence_score == confidence_score
        assert analysis.metadata == metadata
        assert analysis.created_at == created_at

    def test_init_with_invalid_confidence_score(self):
        """Test Analysis initialization with invalid confidence score."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        # Too low confidence score
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            Analysis(
                id=analysis_id,
                filing_id=filing_id,
                analysis_type=analysis_type,
                created_by=created_by,
                confidence_score=-0.1
            )
        
        # Too high confidence score
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            Analysis(
                id=analysis_id,
                filing_id=filing_id,
                analysis_type=analysis_type,
                created_by=created_by,
                confidence_score=1.1
            )

    def test_confidence_classification(self):
        """Test confidence score classification methods."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        # High confidence
        high_conf = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by,
            confidence_score=0.9
        )
        assert high_conf.is_high_confidence() is True
        assert high_conf.is_medium_confidence() is False
        assert high_conf.is_low_confidence() is False
        
        # Medium confidence
        medium_conf = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by,
            confidence_score=0.6
        )
        assert medium_conf.is_high_confidence() is False
        assert medium_conf.is_medium_confidence() is True
        assert medium_conf.is_low_confidence() is False
        
        # Low confidence
        low_conf = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by,
            confidence_score=0.3
        )
        assert low_conf.is_high_confidence() is False
        assert low_conf.is_medium_confidence() is False
        assert low_conf.is_low_confidence() is True
        
        # No confidence score
        no_conf = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        assert no_conf.is_high_confidence() is False
        assert no_conf.is_medium_confidence() is False
        assert no_conf.is_low_confidence() is True

    def test_get_summary(self):
        """Test getting analysis summary."""
        analysis = self._create_test_analysis()
        
        # No summary
        assert analysis.get_filing_summary() == ""
        
        # With summary
        analysis.update_results({"filing_summary": "This is a test summary"})
        assert analysis.get_filing_summary() == "This is a test summary"

    def test_get_key_findings(self):
        """Test getting key findings."""
        analysis = self._create_test_analysis()
        
        # No findings
        assert analysis.get_key_insights() == []
        
        # With findings
        findings = ["Finding 1", "Finding 2", "Finding 3"]
        analysis.update_results({"key_insights": findings})
        assert analysis.get_key_insights() == findings

    def test_get_risks(self):
        """Test getting risks."""
        analysis = self._create_test_analysis()
        
        # No risks
        assert analysis.get_risk_factors() == []
        
        # With risks
        risks = ["High debt levels", "Market volatility", "Regulatory changes"]
        analysis.update_results({"risk_factors": risks})
        risk_factors = analysis.get_risk_factors()
        assert len(risk_factors) == 3
        assert risk_factors[0] == "High debt levels"
        assert risk_factors[1] == "Market volatility"
        assert risk_factors[2] == "Regulatory changes"

    def test_get_opportunities(self):
        """Test getting opportunities."""
        analysis = self._create_test_analysis()
        
        # No opportunities
        assert analysis.get_opportunities() == []
        
        # With opportunities
        opportunities = ["Market expansion", "Cost reduction", "New partnerships"]
        analysis.update_results({"opportunities": opportunities})
        assert analysis.get_opportunities() == opportunities

    def test_get_metrics(self):
        """Test getting metrics."""
        analysis = self._create_test_analysis()
        
        # No metrics
        assert analysis.get_financial_highlights() == []
        
        # With metrics
        highlights = ["Revenue growth: 15.5%", "Debt ratio: 0.35", "Profit margin: 12.3%"]
        analysis.update_results({"financial_highlights": highlights})
        
        metrics = analysis.get_financial_highlights()
        assert len(metrics) == 3
        assert metrics[0] == "Revenue growth: 15.5%"
        assert metrics[1] == "Debt ratio: 0.35"
        assert metrics[2] == "Profit margin: 12.3%"

    def test_add_insight(self):
        """Test adding insights with update_results."""
        analysis = self._create_test_analysis()
        
        # Simple insight
        analysis.update_results({"key_metric": "Revenue increased 20%"})
        assert analysis.results["key_metric"] == "Revenue increased 20%"
        
        # Structured insight
        structured_insight = {
            "type": "trend",
            "description": "Revenue trending upward",
            "confidence": 0.9
        }
        analysis.update_results({"revenue_trend": structured_insight})
        assert analysis.results["revenue_trend"] == structured_insight

    def test_update_confidence_score(self):
        """Test updating confidence score."""
        analysis = self._create_test_analysis()
        
        # Valid score
        analysis.update_confidence_score(0.75)
        assert analysis.confidence_score == 0.75
        
        # Boundary values
        analysis.update_confidence_score(0.0)
        assert analysis.confidence_score == 0.0
        
        analysis.update_confidence_score(1.0)
        assert analysis.confidence_score == 1.0
        
        # Invalid scores
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            analysis.update_confidence_score(-0.1)
        
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            analysis.update_confidence_score(1.1)

    def test_add_metadata(self):
        """Test adding metadata."""
        analysis = self._create_test_analysis()
        
        # Set processing time using proper method
        analysis.set_processing_time(45.2)
        
        # Update metadata manually for testing
        analysis._metadata["model_version"] = "v1.2.3"
        
        metadata = analysis.metadata
        assert metadata["processing_time_seconds"] == 45.2
        assert metadata["model_version"] == "v1.2.3"

    def test_processing_time_methods(self):
        """Test processing time methods."""
        analysis = self._create_test_analysis()
        
        # No processing time
        assert analysis.get_processing_time() is None
        
        # Set processing time
        analysis.set_processing_time(120.5)
        assert analysis.get_processing_time() == 120.5
        
        # Invalid processing time
        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            analysis.set_processing_time(-5.0)

    def test_is_llm_generated(self):
        """Test LLM generation check."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        # No LLM provider
        analysis = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        assert analysis.is_llm_generated() is False
        
        # With LLM provider
        llm_analysis = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by,
            llm_provider="openai"
        )
        assert llm_analysis.is_llm_generated() is True

    def test_equality(self):
        """Test Analysis equality based on ID."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        analysis1 = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        
        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid4(),  # Different filing ID
            analysis_type=AnalysisType.CUSTOM_QUERY,  # Different type
            created_by=uuid4()  # Different creator
        )
        
        # Same ID should be equal
        assert analysis1 == analysis2
        
        # Different ID should not be equal
        analysis3 = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        assert analysis1 != analysis3
        
        # Different type should not be equal
        assert analysis1 != "analysis"
        assert analysis1 != None

    def test_hash(self):
        """Test Analysis hash based on ID."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FILING_ANALYSIS
        
        analysis1 = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        
        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by=uuid4()
        )
        
        # Same ID should have same hash
        assert hash(analysis1) == hash(analysis2)
        
        # Different ID should have different hash
        analysis3 = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        assert hash(analysis1) != hash(analysis3)
        
        # Test in set
        analysis_set = {analysis1, analysis2, analysis3}
        assert len(analysis_set) == 2  # analysis1 and analysis2 have same ID

    def test_str_representation(self):
        """Test Analysis string representation."""
        analysis = self._create_test_analysis()
        
        # Without confidence score
        str_repr = str(analysis)
        assert "Analysis: filing_analysis" in str_repr
        assert str(analysis.created_at.date()) in str_repr
        
        # With confidence score
        analysis.update_confidence_score(0.85)
        str_repr = str(analysis)
        assert "confidence: 0.85" in str_repr

    def test_repr_representation(self):
        """Test Analysis repr representation."""
        analysis = self._create_test_analysis()
        
        repr_str = repr(analysis)
        assert f"Analysis(id={analysis.id}" in repr_str
        assert f"filing_id={analysis.filing_id}" in repr_str
        assert f"type={analysis.analysis_type}" in repr_str
        assert f"created_at={analysis.created_at}" in repr_str

    def test_results_isolation(self):
        """Test that results property returns a copy."""
        analysis = self._create_test_analysis()
        analysis.update_results({"test_key": "test_value"})
        
        # Get results copy
        results = analysis.results
        results["test_key"] = "modified_value"
        
        # Original results should be unchanged
        assert analysis.results["test_key"] == "test_value"

    def test_metadata_isolation(self):
        """Test that metadata property returns a copy."""
        analysis = self._create_test_analysis()
        analysis._metadata["test_key"] = "test_value"
        
        # Get metadata copy
        metadata = analysis.metadata
        metadata["test_key"] = "modified_value"
        
        # Original metadata should be unchanged
        assert analysis.metadata["test_key"] == "test_value"

    def test_insights_isolation(self):
        """Test that results property returns a copy."""
        analysis = self._create_test_analysis()
        
        # Add simple insight (not nested)
        analysis.update_results({"trend_insight": "Original value"})
        
        # Get results copy
        results = analysis.results
        results["trend_insight"] = "Modified value"
        
        # Original results should be unchanged
        assert analysis.results["trend_insight"] == "Original value"

    def test_comprehensive_analysis_workflow(self):
        """Test a comprehensive analysis workflow."""
        analysis = self._create_test_analysis()
        
        # Add comprehensive results
        analysis.update_results({
            "filing_summary": "Apple Inc. shows strong financial performance",
            "key_insights": [
                "Revenue increased 15% YoY",
                "Profit margins improved",
                "Strong cash position"
            ],
            "financial_highlights": [
                "Revenue growth: 15.2%",
                "Profit margin: 23.1%",
                "Current ratio: 1.1"
            ],
            "risk_factors": [
                "Market saturation",
                "Supply chain disruption"
            ],
            "opportunities": [
                "Services expansion",
                "Emerging markets"
            ]
        })
        
        # Update confidence and metadata
        analysis.update_confidence_score(0.88)
        analysis.set_processing_time(125.5)
        analysis._metadata["model_version"] = "v2.1.0"
        
        # Verify all data is accessible
        assert analysis.get_filing_summary() == "Apple Inc. shows strong financial performance"
        assert len(analysis.get_key_insights()) == 3
        assert len(analysis.get_financial_highlights()) == 3
        assert len(analysis.get_risk_factors()) == 2
        assert len(analysis.get_opportunities()) == 2
        assert analysis.is_high_confidence() is True
        assert analysis.get_processing_time() == 125.5
        assert analysis.is_llm_generated() is True

    def _create_test_analysis(self) -> Analysis:
        """Create a test analysis for use in tests."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="gpt-4"
        )