"""Tests for Analysis entity."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.entities.analysis import Analysis, AnalysisType


class TestAnalysisType:
    """Test cases for AnalysisType enum."""

    def test_analysis_type_values(self):
        """Test that all analysis types have correct values."""
        assert AnalysisType.FINANCIAL_SUMMARY.value == "financial_summary"
        assert AnalysisType.RISK_ANALYSIS.value == "risk_analysis"
        assert AnalysisType.RATIO_ANALYSIS.value == "ratio_analysis"
        assert AnalysisType.TREND_ANALYSIS.value == "trend_analysis"
        assert AnalysisType.PEER_COMPARISON.value == "peer_comparison"
        assert AnalysisType.SENTIMENT_ANALYSIS.value == "sentiment_analysis"
        assert AnalysisType.KEY_METRICS.value == "key_metrics"
        assert AnalysisType.ANOMALY_DETECTION.value == "anomaly_detection"
        assert AnalysisType.CUSTOM.value == "custom"

    def test_analysis_type_creation(self):
        """Test creating AnalysisType from string."""
        analysis_type = AnalysisType("financial_summary")
        assert analysis_type == AnalysisType.FINANCIAL_SUMMARY


class TestAnalysis:
    """Test cases for Analysis entity."""

    def test_init_with_required_params(self):
        """Test Analysis initialization with required parameters."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
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
        assert analysis.insights == []
        assert isinstance(analysis.created_at, datetime)

    def test_init_with_all_params(self):
        """Test Analysis initialization with all parameters."""
        analysis_id = uuid4()
        filing_id = uuid4()
        created_by = uuid4()
        analysis_type = AnalysisType.RISK_ANALYSIS
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
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
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
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
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
        assert analysis.get_summary() == ""
        
        # With summary
        analysis.add_insight("summary", "This is a test summary")
        assert analysis.get_summary() == "This is a test summary"

    def test_get_key_findings(self):
        """Test getting key findings."""
        analysis = self._create_test_analysis()
        
        # No findings
        assert analysis.get_key_findings() == []
        
        # With findings
        findings = ["Finding 1", "Finding 2", "Finding 3"]
        analysis.add_insight("key_findings", findings)
        assert analysis.get_key_findings() == findings

    def test_get_risks(self):
        """Test getting risks."""
        analysis = self._create_test_analysis()
        
        # No risks
        assert analysis.get_risks() == []
        
        # With risks
        analysis.add_risk("High debt levels", "high", "medium", "significant")
        risks = analysis.get_risks()
        assert len(risks) == 1
        assert risks[0]["description"] == "High debt levels"
        assert risks[0]["severity"] == "high"
        assert risks[0]["probability"] == "medium"
        assert risks[0]["impact"] == "significant"

    def test_get_opportunities(self):
        """Test getting opportunities."""
        analysis = self._create_test_analysis()
        
        # No opportunities
        assert analysis.get_opportunities() == []
        
        # With opportunities
        opportunities = [
            {"description": "Market expansion", "potential": "high"},
            {"description": "Cost reduction", "potential": "medium"}
        ]
        analysis.add_insight("opportunities", opportunities)
        assert analysis.get_opportunities() == opportunities

    def test_get_metrics(self):
        """Test getting metrics."""
        analysis = self._create_test_analysis()
        
        # No metrics
        assert analysis.get_metrics() == {}
        
        # With metrics
        analysis.add_metric("revenue_growth", 15.5, "%")
        analysis.add_metric("debt_ratio", 0.35)
        
        metrics = analysis.get_metrics()
        assert metrics["revenue_growth"]["value"] == 15.5
        assert metrics["revenue_growth"]["unit"] == "%"
        assert metrics["debt_ratio"]["value"] == 0.35
        assert "unit" not in metrics["debt_ratio"]

    def test_add_insight(self):
        """Test adding insights."""
        analysis = self._create_test_analysis()
        
        # Simple insight
        analysis.add_insight("key_metric", "Revenue increased 20%")
        assert analysis.results["key_metric"] == "Revenue increased 20%"
        
        # Structured insight
        structured_insight = {
            "type": "trend",
            "description": "Revenue trending upward",
            "confidence": 0.9
        }
        analysis.add_insight("revenue_trend", structured_insight)
        assert analysis.results["revenue_trend"] == structured_insight
        
        # Should be added to insights list
        insights = analysis.insights
        assert len(insights) == 1
        assert insights[0]["key"] == "revenue_trend"
        assert insights[0]["type"] == "trend"
        assert insights[0]["description"] == "Revenue trending upward"

    def test_add_insight_with_invalid_key(self):
        """Test adding insight with invalid key."""
        analysis = self._create_test_analysis()
        
        # Empty key
        with pytest.raises(ValueError, match="Insight key cannot be empty"):
            analysis.add_insight("", "value")
        
        # Whitespace only key
        with pytest.raises(ValueError, match="Insight key cannot be empty"):
            analysis.add_insight("   ", "value")

    def test_add_metric(self):
        """Test adding metrics."""
        analysis = self._create_test_analysis()
        
        # Metric with unit
        analysis.add_metric("profit_margin", 12.5, "%")
        
        metrics = analysis.get_metrics()
        assert metrics["profit_margin"]["value"] == 12.5
        assert metrics["profit_margin"]["unit"] == "%"
        
        # Metric without unit
        analysis.add_metric("pe_ratio", 18.5)
        
        metrics = analysis.get_metrics()
        assert metrics["pe_ratio"]["value"] == 18.5
        assert "unit" not in metrics["pe_ratio"]

    def test_add_metric_with_invalid_name(self):
        """Test adding metric with invalid name."""
        analysis = self._create_test_analysis()
        
        # Empty name
        with pytest.raises(ValueError, match="Metric name cannot be empty"):
            analysis.add_metric("", 10.5)
        
        # Whitespace only name
        with pytest.raises(ValueError, match="Metric name cannot be empty"):
            analysis.add_metric("   ", 10.5)

    def test_add_risk(self):
        """Test adding risks."""
        analysis = self._create_test_analysis()
        
        # Risk with all fields
        analysis.add_risk("Market volatility", "high", "high", "significant")
        
        risks = analysis.get_risks()
        assert len(risks) == 1
        risk = risks[0]
        assert risk["description"] == "Market volatility"
        assert risk["severity"] == "high"
        assert risk["probability"] == "high"
        assert risk["impact"] == "significant"
        assert "id" in risk
        assert "timestamp" in risk
        
        # Risk with minimal fields
        analysis.add_risk("Currency fluctuation", "medium")
        
        risks = analysis.get_risks()
        assert len(risks) == 2
        risk = risks[1]
        assert risk["description"] == "Currency fluctuation"
        assert risk["severity"] == "medium"
        assert "probability" not in risk
        assert "impact" not in risk

    def test_add_risk_with_invalid_description(self):
        """Test adding risk with invalid description."""
        analysis = self._create_test_analysis()
        
        # Empty description
        with pytest.raises(ValueError, match="Risk description cannot be empty"):
            analysis.add_risk("", "high")
        
        # Whitespace only description
        with pytest.raises(ValueError, match="Risk description cannot be empty"):
            analysis.add_risk("   ", "high")

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
        
        analysis.add_metadata("processing_time", 45.2)
        analysis.add_metadata("model_version", "v1.2.3")
        
        metadata = analysis.metadata
        assert metadata["processing_time"] == 45.2
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
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
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
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
        analysis1 = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        
        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid4(),  # Different filing ID
            analysis_type=AnalysisType.RISK_ANALYSIS,  # Different type
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
        analysis_type = AnalysisType.FINANCIAL_SUMMARY
        
        analysis1 = Analysis(
            id=analysis_id,
            filing_id=filing_id,
            analysis_type=analysis_type,
            created_by=created_by
        )
        
        analysis2 = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.RISK_ANALYSIS,
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
        assert "Analysis: financial_summary" in str_repr
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
        analysis.add_insight("test_key", "test_value")
        
        # Get results copy
        results = analysis.results
        results["test_key"] = "modified_value"
        
        # Original results should be unchanged
        assert analysis.results["test_key"] == "test_value"

    def test_metadata_isolation(self):
        """Test that metadata property returns a copy."""
        analysis = self._create_test_analysis()
        analysis.add_metadata("test_key", "test_value")
        
        # Get metadata copy
        metadata = analysis.metadata
        metadata["test_key"] = "modified_value"
        
        # Original metadata should be unchanged
        assert analysis.metadata["test_key"] == "test_value"

    def test_insights_isolation(self):
        """Test that insights property returns a copy."""
        analysis = self._create_test_analysis()
        
        # Add structured insight
        structured_insight = {
            "type": "trend",
            "description": "Test trend"
        }
        analysis.add_insight("trend_insight", structured_insight)
        
        # Get insights copy
        insights = analysis.insights
        insights[0]["description"] = "Modified description"
        
        # Original insights should be unchanged
        assert analysis.insights[0]["description"] == "Test trend"

    def test_comprehensive_analysis_workflow(self):
        """Test a comprehensive analysis workflow."""
        analysis = self._create_test_analysis()
        
        # Add summary
        analysis.add_insight("summary", "Apple Inc. shows strong financial performance")
        
        # Add key findings
        analysis.add_insight("key_findings", [
            "Revenue increased 15% YoY",
            "Profit margins improved",
            "Strong cash position"
        ])
        
        # Add metrics
        analysis.add_metric("revenue_growth", 15.2, "%")
        analysis.add_metric("profit_margin", 23.1, "%")
        analysis.add_metric("current_ratio", 1.1)
        
        # Add risks
        analysis.add_risk("Market saturation", "medium", "high", "moderate")
        analysis.add_risk("Supply chain disruption", "high", "medium", "significant")
        
        # Add opportunities
        analysis.add_insight("opportunities", [
            {"description": "Services expansion", "potential": "high"},
            {"description": "Emerging markets", "potential": "medium"}
        ])
        
        # Update confidence and metadata
        analysis.update_confidence_score(0.88)
        analysis.set_processing_time(125.5)
        analysis.add_metadata("model_version", "v2.1.0")
        
        # Verify all data is accessible
        assert analysis.get_summary() == "Apple Inc. shows strong financial performance"
        assert len(analysis.get_key_findings()) == 3
        assert len(analysis.get_metrics()) == 3
        assert len(analysis.get_risks()) == 2
        assert len(analysis.get_opportunities()) == 2
        assert analysis.is_high_confidence() is True
        assert analysis.get_processing_time() == 125.5
        assert analysis.is_llm_generated() is True

    def _create_test_analysis(self) -> Analysis:
        """Create a test analysis for use in tests."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FINANCIAL_SUMMARY,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="gpt-4"
        )