"""Integration tests for AnalysisOrchestrator progress callback functionality."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus


class TestAnalysisOrchestratorProgressCallbacks:
    """Integration tests for AnalysisOrchestrator progress callback functionality."""

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_filing_repository(self) -> AsyncMock:
        """Mock FilingRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_edgar_service(self) -> MagicMock:
        """Mock EdgarService."""
        return MagicMock()

    @pytest.fixture
    def mock_llm_provider(self) -> AsyncMock:
        """Mock LLM Provider."""
        return AsyncMock()

    @pytest.fixture
    def mock_template_service(self) -> MagicMock:
        """Mock AnalysisTemplateService."""
        service = MagicMock()
        service.map_template_to_schemas.return_value = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]
        return service

    @pytest.fixture
    def orchestrator(
        self,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_template_service: MagicMock,
    ) -> AnalysisOrchestrator:
        """Create AnalysisOrchestrator with mocked dependencies."""
        return AnalysisOrchestrator(
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            edgar_service=mock_edgar_service,
            llm_provider=mock_llm_provider,
            template_service=mock_template_service,
        )

    @pytest.fixture
    def sample_command(self) -> AnalyzeFilingCommand:
        """Create sample AnalyzeFilingCommand."""
        return AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            user_id="test_user",
        )

    @pytest.fixture
    def mock_filing(self) -> Filing:
        """Mock Filing entity."""
        return Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("1234567890-12-123456"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
        )

    @pytest.fixture
    def mock_analysis(self) -> Analysis:
        """Mock Analysis entity."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test_user",
            llm_provider="openai",
            llm_model="gpt-4",
            confidence_score=0.85,
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_with_progress_callback(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Integration test for orchestrate_filing_analysis with progress callback."""
        # Setup mocks for successful flow
        mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
            company_name="Test Company",
            filing_type="10-K",
            accession_number="1234567890-12-123456",
            ticker="TEST",
        )
        mock_filing_repository.get_by_accession_number.return_value = mock_filing
        mock_analysis_repository.create.return_value = mock_analysis
        mock_analysis_repository.get_by_id.return_value = mock_analysis
        mock_analysis_repository.update.return_value = mock_analysis

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"analysis": "result"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content"
        }

        # Track progress callback calls
        progress_calls = []

        def progress_callback(progress: float, message: str) -> None:
            progress_calls.append((progress, message))

        # Execute orchestration with progress callback
        result = await orchestrator.orchestrate_filing_analysis(
            sample_command, progress_callback=progress_callback
        )

        # Verify result
        assert result == mock_analysis

        # Verify progress callback was called with expected stages
        assert len(progress_calls) >= 4  # At least 4 progress updates expected

        # Verify progress sequence (should be increasing)
        progress_values = [call[0] for call in progress_calls]
        assert progress_values == sorted(
            progress_values
        )  # Should be monotonically increasing

        # Verify specific progress stages
        expected_progress_stages = [0.1, 0.2, 0.4, 0.8, 1.0]
        actual_progress_values = [call[0] for call in progress_calls]

        for expected_stage in expected_progress_stages:
            assert any(
                abs(actual - expected_stage) < 0.01 for actual in actual_progress_values
            ), f"Expected progress stage {expected_stage} not found in {actual_progress_values}"

        # Verify progress messages are meaningful
        progress_messages = [call[1] for call in progress_calls]
        assert any("started" in msg.lower() for msg in progress_messages)
        assert any("template" in msg.lower() for msg in progress_messages)
        assert any(
            "section" in msg.lower() or "extract" in msg.lower()
            for msg in progress_messages
        )
        assert any(
            "completed" in msg.lower() or "analysis" in msg.lower()
            for msg in progress_messages
        )

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_without_progress_callback(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Integration test for orchestrate_filing_analysis without progress callback."""
        # Setup mocks for successful flow
        mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
            company_name="Test Company",
            filing_type="10-K",
            accession_number="1234567890-12-123456",
            ticker="TEST",
        )
        mock_filing_repository.get_by_accession_number.return_value = mock_filing
        mock_analysis_repository.create.return_value = mock_analysis
        mock_analysis_repository.get_by_id.return_value = mock_analysis
        mock_analysis_repository.update.return_value = mock_analysis

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"analysis": "result"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content"
        }

        # Execute orchestration WITHOUT progress callback (backward compatibility)
        result = await orchestrator.orchestrate_filing_analysis(sample_command)

        # Verify result - should work the same as before
        assert result == mock_analysis

        # Verify all the expected service calls were made
        mock_edgar_service.get_filing_by_accession.assert_called_once()
        mock_filing_repository.get_by_accession_number.assert_called_once()
        mock_analysis_repository.create.assert_called_once()
        mock_llm_provider.analyze_filing.assert_called_once()

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Test that progress callback errors don't break orchestration."""
        # Setup mocks for successful flow
        mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
            company_name="Test Company",
            filing_type="10-K",
            accession_number="1234567890-12-123456",
            ticker="TEST",
        )
        mock_filing_repository.get_by_accession_number.return_value = mock_filing
        mock_analysis_repository.create.return_value = mock_analysis
        mock_analysis_repository.get_by_id.return_value = mock_analysis
        mock_analysis_repository.update.return_value = mock_analysis

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"analysis": "result"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content"
        }

        # Create a progress callback that throws an error
        def failing_progress_callback(progress: float, message: str) -> None:
            if progress > 0.5:  # Fail partway through
                raise Exception("Progress callback failed")

        # Execute orchestration - should complete despite callback error
        result = await orchestrator.orchestrate_filing_analysis(
            sample_command, progress_callback=failing_progress_callback
        )

        # Verify orchestration completed successfully despite callback error
        assert result == mock_analysis

    @pytest.mark.asyncio
    async def test_progress_callback_with_different_templates(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_template_service: MagicMock,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Test progress callback with different analysis templates."""
        templates_to_test = [
            AnalysisTemplate.COMPREHENSIVE,
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        for template in templates_to_test:
            # Setup mocks for each iteration
            mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
                company_name="Test Company",
                filing_type="10-K",
                accession_number="1234567890-12-123456",
                ticker="TEST",
            )
            mock_filing_repository.get_by_accession_number.return_value = mock_filing
            mock_analysis_repository.create.return_value = mock_analysis
            mock_analysis_repository.get_by_id.return_value = mock_analysis
            mock_analysis_repository.update.return_value = mock_analysis

            # Mock LLM response
            mock_llm_response = MagicMock()
            mock_llm_response.model_dump.return_value = {"analysis": "result"}
            mock_llm_response.confidence_score = 0.85
            mock_llm_provider.analyze_filing.return_value = mock_llm_response

            # Mock section extraction
            mock_edgar_service.extract_filing_sections.return_value = {
                "Item 1 - Business": "Business content"
            }

            # Create command with specific template
            command = AnalyzeFilingCommand(
                company_cik=CIK("1234567890"),
                accession_number=AccessionNumber("1234567890-12-123456"),
                analysis_template=template,
                user_id="test_user",
            )

            # Track progress for this template
            template_progress_calls = []

            def template_progress_callback(progress: float, message: str) -> None:
                template_progress_calls.append((progress, message, template.value))

            # Execute orchestration
            result = await orchestrator.orchestrate_filing_analysis(
                command, progress_callback=template_progress_callback
            )

            # Verify result
            assert result == mock_analysis

            # Verify progress callbacks were made for this template
            assert len(template_progress_calls) > 0

            # Reset mocks for next iteration
            mock_edgar_service.reset_mock()
            mock_filing_repository.reset_mock()
            mock_analysis_repository.reset_mock()
            mock_llm_provider.reset_mock()

    @pytest.mark.asyncio
    async def test_progress_callback_with_orchestration_failure(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Test progress callback behavior when orchestration fails."""
        # Setup mocks for partial success then failure
        mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
            company_name="Test Company",
            filing_type="10-K",
            accession_number="1234567890-12-123456",
            ticker="TEST",
        )
        mock_filing_repository.get_by_accession_number.return_value = mock_filing
        mock_analysis_repository.create.return_value = mock_analysis
        mock_analysis_repository.get_by_id.return_value = mock_analysis

        # Mock LLM to fail
        mock_llm_provider.analyze_filing.side_effect = Exception(
            "LLM processing failed"
        )

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content"
        }

        # Track progress calls
        progress_calls = []

        def progress_callback(progress: float, message: str) -> None:
            progress_calls.append((progress, message))

        # Execute orchestration - should fail but still call progress callback
        with pytest.raises(Exception, match="LLM processing failed"):
            await orchestrator.orchestrate_filing_analysis(
                sample_command, progress_callback=progress_callback
            )

        # Verify progress callback was called for the stages that completed
        assert len(progress_calls) > 0

        # Should have initial progress calls before failure
        progress_values = [call[0] for call in progress_calls]
        assert max(progress_values) < 1.0  # Should not reach 100% due to failure

    @pytest.mark.asyncio
    async def test_progress_callback_integration_with_realistic_workflow(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_template_service: MagicMock,
        mock_filing: Filing,
        mock_analysis: Analysis,
    ) -> None:
        """Integration test with realistic workflow and progress tracking."""
        # Create realistic command (Apple Inc. 10-K)
        realistic_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000064"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            user_id="financial_analyst",
        )

        # Setup comprehensive mocks
        mock_edgar_service.get_filing_by_accession.return_value = MagicMock(
            company_name="Apple Inc.",
            filing_type="10-K",
            accession_number="0000320193-23-000064",
            ticker="AAPL",
        )
        mock_filing_repository.get_by_accession_number.return_value = mock_filing
        mock_analysis_repository.create.return_value = mock_analysis
        mock_analysis_repository.get_by_id.return_value = mock_analysis
        mock_analysis_repository.update.return_value = mock_analysis

        # Mock comprehensive template mapping
        mock_template_service.map_template_to_schemas.return_value = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "FinancialAnalysisSection",
            "MarketAnalysisSection",
            "CompetitiveAnalysisSection",
            "ESGAnalysisSection",
        ]

        # Mock realistic LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {
            "business_analysis": {
                "revenue_trends": "Strong growth in services segment",
                "competitive_position": "Market leader with sustainable moat",
            },
            "risk_analysis": {
                "primary_risks": ["Regulatory changes", "Supply chain disruption"],
                "risk_assessment": "Moderate overall risk profile",
            },
            "financial_analysis": {
                "profitability": "High margins maintained",
                "liquidity": "Strong balance sheet",
            },
        }
        mock_llm_response.confidence_score = 0.94
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock comprehensive section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Apple designs, manufactures and markets...",
            "Item 1A - Risk Factors": "Investment in Apple involves risks...",
            "Item 7 - Management's Discussion": "Fiscal 2023 highlights...",
            "Item 8 - Financial Statements": "Consolidated statements...",
        }

        # Create comprehensive progress tracking
        detailed_progress_log = []

        def detailed_progress_callback(progress: float, message: str) -> None:
            detailed_progress_log.append(
                {
                    "timestamp": datetime.now(UTC),
                    "progress": progress,
                    "message": message,
                    "stage": _determine_stage_from_progress(progress),
                }
            )

        def _determine_stage_from_progress(progress: float) -> str:
            if progress <= 0.1:
                return "validation"
            elif progress <= 0.3:
                return "template_resolution"
            elif progress <= 0.5:
                return "section_extraction"
            elif progress <= 0.9:
                return "llm_processing"
            else:
                return "completion"

        # Execute comprehensive analysis with detailed progress tracking
        result = await orchestrator.orchestrate_filing_analysis(
            realistic_command, progress_callback=detailed_progress_callback
        )

        # Verify successful completion
        assert result == mock_analysis

        # Verify comprehensive progress tracking
        assert len(detailed_progress_log) >= 5  # All major stages covered

        # Verify all stages were covered
        stages_covered = {entry["stage"] for entry in detailed_progress_log}
        expected_stages = {
            "validation",
            "template_resolution",
            "section_extraction",
            "llm_processing",
            "completion",
        }
        assert expected_stages.issubset(stages_covered)

        # Verify progress is monotonically increasing
        progress_values = [entry["progress"] for entry in detailed_progress_log]
        assert progress_values == sorted(progress_values)

        # Verify final progress is 100%
        assert progress_values[-1] == 1.0

        # Verify meaningful progress messages
        messages = [entry["message"] for entry in detailed_progress_log]
        assert any(
            "started" in msg.lower() or "validat" in msg.lower() for msg in messages
        )
        assert any(
            "template" in msg.lower() or "resolv" in msg.lower() for msg in messages
        )
        assert any(
            "extract" in msg.lower() or "section" in msg.lower() for msg in messages
        )
        assert any(
            "analys" in msg.lower() or "process" in msg.lower() for msg in messages
        )
        assert any(
            "complet" in msg.lower() or "finish" in msg.lower() for msg in messages
        )
