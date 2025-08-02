"""Tests for AnalysisOrchestrator."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

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
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType


class TestAnalysisOrchestrator:
    """Test AnalysisOrchestrator functionality."""

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        repository = AsyncMock()
        return repository

    @pytest.fixture
    def mock_filing_repository(self) -> AsyncMock:
        """Mock FilingRepository."""
        repository = AsyncMock()
        return repository

    @pytest.fixture
    def mock_edgar_service(self) -> MagicMock:
        """Mock EdgarService."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_llm_provider(self) -> AsyncMock:
        """Mock LLM Provider."""
        provider = AsyncMock()
        return provider

    @pytest.fixture
    def mock_template_service(self) -> MagicMock:
        """Mock AnalysisTemplateService."""
        service = MagicMock(spec=AnalysisTemplateService)
        service.get_schemas_for_template.return_value = [
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
        """Create AnalysisOrchestrator instance with mocked dependencies."""
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
    def mock_filing_data(self) -> MagicMock:
        """Mock filing data from EdgarService."""
        filing_data = MagicMock()
        filing_data.company_name = "Test Company"
        filing_data.filing_type = FilingType.FORM_10K.value  # Use FilingType enum value
        filing_data.accession_number = "1234567890-12-123456"
        filing_data.ticker = "TEST"
        return filing_data

    @pytest.fixture
    def mock_filing_entity(self) -> MagicMock:
        """Mock filing entity."""
        filing = MagicMock()
        filing.id = uuid4()
        return filing

    @pytest.fixture
    def mock_analysis_entity(self) -> Analysis:
        """Create mock Analysis entity."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test_user",
            llm_provider="openai",
            llm_model="gpt-4",
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_success(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test successful filing access validation."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        result = await orchestrator.validate_filing_access(accession_number)

        assert result is True
        mock_edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_missing_company_name(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test filing access validation with missing company name."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_filing_data.company_name = None
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        with pytest.raises(
            FilingAccessError, match="Filing missing required company name"
        ):
            await orchestrator.validate_filing_access(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_missing_filing_type(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test filing access validation with missing filing type."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_filing_data.filing_type = None
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        with pytest.raises(
            FilingAccessError, match="Filing missing required filing type"
        ):
            await orchestrator.validate_filing_access(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_edgar_service_error(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
    ) -> None:
        """Test filing access validation with EdgarService error."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Filing not found"
        )

        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await orchestrator.validate_filing_access(accession_number)

    @pytest.mark.asyncio
    async def test_handle_analysis_failure(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test analysis failure handling."""
        analysis_id = mock_analysis_entity.id
        error = Exception("Test error")
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity

        await orchestrator.handle_analysis_failure(analysis_id, error)

        # Should retrieve analysis and update it (called twice - once in handle_analysis_failure, once in track_analysis_progress)
        assert mock_analysis_repository.get_by_id.call_count == 2
        mock_analysis_repository.update.assert_called_with(mock_analysis_entity)

        # Check that failure metadata was added
        updated_metadata = mock_analysis_entity.metadata
        assert "failure_reason" in updated_metadata
        assert "failure_type" in updated_metadata
        assert "failed_at" in updated_metadata
        assert updated_metadata["failure_reason"] == "Test error"
        assert updated_metadata["failure_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_handle_analysis_failure_no_analysis(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test analysis failure handling when analysis not found."""
        analysis_id = uuid4()
        error = Exception("Test error")
        mock_analysis_repository.get_by_id.return_value = None

        # Should not raise exception, just log and continue
        await orchestrator.handle_analysis_failure(analysis_id, error)

        mock_analysis_repository.get_by_id.assert_called_once_with(analysis_id)
        mock_analysis_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_analysis_progress(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test analysis progress tracking."""
        analysis_id = mock_analysis_entity.id
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity

        await orchestrator.track_analysis_progress(analysis_id, 0.5, "Processing")

        # Should retrieve and update analysis
        mock_analysis_repository.get_by_id.assert_called_once_with(analysis_id)
        mock_analysis_repository.update.assert_called_once_with(mock_analysis_entity)

        # Check progress metadata was added
        updated_metadata = mock_analysis_entity.metadata
        assert updated_metadata["current_progress"] == 0.5
        assert updated_metadata["current_status"] == "Processing"
        assert "last_updated" in updated_metadata

    @pytest.mark.asyncio
    async def test_track_analysis_progress_no_analysis(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test progress tracking when analysis not found."""
        analysis_id = uuid4()
        mock_analysis_repository.get_by_id.return_value = None

        # Should not raise exception, just log warning and continue
        await orchestrator.track_analysis_progress(analysis_id, 0.5, "Processing")

        mock_analysis_repository.get_by_id.assert_called_once_with(analysis_id)
        mock_analysis_repository.update.assert_not_called()

    @patch('src.application.services.analysis_orchestrator.uuid4')
    @pytest.mark.asyncio
    async def test_create_analysis_entity(
        self,
        mock_uuid4: MagicMock,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test creation of analysis entity."""
        filing_id = uuid4()
        analysis_id = uuid4()
        mock_uuid4.return_value = analysis_id
        mock_analysis_repository.create.return_value = mock_analysis_entity

        result = await orchestrator._create_analysis_entity(filing_id, sample_command)

        assert result == mock_analysis_entity
        mock_analysis_repository.create.assert_called_once()

        # Check that create was called with correct analysis properties
        created_analysis = mock_analysis_repository.create.call_args[0][0]
        assert created_analysis.id == analysis_id
        assert created_analysis.filing_id == filing_id
        assert created_analysis.analysis_type == AnalysisType.FILING_ANALYSIS
        assert created_analysis.created_by == sample_command.user_id
        assert created_analysis.llm_provider == "openai"
        assert created_analysis.llm_model == "gpt-4"

    @pytest.mark.asyncio
    async def test_find_existing_analysis(
        self,
        orchestrator: AnalysisOrchestrator,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test finding existing analysis (placeholder implementation)."""
        filing_id = uuid4()

        # Current implementation always returns None
        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_success(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test successful extraction of relevant filing sections."""
        schemas_to_use = ["BusinessAnalysisSection", "RiskFactorsAnalysisSection"]

        # Mock the extract_filing_sections method
        mock_sections = {
            "Item 1 - Business": "Business section content",
            "Item 1A - Risk Factors": "Risk factors content",
            "Item 7 - Management Discussion & Analysis": "MDA content",
        }
        mock_edgar_service.extract_filing_sections.return_value = mock_sections

        result = await orchestrator._extract_relevant_filing_sections(
            mock_filing_data, schemas_to_use
        )

        # Should only return relevant sections
        expected = {
            "Item 1 - Business": "Business section content",
            "Item 1A - Risk Factors": "Risk factors content",
        }
        assert result == expected

        # Verify the method was called with Ticker and FilingType value objects
        mock_edgar_service.extract_filing_sections.assert_called_once()
        call_args = mock_edgar_service.extract_filing_sections.call_args[0]
        assert str(call_args[0]) == mock_filing_data.ticker  # Ticker value object
        assert (
            call_args[1].value == mock_filing_data.filing_type
        )  # FilingType value object

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_fallback(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test fallback when section extraction fails."""
        schemas_to_use = ["BusinessAnalysisSection"]

        # Mock extraction failure
        mock_edgar_service.extract_filing_sections.side_effect = Exception(
            "Extraction failed"
        )
        mock_filing_data.sections = {"fallback": "content"}

        result = await orchestrator._extract_relevant_filing_sections(
            mock_filing_data, schemas_to_use
        )

        # Should fallback to filing_data.sections
        assert result == {"fallback": "content"}

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_success(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_template_service: MagicMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing_data: MagicMock,
        mock_filing_entity: MagicMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test successful orchestration of filing analysis."""
        # Setup mocks for successful flow
        # Note: We patch validate_filing_access_and_get_data, so Edgar service setup is not needed
        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content"
        }

        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.return_value = mock_filing_data

            result = await orchestrator.orchestrate_filing_analysis(sample_command)

        assert result == mock_analysis_entity

        # Verify key method calls
        mock_validate.assert_called_once_with(sample_command.accession_number)
        # Note: mock_edgar_service.get_filing_by_accession is not called because we patch validate_filing_access_and_get_data
        mock_template_service.get_schemas_for_template.assert_called_once()
        mock_llm_provider.analyze_filing.assert_called_once()

        # Verify the orchestration completed successfully
        assert result == mock_analysis_entity

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_filing_access_error(
        self,
        orchestrator: AnalysisOrchestrator,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test orchestration with filing access error."""
        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.side_effect = FilingAccessError("Cannot access filing")

            with pytest.raises(FilingAccessError):
                await orchestrator.orchestrate_filing_analysis(sample_command)

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_llm_error(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing_data: MagicMock,
        mock_filing_entity: MagicMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test orchestration with LLM processing error."""
        # Setup mocks for partial success
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data
        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_edgar_service.extract_filing_sections.return_value = {}

        # Mock LLM failure
        mock_llm_provider.analyze_filing.side_effect = Exception("LLM failed")

        with (
            patch.object(orchestrator, 'validate_filing_access') as mock_validate,
            patch.object(
                orchestrator, 'handle_analysis_failure'
            ) as mock_handle_failure,
        ):
            mock_validate.return_value = True

            with pytest.raises(AnalysisProcessingError, match="LLM analysis failed"):
                await orchestrator.orchestrate_filing_analysis(sample_command)

            # Should have called failure handler
            mock_handle_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_force_reprocess(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_filing_data: MagicMock,
        mock_filing_entity: MagicMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test orchestration with force reprocess flag."""
        # Create command with force_reprocess=True
        command = AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=True,
            user_id="test_user",
        )

        # Setup mocks
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data
        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        mock_edgar_service.extract_filing_sections.return_value = {}

        with (
            patch.object(orchestrator, 'validate_filing_access') as mock_validate,
            patch.object(orchestrator, '_find_existing_analysis') as mock_find_existing,
        ):
            mock_validate.return_value = True
            mock_find_existing.return_value = (
                mock_analysis_entity  # Existing analysis found
            )

            result = await orchestrator.orchestrate_filing_analysis(command)

        # Should not use existing analysis due to force_reprocess=True
        # Should create new analysis instead
        assert result == mock_analysis_entity
        mock_analysis_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_unexpected_error(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test orchestration with unexpected error."""
        # Mock an unexpected error early in the process
        mock_edgar_service.get_filing_by_accession.side_effect = RuntimeError(
            "Unexpected error"
        )

        with patch.object(orchestrator, 'validate_filing_access') as mock_validate:
            mock_validate.return_value = True

            with pytest.raises(
                AnalysisOrchestrationError, match="Analysis orchestration failed"
            ):
                await orchestrator.orchestrate_filing_analysis(sample_command)

    def test_orchestrator_initialization(
        self,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        mock_template_service: MagicMock,
    ) -> None:
        """Test orchestrator initialization with dependencies."""
        orchestrator = AnalysisOrchestrator(
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            edgar_service=mock_edgar_service,
            llm_provider=mock_llm_provider,
            template_service=mock_template_service,
        )

        assert orchestrator.analysis_repository == mock_analysis_repository
        assert orchestrator.filing_repository == mock_filing_repository
        assert orchestrator.edgar_service == mock_edgar_service
        assert orchestrator.llm_provider == mock_llm_provider
        assert orchestrator.template_service == mock_template_service
