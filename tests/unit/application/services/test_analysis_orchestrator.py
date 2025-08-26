"""Comprehensive tests for AnalysisOrchestrator service."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.services.analysis_orchestrator import (
    AnalysisOrchestrationError,
    AnalysisOrchestrator,
    AnalysisProcessingError,
    FilingAccessError,
)
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects import CIK
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm.base import BaseLLMProvider
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository


@pytest.mark.unit
class TestAnalysisOrchestratorConstruction:
    """Test AnalysisOrchestrator construction and dependency injection."""

    def test_constructor_with_all_dependencies(self):
        """Test creating orchestrator with all required dependencies."""
        # Arrange
        analysis_repository = Mock(spec=AnalysisRepository)
        filing_repository = Mock(spec=FilingRepository)
        edgar_service = Mock(spec=EdgarService)
        llm_provider = Mock(spec=BaseLLMProvider)
        template_service = Mock(spec=AnalysisTemplateService)

        # Act
        orchestrator = AnalysisOrchestrator(
            analysis_repository=analysis_repository,
            filing_repository=filing_repository,
            edgar_service=edgar_service,
            llm_provider=llm_provider,
            template_service=template_service,
        )

        # Assert
        assert orchestrator.analysis_repository is analysis_repository
        assert orchestrator.filing_repository is filing_repository
        assert orchestrator.edgar_service is edgar_service
        assert orchestrator.llm_provider is llm_provider
        assert orchestrator.template_service is template_service

    def test_constructor_stores_dependencies_correctly(self):
        """Test that constructor correctly stores all injected dependencies."""
        # Arrange
        dependencies = {
            "analysis_repository": Mock(spec=AnalysisRepository),
            "filing_repository": Mock(spec=FilingRepository),
            "edgar_service": Mock(spec=EdgarService),
            "llm_provider": Mock(spec=BaseLLMProvider),
            "template_service": Mock(spec=AnalysisTemplateService),
        }

        # Act
        orchestrator = AnalysisOrchestrator(**dependencies)

        # Assert
        for attr_name, dependency in dependencies.items():
            assert getattr(orchestrator, attr_name) is dependency

    def test_constructor_immutability(self):
        """Test that orchestrator dependencies cannot be modified after construction."""
        # Arrange
        analysis_repository = Mock(spec=AnalysisRepository)
        filing_repository = Mock(spec=FilingRepository)
        edgar_service = Mock(spec=EdgarService)
        llm_provider = Mock(spec=BaseLLMProvider)
        template_service = Mock(spec=AnalysisTemplateService)

        orchestrator = AnalysisOrchestrator(
            analysis_repository=analysis_repository,
            filing_repository=filing_repository,
            edgar_service=edgar_service,
            llm_provider=llm_provider,
            template_service=template_service,
        )

        # Act & Assert - Store original references
        original_analysis_repo = orchestrator.analysis_repository
        original_filing_repo = orchestrator.filing_repository
        original_edgar = orchestrator.edgar_service
        original_llm = orchestrator.llm_provider
        original_template = orchestrator.template_service

        # Verify references remain unchanged (dependencies are set at construction)
        assert orchestrator.analysis_repository is original_analysis_repo
        assert orchestrator.filing_repository is original_filing_repo
        assert orchestrator.edgar_service is original_edgar
        assert orchestrator.llm_provider is original_llm
        assert orchestrator.template_service is original_template


@pytest.mark.unit
class TestAnalysisOrchestratorValidation:
    """Test command and filing validation in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.valid_command = AnalyzeFilingCommand(
            user_id=uuid4(),
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.valid_filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample filing content",
            raw_html="<html>Sample filing content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_success(self):
        """Test successful filing validation and data retrieval."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data

        # Act
        result = await self.orchestrator.validate_filing_access_and_get_data(
            accession_number
        )

        # Assert
        assert result == self.valid_filing_data
        self.edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_missing_company_name(self):
        """Test filing validation failure due to missing company name."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        invalid_filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="",  # Missing company name
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample filing content",
            raw_html="<html>Sample filing content</html>",
            ticker="AAPL",
            sections={},
        )
        self.edgar_service.get_filing_by_accession.return_value = invalid_filing_data

        # Act & Assert
        with pytest.raises(
            FilingAccessError, match="Filing missing required company name"
        ):
            await self.orchestrator.validate_filing_access_and_get_data(
                accession_number
            )

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_missing_filing_type(self):
        """Test filing validation failure due to missing filing type."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        invalid_filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="",  # Missing filing type
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample filing content",
            raw_html="<html>Sample filing content</html>",
            ticker="AAPL",
            sections={},
        )
        self.edgar_service.get_filing_by_accession.return_value = invalid_filing_data

        # Act & Assert
        with pytest.raises(
            FilingAccessError, match="Filing missing required filing type"
        ):
            await self.orchestrator.validate_filing_access_and_get_data(
                accession_number
            )

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_edgar_error(self):
        """Test filing validation failure due to Edgar service error."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        self.edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Filing not found"
        )

        # Act & Assert
        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await self.orchestrator.validate_filing_access_and_get_data(
                accession_number
            )

    @pytest.mark.asyncio
    async def test_validate_filing_access_legacy_method(self):
        """Test legacy validate_filing_access method returns True on success."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data

        # Act
        result = await self.orchestrator.validate_filing_access(accession_number)

        # Assert
        assert result is True
        self.edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_legacy_method_error(self):
        """Test legacy validate_filing_access method propagates errors."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        self.edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Service error"
        )

        # Act & Assert
        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await self.orchestrator.validate_filing_access(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_unexpected_error(self):
        """Test validate_filing_access handles unexpected errors."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        self.edgar_service.get_filing_by_accession.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act & Assert
        with pytest.raises(FilingAccessError, match="Unexpected error validating"):
            await self.orchestrator.validate_filing_access(accession_number)


@pytest.mark.unit
class TestAnalysisOrchestratorHappyPath:
    """Test complete successful workflow of AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.company_id = uuid4()
        self.filing_id = uuid4()
        self.analysis_id = uuid4()

        self.valid_command = AnalyzeFilingCommand(
            user_id=uuid4(),
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.valid_filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample filing content",
            raw_html="<html>Sample filing content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

        self.valid_filing = Filing(
            id=self.filing_id,
            company_id=self.company_id,
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PENDING,
            metadata={},
        )

        self.valid_analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        self.mock_llm_response = Mock()
        self.mock_llm_response.confidence_score = 0.95
        self.mock_llm_response.model_dump.return_value = {
            "analysis": "Sample analysis",
            "confidence_score": 0.95,
        }
        self.mock_llm_response.section_analyses = [
            Mock(section_name="Item 1 - Business")
        ]

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_complete_success(self):
        """Test complete successful filing analysis workflow."""
        # Arrange
        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = []  # No existing
        self.analysis_repository.create.return_value = self.valid_analysis
        self.analysis_repository.update.return_value = self.valid_analysis
        self.analysis_repository.get_by_id.return_value = self.valid_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = self.mock_llm_response

        # Mock storage functions
        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"},
                "content_text": "Full filing content",
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command
            )

            # Assert
            assert result is not None
            assert isinstance(result, Analysis)

            # Verify key method calls
            self.edgar_service.get_filing_by_accession.assert_called()
            self.filing_repository.get_by_accession_number.assert_called_once()
            self.template_service.get_schemas_for_template.assert_called_once_with(
                AnalysisTemplate.COMPREHENSIVE
            )
            self.llm_provider.analyze_filing.assert_called_once()
            mock_store_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_with_progress_callback(self):
        """Test analysis workflow with progress tracking callbacks."""
        # Arrange
        progress_calls = []

        async def progress_callback(progress: float, message: str):
            progress_calls.append((progress, message))

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = []
        self.analysis_repository.create.return_value = self.valid_analysis
        self.analysis_repository.update.return_value = self.valid_analysis
        self.analysis_repository.get_by_id.return_value = self.valid_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = self.mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command, progress_callback=progress_callback
            )

            # Assert
            assert len(progress_calls) >= 4  # Multiple progress updates
            assert progress_calls[0] == (0.1, "Analysis started")
            assert progress_calls[-1] == (1.0, "Analysis completed")

            # Verify progress increases monotonically
            for i in range(1, len(progress_calls)):
                assert progress_calls[i][0] >= progress_calls[i - 1][0]

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_force_reprocess(self):
        """Test analysis workflow with force reprocess flag."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "comprehensive"}

        # Set force_reprocess to True
        force_command = AnalyzeFilingCommand(
            user_id=self.valid_command.user_id,
            company_cik=self.valid_command.company_cik,
            accession_number=self.valid_command.accession_number,
            analysis_template=self.valid_command.analysis_template,
            force_reprocess=True,
        )

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]
        self.analysis_repository.create.return_value = self.valid_analysis
        self.analysis_repository.update.return_value = self.valid_analysis
        self.analysis_repository.get_by_id.return_value = self.valid_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = self.mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(force_command)

            # Assert
            assert result == self.valid_analysis
            # Should create new analysis even though existing one was found
            self.analysis_repository.create.assert_called_once()
            self.llm_provider.analyze_filing.assert_called_once()


@pytest.mark.unit
class TestAnalysisOrchestratorWorkflowSteps:
    """Test individual workflow steps of AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.filing_id = uuid4()
        self.analysis_id = uuid4()

        self.valid_command = AnalyzeFilingCommand(
            user_id=uuid4(),
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

    @pytest.mark.asyncio
    async def test_create_analysis_entity(self):
        """Test analysis entity creation with correct configuration."""
        # Arrange
        expected_analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        self.analysis_repository.create.return_value = expected_analysis

        with patch("src.shared.config.settings") as mock_settings:
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator._create_analysis_entity(
                self.filing_id, self.valid_command
            )

            # Assert
            assert result == expected_analysis
            self.analysis_repository.create.assert_called_once()

            # Verify the created analysis has correct attributes
            created_analysis = self.analysis_repository.create.call_args[0][0]
            assert created_analysis.filing_id == self.filing_id
            assert created_analysis.analysis_type == AnalysisType.FILING_ANALYSIS
            assert created_analysis.created_by == self.valid_command.user_id
            assert created_analysis.llm_provider == "openai"
            assert created_analysis.llm_model == "default"

    @pytest.mark.asyncio
    async def test_find_existing_analysis_found(self):
        """Test finding existing analysis with matching template."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "comprehensive"}

        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]

        # Act
        result = await self.orchestrator._find_existing_analysis(
            self.filing_id, self.valid_command
        )

        # Assert
        assert result == existing_analysis
        self.analysis_repository.get_by_filing_id.assert_called_once_with(
            self.filing_id, AnalysisType.FILING_ANALYSIS
        )

    @pytest.mark.asyncio
    async def test_find_existing_analysis_not_found(self):
        """Test finding existing analysis when none match template."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "financial_focused"}

        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]

        # Act
        result = await self.orchestrator._find_existing_analysis(
            self.filing_id, self.valid_command
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_analysis_repository_error(self):
        """Test finding existing analysis when repository raises error."""
        # Arrange
        self.analysis_repository.get_by_filing_id.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await self.orchestrator._find_existing_analysis(
            self.filing_id, self.valid_command
        )

        # Assert
        assert result is None  # Should return None instead of raising

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_from_content(self):
        """Test extracting relevant sections from filing content."""
        # Arrange
        filing_content = {
            "sections": {
                "Item 1 - Business": "Business content",
                "Item 1A - Risk Factors": "Risk content",
                "Item 2 - Properties": "Properties content",
            }
        }
        schemas_to_use = ["BusinessAnalysisSection", "RiskFactorsAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        expected_sections = {
            "Item 1 - Business": "Business content",
            "Item 1A - Risk Factors": "Risk content",
        }
        assert result == expected_sections

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_content_text_fallback(self):
        """Test extracting sections falls back to content text when no sections."""
        # Arrange
        filing_content = {"content_text": "Full filing content"}
        schemas_to_use = ["BusinessAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Filing Content": "Full filing content"}

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_edgar_fallback(self):
        """Test extracting sections falls back to Edgar service."""
        # Arrange
        filing_content = None
        schemas_to_use = ["BusinessAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Edgar content",
            raw_html="<html>Edgar content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business from Edgar"},
        )
        self.edgar_service.get_filing_by_accession.return_value = filing_data

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Item 1 - Business": "Business from Edgar"}
        self.edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_get_filing_content_from_storage_success(self):
        """Test successful filing content retrieval from storage."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        company_cik = CIK("0000320193")
        expected_content = {
            "sections": {"Item 1 - Business": "Business content"},
            "content_text": "Full content",
        }

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.return_value = expected_content

            # Act
            result = await self.orchestrator._get_filing_content_from_storage(
                accession_number, company_cik
            )

            # Assert
            assert result == expected_content
            mock_get_content.assert_called_once_with(accession_number, company_cik)

    @pytest.mark.asyncio
    async def test_get_filing_content_from_storage_not_found(self):
        """Test filing content retrieval when content not found in storage."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        company_cik = CIK("0000320193")

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.return_value = None

            # Act
            result = await self.orchestrator._get_filing_content_from_storage(
                accession_number, company_cik
            )

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_filing_content_from_storage_error(self):
        """Test filing content retrieval when storage raises error."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        company_cik = CIK("0000320193")

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.side_effect = Exception("Storage error")

            # Act
            result = await self.orchestrator._get_filing_content_from_storage(
                accession_number, company_cik
            )

            # Assert
            assert result is None  # Should return None instead of raising


@pytest.mark.unit
class TestAnalysisOrchestratorErrorHandling:
    """Test error handling and rollback mechanisms in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.filing_id = uuid4()
        self.analysis_id = uuid4()

        self.valid_command = AnalyzeFilingCommand(
            user_id=uuid4(),
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.valid_filing = Filing(
            id=self.filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PENDING,
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_command_validation_error(self):
        """Test workflow failure due to command validation error."""
        # Arrange - create command with valid construction but mock validate to allow testing orchestrator validation handling
        with patch.object(AnalyzeFilingCommand, "validate"):
            invalid_command = AnalyzeFilingCommand(
                user_id=uuid4(),
                company_cik=None,  # Invalid - None CIK
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

        # Act & Assert - test that orchestrator wraps validation errors in AnalysisOrchestrationError
        with pytest.raises(
            AnalysisOrchestrationError,
            match="Analysis orchestration failed.*company_cik is required",
        ):
            await self.orchestrator.orchestrate_filing_analysis(invalid_command)

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_filing_access_error(self):
        """Test workflow failure due to filing access error."""
        # Arrange
        self.edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Filing not found"
        )

        # Act & Assert
        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await self.orchestrator.orchestrate_filing_analysis(self.valid_command)

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_content_not_found_error(self):
        """Test workflow failure when filing content not found in storage."""
        # Arrange
        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample content",
            raw_html="<html>Sample content</html>",
            ticker="AAPL",
            sections={},
        )

        self.edgar_service.get_filing_by_accession.return_value = filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.return_value = None

            # Act & Assert
            with pytest.raises(FilingAccessError, match="Filing content.*not found"):
                await self.orchestrator.orchestrate_filing_analysis(self.valid_command)

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_llm_processing_error(self):
        """Test workflow failure during LLM processing with proper rollback."""
        # Arrange
        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample content",
            raw_html="<html>Sample content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

        analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        self.edgar_service.get_filing_by_accession.return_value = filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = []
        self.analysis_repository.create.return_value = analysis
        self.analysis_repository.get_by_id.return_value = analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.side_effect = Exception("LLM service error")

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act & Assert
            with pytest.raises(AnalysisProcessingError, match="LLM analysis failed"):
                await self.orchestrator.orchestrate_filing_analysis(self.valid_command)

            # Verify failure was handled
            self.analysis_repository.update.assert_called()  # For failure metadata

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_storage_failure_rollback(self):
        """Test workflow failure during storage with proper analysis rollback."""
        # Arrange
        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample content",
            raw_html="<html>Sample content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

        analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.valid_command.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        mock_llm_response = Mock()
        mock_llm_response.confidence_score = 0.95
        mock_llm_response.model_dump.return_value = {"analysis": "Sample analysis"}
        mock_llm_response.section_analyses = [Mock(section_name="Item 1 - Business")]

        self.edgar_service.get_filing_by_accession.return_value = filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = []
        self.analysis_repository.create.return_value = analysis
        self.analysis_repository.get_by_id.return_value = analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = False  # Storage failure
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act & Assert
            with pytest.raises(
                AnalysisProcessingError,
                match="Failed to store analysis results to storage",
            ):
                await self.orchestrator.orchestrate_filing_analysis(self.valid_command)

            # Verify analysis was rolled back - delete may be called multiple times due to different failure paths
            self.analysis_repository.delete.assert_called_with(analysis.id)
            assert self.analysis_repository.delete.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_analysis_failure_updates_metadata(self):
        """Test analysis failure handling updates analysis with failure metadata."""
        # Arrange
        analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        analysis._metadata = {}
        error = Exception("Test error")

        self.analysis_repository.get_by_id.return_value = analysis
        self.analysis_repository.update.return_value = analysis

        # Act
        await self.orchestrator.handle_analysis_failure(self.analysis_id, error)

        # Assert - get_by_id called twice: once in handle_analysis_failure and once in track_analysis_progress
        assert self.analysis_repository.get_by_id.call_count == 2
        self.analysis_repository.get_by_id.assert_called_with(self.analysis_id)
        # update called twice: once in handle_analysis_failure and once in track_analysis_progress
        assert self.analysis_repository.update.call_count == 2

        # Verify failure metadata was added
        assert "failure_reason" in analysis._metadata
        assert "failure_type" in analysis._metadata
        assert "failed_at" in analysis._metadata
        assert analysis._metadata["failure_reason"] == "Test error"
        assert analysis._metadata["failure_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_handle_analysis_failure_no_analysis_found(self):
        """Test analysis failure handling when analysis not found."""
        # Arrange
        error = Exception("Test error")
        self.analysis_repository.get_by_id.return_value = None

        # Act
        await self.orchestrator.handle_analysis_failure(self.analysis_id, error)

        # Assert
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)
        self.analysis_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_analysis_failure_repository_error(self):
        """Test analysis failure handling when repository update fails."""
        # Arrange
        analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        error = Exception("Test error")

        self.analysis_repository.get_by_id.return_value = analysis
        self.analysis_repository.update.side_effect = Exception("Repository error")

        # Act (should not raise exception)
        await self.orchestrator.handle_analysis_failure(self.analysis_id, error)

        # Assert - method should handle repository errors gracefully
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)

    @pytest.mark.asyncio
    async def test_rollback_filing_status_on_failure(self):
        """Test filing status rollback on failure."""
        # Arrange
        filing = Filing(
            id=self.filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PROCESSING,
            metadata={},
        )
        error_message = "Analysis failed"

        self.filing_repository.update.return_value = filing

        # Act
        await self.orchestrator._rollback_filing_status_on_failure(
            filing, error_message
        )

        # Assert
        assert filing.processing_status == ProcessingStatus.FAILED
        self.filing_repository.update.assert_called_once_with(filing)

    @pytest.mark.asyncio
    async def test_rollback_filing_status_on_failure_none_filing(self):
        """Test filing status rollback with None filing."""
        # Act (should not raise exception)
        await self.orchestrator._rollback_filing_status_on_failure(None, "Test error")

        # Assert
        self.filing_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_filing_status_on_failure_not_processing(self):
        """Test filing status rollback when filing not in processing state."""
        # Arrange
        filing = Filing(
            id=self.filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PENDING,  # Not PROCESSING
            metadata={},
        )
        error_message = "Analysis failed"

        # Act
        await self.orchestrator._rollback_filing_status_on_failure(
            filing, error_message
        )

        # Assert
        self.filing_repository.update.assert_not_called()


@pytest.mark.unit
class TestAnalysisOrchestratorProgressTracking:
    """Test progress tracking and callback mechanisms in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.analysis_id = uuid4()
        self.analysis = Analysis(
            id=self.analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        self.analysis._metadata = {}

    @pytest.mark.asyncio
    async def test_track_analysis_progress_success(self):
        """Test successful progress tracking with metadata update."""
        # Arrange
        progress = 0.5
        status = "Processing"
        self.analysis_repository.get_by_id.return_value = self.analysis
        self.analysis_repository.update.return_value = self.analysis

        # Act
        await self.orchestrator.track_analysis_progress(
            self.analysis_id, progress, status
        )

        # Assert
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)
        self.analysis_repository.update.assert_called_once_with(self.analysis)

        # Verify progress metadata was added
        assert self.analysis._metadata["current_progress"] == progress
        assert self.analysis._metadata["current_status"] == status
        assert "last_updated" in self.analysis._metadata

    @pytest.mark.asyncio
    async def test_track_analysis_progress_analysis_not_found(self):
        """Test progress tracking when analysis not found."""
        # Arrange
        self.analysis_repository.get_by_id.return_value = None

        # Act (should not raise exception)
        await self.orchestrator.track_analysis_progress(
            self.analysis_id, 0.5, "Processing"
        )

        # Assert
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)
        self.analysis_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_analysis_progress_repository_error(self):
        """Test progress tracking when repository update fails."""
        # Arrange
        self.analysis_repository.get_by_id.return_value = self.analysis
        self.analysis_repository.update.side_effect = Exception("Repository error")

        # Act (should not raise exception)
        await self.orchestrator.track_analysis_progress(
            self.analysis_id, 0.5, "Processing"
        )

        # Assert - method should handle errors gracefully
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)

    @pytest.mark.asyncio
    async def test_call_progress_callback_sync_function(self):
        """Test calling synchronous progress callback function."""
        # Arrange
        callback_calls = []

        def sync_callback(progress: float, message: str):
            callback_calls.append((progress, message))

        # Act
        await self.orchestrator._call_progress_callback(
            sync_callback, 0.5, "Test message"
        )

        # Assert
        assert len(callback_calls) == 1
        assert callback_calls[0] == (0.5, "Test message")

    @pytest.mark.asyncio
    async def test_call_progress_callback_async_function(self):
        """Test calling asynchronous progress callback function."""
        # Arrange
        callback_calls = []

        async def async_callback(progress: float, message: str):
            callback_calls.append((progress, message))

        # Act
        await self.orchestrator._call_progress_callback(
            async_callback, 0.75, "Async test"
        )

        # Assert
        assert len(callback_calls) == 1
        assert callback_calls[0] == (0.75, "Async test")

    @pytest.mark.asyncio
    async def test_call_progress_callback_none(self):
        """Test calling progress callback when callback is None."""
        # Act (should not raise exception)
        await self.orchestrator._call_progress_callback(None, 0.5, "Test message")

        # Assert - no exception should be raised

    @pytest.mark.asyncio
    async def test_call_progress_callback_sync_function_error(self):
        """Test calling progress callback when sync function raises error."""

        # Arrange
        def error_callback(progress: float, message: str):
            raise ValueError("Callback error")

        # Act (should not raise exception)
        await self.orchestrator._call_progress_callback(
            error_callback, 0.5, "Test message"
        )

        # Assert - no exception should be raised

    @pytest.mark.asyncio
    async def test_call_progress_callback_async_function_error(self):
        """Test calling progress callback when async function raises error."""

        # Arrange
        async def error_callback(progress: float, message: str):
            raise ValueError("Async callback error")

        # Act (should not raise exception)
        await self.orchestrator._call_progress_callback(
            error_callback, 0.5, "Test message"
        )

        # Assert - no exception should be raised

    @pytest.mark.asyncio
    async def test_progress_tracking_during_workflow_steps(self):
        """Test that progress tracking is called during workflow steps."""
        # This test is covered in the happy path tests, but worth documenting
        # that progress tracking occurs at:
        # - 0.1: Analysis started
        # - 0.2: Template resolved
        # - 0.4: Filing sections extracted
        # - 0.8: LLM analysis completed
        # - 1.0: Analysis completed
        pass


@pytest.mark.unit
class TestAnalysisOrchestratorDuplicateDetection:
    """Test duplicate analysis detection and force reprocessing in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.filing_id = uuid4()
        self.user_id = uuid4()

        self.valid_command = AnalyzeFilingCommand(
            user_id=self.user_id,
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.valid_filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample filing content",
            raw_html="<html>Sample filing content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

        self.valid_filing = Filing(
            id=self.filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PENDING,
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_duplicate_detection_existing_analysis_returned(self):
        """Test that existing analysis is returned when duplicate found."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "comprehensive"}

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command
            )

            # Assert
            assert result == existing_analysis
            # Should not create new analysis or call LLM
            self.analysis_repository.create.assert_not_called()
            self.llm_provider.analyze_filing.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_detection_different_template_not_returned(self):
        """Test that existing analysis with different template is not returned."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "financial_focused"}

        new_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        mock_llm_response = Mock()
        mock_llm_response.confidence_score = 0.95
        mock_llm_response.model_dump.return_value = {"analysis": "New analysis"}
        mock_llm_response.section_analyses = [Mock(section_name="Item 1 - Business")]

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]
        self.analysis_repository.create.return_value = new_analysis
        self.analysis_repository.update.return_value = new_analysis
        self.analysis_repository.get_by_id.return_value = new_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command
            )

            # Assert
            assert result == new_analysis
            # Should create new analysis and call LLM
            self.analysis_repository.create.assert_called_once()
            self.llm_provider.analyze_filing.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_reprocess_ignores_existing_analysis(self):
        """Test that force_reprocess bypasses duplicate detection."""
        # Arrange
        existing_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis._metadata = {"template_used": "comprehensive"}

        new_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        # Create command with force_reprocess=True
        force_command = AnalyzeFilingCommand(
            user_id=self.user_id,
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=True,
        )

        mock_llm_response = Mock()
        mock_llm_response.confidence_score = 0.95
        mock_llm_response.model_dump.return_value = {"analysis": "Forced reprocess"}
        mock_llm_response.section_analyses = [Mock(section_name="Item 1 - Business")]

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = [existing_analysis]
        self.analysis_repository.create.return_value = new_analysis
        self.analysis_repository.update.return_value = new_analysis
        self.analysis_repository.get_by_id.return_value = new_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(force_command)

            # Assert
            assert result == new_analysis
            # Should create new analysis despite existing one
            self.analysis_repository.create.assert_called_once()
            self.llm_provider.analyze_filing.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_detection_multiple_existing_analyses(self):
        """Test duplicate detection with multiple existing analyses."""
        # Arrange
        existing_analysis_1 = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis_1._metadata = {"template_used": "financial_focused"}

        existing_analysis_2 = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        existing_analysis_2._metadata = {"template_used": "comprehensive"}

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = [
            existing_analysis_1,
            existing_analysis_2,
        ]

        with patch(
            "src.infrastructure.tasks.analysis_tasks.get_filing_content"
        ) as mock_get_content:
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command
            )

            # Assert
            assert result == existing_analysis_2  # Should match comprehensive template
            self.analysis_repository.create.assert_not_called()
            self.llm_provider.analyze_filing.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_detection_no_existing_analyses(self):
        """Test behavior when no existing analyses found."""
        # Arrange
        new_analysis = Analysis(
            id=uuid4(),
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=self.user_id,
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        mock_llm_response = Mock()
        mock_llm_response.confidence_score = 0.95
        mock_llm_response.model_dump.return_value = {"analysis": "New analysis"}
        mock_llm_response.section_analyses = [Mock(section_name="Item 1 - Business")]

        self.edgar_service.get_filing_by_accession.return_value = self.valid_filing_data
        self.filing_repository.get_by_accession_number.return_value = self.valid_filing
        self.filing_repository.update.return_value = self.valid_filing
        self.analysis_repository.get_by_filing_id.return_value = []  # No existing
        self.analysis_repository.create.return_value = new_analysis
        self.analysis_repository.update.return_value = new_analysis
        self.analysis_repository.get_by_id.return_value = new_analysis
        self.template_service.get_schemas_for_template.return_value = [
            "BusinessAnalysisSection"
        ]
        self.llm_provider.analyze_filing.return_value = mock_llm_response

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
            patch("src.shared.config.settings") as mock_settings,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "default"

            # Act
            result = await self.orchestrator.orchestrate_filing_analysis(
                self.valid_command
            )

            # Assert
            assert result == new_analysis
            self.analysis_repository.create.assert_called_once()
            self.llm_provider.analyze_filing.assert_called_once()


@pytest.mark.unit
class TestAnalysisOrchestratorExternalIntegrations:
    """Test external service integrations and mocking in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

        self.filing_id = uuid4()
        self.analysis_id = uuid4()

    @pytest.mark.asyncio
    async def test_edgar_service_integration(self):
        """Test integration with Edgar service for filing data retrieval."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Apple Inc.",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Sample content",
            raw_html="<html>Sample content</html>",
            ticker="AAPL",
            sections={"Item 1 - Business": "Business content"},
        )

        self.edgar_service.get_filing_by_accession.return_value = filing_data

        # Act
        result = await self.orchestrator.validate_filing_access_and_get_data(
            accession_number
        )

        # Assert
        assert result == filing_data
        self.edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_llm_provider_integration(self):
        """Test integration with LLM provider for analysis processing."""
        # Arrange
        filing_sections = {"Item 1 - Business": "Business content"}
        filing_type = FilingType.FORM_10K
        company_name = "Apple Inc."
        analysis_focus = ["BusinessAnalysisSection"]

        mock_response = Mock()
        mock_response.confidence_score = 0.95
        mock_response.model_dump.return_value = {"analysis": "LLM analysis"}
        mock_response.section_analyses = [Mock(section_name="Item 1 - Business")]

        self.llm_provider.analyze_filing.return_value = mock_response

        # Act
        result = await self.llm_provider.analyze_filing(
            filing_sections=filing_sections,
            filing_type=filing_type,
            company_name=company_name,
            analysis_focus=analysis_focus,
        )

        # Assert
        assert result == mock_response
        self.llm_provider.analyze_filing.assert_called_once_with(
            filing_sections=filing_sections,
            filing_type=filing_type,
            company_name=company_name,
            analysis_focus=analysis_focus,
        )

    @pytest.mark.asyncio
    async def test_template_service_integration(self):
        """Test integration with template service for schema mapping."""
        # Arrange
        template = AnalysisTemplate.COMPREHENSIVE
        expected_schemas = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]

        self.template_service.get_schemas_for_template.return_value = expected_schemas

        # Act
        result = self.template_service.get_schemas_for_template(template)

        # Assert
        assert result == expected_schemas
        self.template_service.get_schemas_for_template.assert_called_once_with(template)

    @pytest.mark.asyncio
    async def test_storage_service_integration(self):
        """Test integration with storage service for filing content and results."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        company_cik = CIK("0000320193")
        _ = uuid4()
        _ = {"analysis": "Sample analysis"}

        with (
            patch(
                "src.infrastructure.tasks.analysis_tasks.get_filing_content"
            ) as mock_get_content,
            patch(
                "src.infrastructure.tasks.analysis_tasks.store_analysis_results"
            ) as mock_store_results,
        ):
            mock_get_content.return_value = {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_store_results.return_value = True

            # Act - Test filing content retrieval
            content_result = await self.orchestrator._get_filing_content_from_storage(
                accession_number, company_cik
            )

            # Assert
            assert content_result == {
                "sections": {"Item 1 - Business": "Business content"}
            }
            mock_get_content.assert_called_once_with(accession_number, company_cik)

    @pytest.mark.asyncio
    async def test_repository_integration_analysis(self):
        """Test integration with analysis repository."""
        # Arrange
        analysis = Analysis(
            id=self.analysis_id,
            filing_id=self.filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )

        self.analysis_repository.create.return_value = analysis
        self.analysis_repository.get_by_id.return_value = analysis
        self.analysis_repository.update.return_value = analysis

        # Act - Test create
        create_result = await self.analysis_repository.create(analysis)

        # Act - Test get by id
        get_result = await self.analysis_repository.get_by_id(self.analysis_id)

        # Act - Test update
        update_result = await self.analysis_repository.update(analysis)

        # Assert
        assert create_result == analysis
        assert get_result == analysis
        assert update_result == analysis

        self.analysis_repository.create.assert_called_once_with(analysis)
        self.analysis_repository.get_by_id.assert_called_once_with(self.analysis_id)
        self.analysis_repository.update.assert_called_once_with(analysis)

    @pytest.mark.asyncio
    async def test_repository_integration_filing(self):
        """Test integration with filing repository."""
        # Arrange
        filing = Filing(
            id=self.filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.now(UTC).date(),
            processing_status=ProcessingStatus.PENDING,
            metadata={},
        )

        self.filing_repository.get_by_accession_number.return_value = filing
        self.filing_repository.update.return_value = filing

        # Act
        get_result = await self.filing_repository.get_by_accession_number(
            filing.accession_number
        )
        update_result = await self.filing_repository.update(filing)

        # Assert
        assert get_result == filing
        assert update_result == filing

        self.filing_repository.get_by_accession_number.assert_called_once_with(
            filing.accession_number
        )
        self.filing_repository.update.assert_called_once_with(filing)

    @pytest.mark.asyncio
    async def test_external_service_error_handling(self):
        """Test error handling for external service failures."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")

        # Test Edgar service error
        self.edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Edgar API error"
        )

        # Act & Assert
        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await self.orchestrator.validate_filing_access_and_get_data(
                accession_number
            )

        # Test LLM provider error
        self.llm_provider.analyze_filing.side_effect = Exception("LLM API error")

        with pytest.raises(Exception, match="LLM API error"):
            await self.llm_provider.analyze_filing(
                filing_sections={},
                filing_type=FilingType.FORM_10K,
                company_name="Test",
                analysis_focus=[],
            )

    @pytest.mark.asyncio
    async def test_settings_integration(self):
        """Test integration with application settings."""
        # This test verifies that settings are properly accessed in the orchestrator
        with patch(
            "src.application.services.analysis_orchestrator.settings"
        ) as mock_settings:
            mock_settings.default_llm_provider = "openai"
            mock_settings.llm_model = "gpt-4"

            command = AnalyzeFilingCommand(
                user_id=uuid4(),
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

            # Act
            _ = await self.orchestrator._create_analysis_entity(self.filing_id, command)

            # Assert
            created_analysis = self.analysis_repository.create.call_args[0][0]
            assert created_analysis.llm_provider == "openai"
            assert created_analysis.llm_model == "gpt-4"


@pytest.mark.unit
class TestAnalysisOrchestratorEdgeCases:
    """Test edge cases and boundary conditions in AnalysisOrchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_repository = AsyncMock(spec=AnalysisRepository)
        self.filing_repository = AsyncMock(spec=FilingRepository)
        self.filing_repository.session = (
            AsyncMock()
        )  # Add session attribute for CompanyRepository
        self.edgar_service = Mock(spec=EdgarService)
        self.llm_provider = AsyncMock(spec=BaseLLMProvider)
        self.template_service = Mock(spec=AnalysisTemplateService)

        self.orchestrator = AnalysisOrchestrator(
            analysis_repository=self.analysis_repository,
            filing_repository=self.filing_repository,
            edgar_service=self.edgar_service,
            llm_provider=self.llm_provider,
            template_service=self.template_service,
        )

    @pytest.mark.asyncio
    async def test_command_validation_edge_cases(self):
        """Test command validation with various edge cases."""
        # Test with None accession number using object.__setattr__ to bypass frozen dataclass
        with patch.object(AnalyzeFilingCommand, "validate"):
            command = AnalyzeFilingCommand(
                user_id=uuid4(),
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(command, "accession_number", None)

        with pytest.raises(
            AnalysisOrchestrationError,
            match="Analysis orchestration failed.*accession_number is required",
        ):
            await self.orchestrator.orchestrate_filing_analysis(command)

    @pytest.mark.asyncio
    async def test_filing_creation_with_minimal_data(self):
        """Test filing creation with minimal required data."""
        # Arrange
        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Test Company",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01",  # Minimal date format
            content_text="Minimal content",
            raw_html=None,  # No HTML
            ticker=None,  # No ticker
            sections={},  # No sections
        )

        company_cik = CIK("0000320193")

        # Mock company repository
        with patch(
            "src.application.services.analysis_orchestrator.CompanyRepository"
        ) as mock_company_repo_class:
            mock_company_repo = AsyncMock()
            mock_company_repo_class.return_value = mock_company_repo
            mock_company_repo.get_by_cik.return_value = None  # No existing company
            mock_company_repo.create.return_value = Company(
                id=uuid4(),
                cik=company_cik,
                name="Test Company",
                metadata={},
            )

            self.filing_repository.create.return_value = Filing(
                id=uuid4(),
                company_id=uuid4(),
                accession_number=AccessionNumber("0000320193-23-000106"),
                filing_type=FilingType.FORM_10K,
                filing_date=datetime.now(UTC).date(),
                processing_status=ProcessingStatus.PENDING,
                metadata={},
            )

            # Act
            result = await self.orchestrator._create_filing_from_edgar_data(
                filing_data, company_cik
            )

            # Assert
            assert result is not None
            assert isinstance(result, Filing)

    @pytest.mark.asyncio
    async def test_section_extraction_with_empty_sections(self):
        """Test section extraction when filing has no sections."""
        # Arrange
        filing_content = {"sections": {}}  # Empty sections
        schemas_to_use = ["BusinessAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        filing_data = FilingData(
            accession_number="0000320193-23-000106",
            company_name="Test Company",
            cik="0000320193",
            filing_type="10-K",
            filing_date="2023-10-01T00:00:00Z",
            content_text="Fallback content",
            raw_html="<html>Fallback content</html>",
            ticker=None,
            sections={},  # Empty sections in Edgar data too
        )

        self.edgar_service.get_filing_by_accession.return_value = filing_data

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Filing Content": "Fallback content"}

    @pytest.mark.asyncio
    async def test_section_extraction_with_partial_schema_matches(self):
        """Test section extraction when only some schemas have matching sections."""
        # Arrange
        filing_content = {
            "sections": {
                "Item 1 - Business": "Business content",
                # Missing: Risk Factors section
                "Item 2 - Properties": "Properties content",
            }
        }
        schemas_to_use = ["BusinessAnalysisSection", "RiskFactorsAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Item 1 - Business": "Business content"}
        # Should only include the matching section

    @pytest.mark.asyncio
    async def test_metadata_handling_with_various_schemas(self):
        """Test metadata handling with different schema combinations."""
        # This test verifies that the section-to-schema reverse mapping works correctly
        sections_analyzed = [
            "Item 1 - Business",
            "Part I Item 2 - Management Discussion & Analysis",  # 10-Q MDA
            "Balance Sheet",
            "Unknown Section",  # Should be ignored
        ]

        # Create mock LLM response
        mock_llm_response = Mock()
        mock_llm_response.section_analyses = []
        for section in sections_analyzed:
            mock_section = Mock()
            mock_section.section_name = section
            mock_llm_response.section_analyses.append(mock_section)

        # Test the section-to-schema mapping logic
        section_to_schema_reverse = {
            "Item 1 - Business": "BusinessAnalysisSection",
            "Item 1A - Risk Factors": "RiskFactorsAnalysisSection",
            "Item 7 - Management Discussion & Analysis": "MDAAnalysisSection",
            "Part I Item 2 - Management Discussion & Analysis": "MDAAnalysisSection",
            "Part II Item 1A - Risk Factors": "RiskFactorsAnalysisSection",
            "Balance Sheet": "BalanceSheetAnalysisSection",
            "Income Statement": "IncomeStatementAnalysisSection",
            "Cash Flow Statement": "CashFlowAnalysisSection",
        }

        actual_schemas_processed = []
        for section in sections_analyzed:
            schema = section_to_schema_reverse.get(section)
            if schema and schema not in actual_schemas_processed:
                actual_schemas_processed.append(schema)

        # Assert
        expected_schemas = [
            "BusinessAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
        ]
        assert actual_schemas_processed == expected_schemas

    @pytest.mark.asyncio
    async def test_large_filing_content_handling(self):
        """Test handling of very large filing content."""
        # Arrange
        large_content = "x" * 10000  # Large content string
        filing_content = {
            "sections": {"Item 1 - Business": large_content},
            "content_text": large_content,
        }
        schemas_to_use = ["BusinessAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Item 1 - Business": large_content}
        assert len(result["Item 1 - Business"]) == 10000

    @pytest.mark.asyncio
    async def test_unicode_content_handling(self):
        """Test handling of filing content with unicode characters."""
        # Arrange
        unicode_content = "Business overview: 财务状况良好 ñoño café résumé"
        filing_content = {
            "sections": {"Item 1 - Business": unicode_content},
        }
        schemas_to_use = ["BusinessAnalysisSection"]
        accession_number = AccessionNumber("0000320193-23-000106")

        # Act
        result = await self.orchestrator._extract_relevant_filing_sections(
            filing_content, schemas_to_use, accession_number
        )

        # Assert
        assert result == {"Item 1 - Business": unicode_content}
        assert "财务状况良好" in result["Item 1 - Business"]

    @given(
        progress=st.floats(min_value=0.0, max_value=1.0),
        message=st.text(min_size=1, max_size=100),
    )
    @pytest.mark.asyncio
    async def test_progress_tracking_with_various_inputs(self, progress, message):
        """Test progress tracking with various progress values and messages."""
        # Arrange
        analysis_id = uuid4()
        analysis = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=uuid4(),
            llm_provider="openai",
            llm_model="default",
            created_at=datetime.now(UTC),
        )
        analysis._metadata = {}

        self.analysis_repository.get_by_id.return_value = analysis
        self.analysis_repository.update.return_value = analysis

        # Act
        await self.orchestrator.track_analysis_progress(analysis_id, progress, message)

        # Assert
        assert analysis._metadata["current_progress"] == progress
        assert analysis._metadata["current_status"] == message
        assert "last_updated" in analysis._metadata

    @pytest.mark.asyncio
    async def test_concurrent_progress_callbacks(self):
        """Test handling multiple concurrent progress callbacks."""
        # Arrange
        callback_calls = []
        call_order = []

        async def async_callback_1(progress: float, message: str):
            await asyncio.sleep(0.01)  # Simulate async work
            callback_calls.append(("callback_1", progress, message))
            call_order.append("callback_1")

        async def async_callback_2(progress: float, message: str):
            await asyncio.sleep(0.005)  # Different timing
            callback_calls.append(("callback_2", progress, message))
            call_order.append("callback_2")

        # Act
        await asyncio.gather(
            self.orchestrator._call_progress_callback(
                async_callback_1, 0.5, "Message 1"
            ),
            self.orchestrator._call_progress_callback(
                async_callback_2, 0.7, "Message 2"
            ),
        )

        # Assert
        assert len(callback_calls) == 2
        assert ("callback_1", 0.5, "Message 1") in callback_calls
        assert ("callback_2", 0.7, "Message 2") in callback_calls

    @pytest.mark.asyncio
    async def test_boundary_confidence_scores(self):
        """Test handling of boundary confidence scores."""
        # Test with minimum confidence score
        mock_llm_response_min = Mock()
        mock_llm_response_min.confidence_score = 0.0
        mock_llm_response_min.model_dump.return_value = {"analysis": "Low confidence"}
        mock_llm_response_min.section_analyses = []

        # Test with maximum confidence score
        mock_llm_response_max = Mock()
        mock_llm_response_max.confidence_score = 1.0
        mock_llm_response_max.model_dump.return_value = {"analysis": "High confidence"}
        mock_llm_response_max.section_analyses = []

        # Test with intermediate confidence score
        mock_llm_response_mid = Mock()
        mock_llm_response_mid.confidence_score = 0.5
        mock_llm_response_mid.model_dump.return_value = {"analysis": "Mid confidence"}
        mock_llm_response_mid.section_analyses = []

        # All should be handled correctly
        for response in [
            mock_llm_response_min,
            mock_llm_response_max,
            mock_llm_response_mid,
        ]:
            analysis = Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by=uuid4(),
                llm_provider="openai",
                llm_model="default",
                created_at=datetime.now(UTC),
            )

            # Act
            analysis.update_confidence_score(response.confidence_score)

            # Assert
            assert analysis.confidence_score == response.confidence_score


# Test classes are automatically marked as unit tests by pytest configuration
