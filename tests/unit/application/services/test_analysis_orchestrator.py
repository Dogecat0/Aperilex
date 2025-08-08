"""Tests for AnalysisOrchestrator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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

    # ====================
    # _call_progress_callback() Tests
    # ====================

    @pytest.mark.asyncio
    async def test_call_progress_callback_none(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        """Test _call_progress_callback with None callback."""
        # Should not raise exception
        await orchestrator._call_progress_callback(None, 0.5, "Test message")

    @pytest.mark.asyncio
    async def test_call_progress_callback_sync(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        """Test _call_progress_callback with synchronous callback."""
        callback_called = False
        callback_args = []

        def sync_callback(progress: float, message: str) -> None:
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = [progress, message]

        await orchestrator._call_progress_callback(sync_callback, 0.75, "Sync test")

        assert callback_called
        assert callback_args == [0.75, "Sync test"]

    @pytest.mark.asyncio
    async def test_call_progress_callback_async(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        """Test _call_progress_callback with asynchronous callback."""
        callback_called = False
        callback_args = []

        async def async_callback(progress: float, message: str) -> None:
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = [progress, message]

        await orchestrator._call_progress_callback(async_callback, 0.25, "Async test")

        assert callback_called
        assert callback_args == [0.25, "Async test"]

    @pytest.mark.asyncio
    async def test_call_progress_callback_sync_exception(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        """Test _call_progress_callback with sync callback that raises exception."""

        def failing_sync_callback(progress: float, message: str) -> None:
            raise ValueError("Sync callback failed")

        # Should not raise exception, just log warning
        await orchestrator._call_progress_callback(
            failing_sync_callback, 0.5, "Test message"
        )

    @pytest.mark.asyncio
    async def test_call_progress_callback_async_exception(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        """Test _call_progress_callback with async callback that raises exception."""

        async def failing_async_callback(progress: float, message: str) -> None:
            raise ValueError("Async callback failed")

        # Should not raise exception, just log warning
        await orchestrator._call_progress_callback(
            failing_async_callback, 0.5, "Test message"
        )

    # ====================
    # validate_filing_access_and_get_data() Tests
    # ====================

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_success(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test successful validate_filing_access_and_get_data."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        result = await orchestrator.validate_filing_access_and_get_data(
            accession_number
        )

        assert result == mock_filing_data
        mock_edgar_service.get_filing_by_accession.assert_called_once_with(
            accession_number
        )

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_missing_company_name(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test validate_filing_access_and_get_data with missing company name."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_filing_data.company_name = None
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        with pytest.raises(
            FilingAccessError, match="Filing missing required company name"
        ):
            await orchestrator.validate_filing_access_and_get_data(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_missing_filing_type(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test validate_filing_access_and_get_data with missing filing type."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_filing_data.filing_type = None
        mock_edgar_service.get_filing_by_accession.return_value = mock_filing_data

        with pytest.raises(
            FilingAccessError, match="Filing missing required filing type"
        ):
            await orchestrator.validate_filing_access_and_get_data(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_and_get_data_value_error(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
    ) -> None:
        """Test validate_filing_access_and_get_data with ValueError from EdgarService."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_edgar_service.get_filing_by_accession.side_effect = ValueError(
            "Filing not found"
        )

        with pytest.raises(FilingAccessError, match="Cannot access filing"):
            await orchestrator.validate_filing_access_and_get_data(accession_number)

    @pytest.mark.asyncio
    async def test_validate_filing_access_exception_handling(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_edgar_service: MagicMock,
    ) -> None:
        """Test validate_filing_access with unexpected exception handling."""
        accession_number = AccessionNumber("1234567890-12-123456")
        mock_edgar_service.get_filing_by_accession.side_effect = RuntimeError(
            "Unexpected error"
        )

        with pytest.raises(
            FilingAccessError, match="Unexpected error validating filing access"
        ):
            await orchestrator.validate_filing_access(accession_number)

    # ====================
    # _create_filing_from_edgar_data() Tests
    # ====================

    @pytest.mark.asyncio
    async def test_create_filing_from_edgar_data_success_with_cik(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_repository: AsyncMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test successful filing creation from Edgar data with CIK object."""
        company_cik = CIK("1234567890")
        mock_filing_data.ticker = "TEST"
        mock_filing_data.filing_date = "2023-12-31T00:00:00Z"
        mock_filing_data.content_text = "Filing content here"
        mock_filing_data.raw_html = "<html>content</html>"
        mock_filing_data.sections = {"Section 1": "Content 1"}

        # Mock company repository and its methods
        mock_company_repo = AsyncMock()
        mock_company = MagicMock()
        mock_company.id = uuid4()
        mock_company.name = "Test Company"
        mock_company_repo.get_by_cik.return_value = mock_company

        mock_filing_entity = MagicMock()
        mock_filing_entity.id = uuid4()
        mock_filing_repository.create.return_value = mock_filing_entity

        with patch(
            'src.infrastructure.repositories.company_repository.CompanyRepository'
        ) as mock_company_repo_class:
            mock_company_repo_class.return_value = mock_company_repo

            result = await orchestrator._create_filing_from_edgar_data(
                mock_filing_data, company_cik
            )

        assert result == mock_filing_entity
        mock_company_repo.get_by_cik.assert_called_once()
        mock_filing_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_filing_from_edgar_data_success_without_cik(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_repository: AsyncMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test successful filing creation from Edgar data without provided CIK."""
        mock_filing_data.cik = "9876543210"
        mock_filing_data.ticker = "TEST"
        mock_filing_data.filing_date = "2023-12-31T00:00:00Z"
        mock_filing_data.content_text = "Filing content here"
        mock_filing_data.raw_html = None
        mock_filing_data.sections = {}

        # Mock company repository and its methods
        mock_company_repo = AsyncMock()
        mock_company = MagicMock()
        mock_company.id = uuid4()
        mock_company.name = "Test Company"
        mock_company_repo.get_by_cik.return_value = mock_company

        mock_filing_entity = MagicMock()
        mock_filing_entity.id = uuid4()
        mock_filing_repository.create.return_value = mock_filing_entity

        with patch(
            'src.infrastructure.repositories.company_repository.CompanyRepository'
        ) as mock_company_repo_class:
            mock_company_repo_class.return_value = mock_company_repo

            result = await orchestrator._create_filing_from_edgar_data(
                mock_filing_data, None
            )

        assert result == mock_filing_entity
        mock_company_repo.get_by_cik.assert_called_once_with(CIK("9876543210"))
        mock_filing_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_filing_from_edgar_data_create_new_company(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_repository: AsyncMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test filing creation when company doesn't exist and needs to be created."""
        company_cik = CIK("1234567890")
        mock_filing_data.ticker = "NEWCO"
        mock_filing_data.filing_date = "2023-12-31"
        mock_filing_data.content_text = "Filing content here"
        mock_filing_data.raw_html = None
        mock_filing_data.sections = {"Item 1": "Business description"}

        # Mock company repository - no existing company found
        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_cik.return_value = None

        # Mock new company creation
        mock_new_company = MagicMock()
        mock_new_company.id = uuid4()
        mock_new_company.name = "Test Company"
        mock_company_repo.create.return_value = mock_new_company

        mock_filing_entity = MagicMock()
        mock_filing_entity.id = uuid4()
        mock_filing_repository.create.return_value = mock_filing_entity

        with patch(
            'src.infrastructure.repositories.company_repository.CompanyRepository'
        ) as mock_company_repo_class:
            mock_company_repo_class.return_value = mock_company_repo

            result = await orchestrator._create_filing_from_edgar_data(
                mock_filing_data, company_cik
            )

        assert result == mock_filing_entity
        mock_company_repo.get_by_cik.assert_called_once()
        mock_company_repo.create.assert_called_once()
        mock_filing_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_filing_from_edgar_data_exception(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_repository: AsyncMock,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test filing creation with exception handling."""
        company_cik = CIK("1234567890")
        mock_filing_data.ticker = "TEST"

        # Mock company repository to raise exception
        with (
            patch(
                'src.infrastructure.repositories.company_repository.CompanyRepository'
            ) as mock_company_repo_class,
        ):
            mock_company_repo_class.side_effect = Exception(
                "Database connection failed"
            )

            with pytest.raises(
                AnalysisOrchestrationError, match="Failed to create filing entity"
            ):
                await orchestrator._create_filing_from_edgar_data(
                    mock_filing_data, company_cik
                )

    # ====================
    # _find_existing_analysis() Tests - Real Implementation
    # ====================

    @pytest.mark.asyncio
    async def test_find_existing_analysis_found_match(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test finding existing analysis with matching template."""
        filing_id = uuid4()

        # Set up existing analysis with matching template metadata
        mock_analysis_entity._metadata = {
            "template_used": sample_command.analysis_template.value
        }
        mock_analysis_repository.get_by_filing_id.return_value = [mock_analysis_entity]

        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        assert result == mock_analysis_entity
        mock_analysis_repository.get_by_filing_id.assert_called_once_with(
            filing_id, AnalysisType.FILING_ANALYSIS
        )

    @pytest.mark.asyncio
    async def test_find_existing_analysis_no_match(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test finding existing analysis with no matching template."""
        filing_id = uuid4()

        # Set up existing analysis with different template metadata
        mock_analysis_entity._metadata = {"template_used": "DIFFERENT_TEMPLATE"}
        mock_analysis_repository.get_by_filing_id.return_value = [mock_analysis_entity]

        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        assert result is None
        mock_analysis_repository.get_by_filing_id.assert_called_once_with(
            filing_id, AnalysisType.FILING_ANALYSIS
        )

    @pytest.mark.asyncio
    async def test_find_existing_analysis_no_analyses(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test finding existing analysis when no analyses exist."""
        filing_id = uuid4()

        mock_analysis_repository.get_by_filing_id.return_value = []

        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        assert result is None
        mock_analysis_repository.get_by_filing_id.assert_called_once_with(
            filing_id, AnalysisType.FILING_ANALYSIS
        )

    @pytest.mark.asyncio
    async def test_find_existing_analysis_multiple_analyses_first_match(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test finding existing analysis with multiple analyses, returns first match."""
        filing_id = uuid4()

        # Create two analyses, first one matches
        analysis1 = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user1",
            llm_provider="openai",
            llm_model="gpt-4",
            created_at=datetime.now(UTC),
        )
        analysis1._metadata = {"template_used": sample_command.analysis_template.value}

        analysis2 = Analysis(
            id=uuid4(),
            filing_id=filing_id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user2",
            llm_provider="openai",
            llm_model="gpt-4",
            created_at=datetime.now(UTC),
        )
        analysis2._metadata = {"template_used": "DIFFERENT_TEMPLATE"}

        mock_analysis_repository.get_by_filing_id.return_value = [analysis1, analysis2]

        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        assert result == analysis1  # Should return first matching analysis
        mock_analysis_repository.get_by_filing_id.assert_called_once_with(
            filing_id, AnalysisType.FILING_ANALYSIS
        )

    @pytest.mark.asyncio
    async def test_find_existing_analysis_repository_exception(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test finding existing analysis with repository exception."""
        filing_id = uuid4()

        mock_analysis_repository.get_by_filing_id.side_effect = Exception(
            "Database error"
        )

        result = await orchestrator._find_existing_analysis(filing_id, sample_command)

        # Should return None on exception instead of failing
        assert result is None
        mock_analysis_repository.get_by_filing_id.assert_called_once_with(
            filing_id, AnalysisType.FILING_ANALYSIS
        )

    # ====================
    # Additional Edge Cases for Extract Relevant Filing Sections
    # ====================

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_pre_extracted_relevant(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test extraction when filing data has pre-extracted relevant sections."""
        schemas_to_use = ["BusinessAnalysisSection"]
        mock_filing_data.sections = {
            "Item 1 - Business": "Business section content",
            "Item 2 - Properties": "Properties content",  # Not needed
        }

        result = await orchestrator._extract_relevant_filing_sections(
            mock_filing_data, schemas_to_use
        )

        expected = {"Item 1 - Business": "Business section content"}
        assert result == expected

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_no_ticker_fallback_to_sections(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test extraction when no ticker available, fallback to sections."""
        schemas_to_use = ["BusinessAnalysisSection"]
        mock_filing_data.ticker = None  # No ticker
        mock_filing_data.sections = {"Item 1 - Business": "Business content"}

        result = await orchestrator._extract_relevant_filing_sections(
            mock_filing_data, schemas_to_use
        )

        expected = {"Item 1 - Business": "Business content"}
        assert result == expected

    @pytest.mark.asyncio
    async def test_extract_relevant_filing_sections_no_ticker_no_sections_fallback(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_filing_data: MagicMock,
    ) -> None:
        """Test extraction when no ticker and no sections, fallback to content."""
        schemas_to_use = ["BusinessAnalysisSection"]
        mock_filing_data.ticker = None  # No ticker
        mock_filing_data.sections = {}  # No sections
        mock_filing_data.content_text = "Full filing content text"

        result = await orchestrator._extract_relevant_filing_sections(
            mock_filing_data, schemas_to_use
        )

        expected = {"Filing Content": "Full filing content text"}
        assert result == expected

    # ====================
    # Additional Orchestration Edge Cases
    # ====================

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_extract_sections_no_relevant_found(
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
        """Test orchestration when section extraction finds no relevant sections."""
        # Setup mocks
        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        # Mock filing data with sections but no relevant ones
        mock_filing_data.sections = {"Item 2 - Properties": "Properties content"}
        mock_filing_data.ticker = "TEST"

        # Mock EdgarService to return all sections when no relevant sections found
        all_sections = {
            "Item 1 - Business": "Business content",
            "Item 2 - Properties": "Properties content",
        }
        mock_edgar_service.extract_filing_sections.return_value = all_sections

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_response.section_analyses = []
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.return_value = mock_filing_data

            result = await orchestrator.orchestrate_filing_analysis(sample_command)

        assert result == mock_analysis_entity
        # Verify that EdgarService was called to extract sections
        mock_edgar_service.extract_filing_sections.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_filing_status_already_completed(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing_data: MagicMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test orchestration when filing is already marked as completed."""
        from src.domain.value_objects.processing_status import ProcessingStatus

        # Create filing with COMPLETED status
        mock_filing_entity = MagicMock()
        mock_filing_entity.id = uuid4()
        mock_filing_entity.processing_status = ProcessingStatus.COMPLETED

        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_response.section_analyses = []
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {}

        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.return_value = mock_filing_data

            result = await orchestrator.orchestrate_filing_analysis(sample_command)

        assert result == mock_analysis_entity

        # Verify filing status was NOT updated since it's already completed
        mock_filing_entity.mark_as_completed.assert_not_called()

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_with_section_analyses_mapping(
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
        """Test orchestration with section analyses that map to schemas."""
        # Setup mocks
        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        # Create mock section analyses that will be mapped to schemas
        mock_section_analysis1 = MagicMock()
        mock_section_analysis1.section_name = "Item 1 - Business"
        mock_section_analysis2 = MagicMock()
        mock_section_analysis2.section_name = "Item 1A - Risk Factors"

        # Mock LLM response with section analyses
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_response.section_analyses = [
            mock_section_analysis1,
            mock_section_analysis2,
        ]
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {
            "Item 1 - Business": "Business content",
            "Item 1A - Risk Factors": "Risk content",
        }

        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.return_value = mock_filing_data

            result = await orchestrator.orchestrate_filing_analysis(sample_command)

        assert result == mock_analysis_entity

        # Check that metadata includes processed schemas
        expected_schemas_processed = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]
        # The metadata should be updated during orchestration
        mock_analysis_repository.update.assert_called_with(mock_analysis_entity)

    @pytest.mark.asyncio
    async def test_orchestrate_filing_analysis_filing_status_update(
        self,
        orchestrator: AnalysisOrchestrator,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_llm_provider: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_filing_data: MagicMock,
        mock_analysis_entity: Analysis,
    ) -> None:
        """Test orchestration updates filing status to completed."""
        from src.domain.value_objects.processing_status import ProcessingStatus

        # Create filing with PENDING status
        mock_filing_entity = MagicMock()
        mock_filing_entity.id = uuid4()
        mock_filing_entity.processing_status = ProcessingStatus.PENDING

        mock_filing_repository.get_by_accession_number.return_value = mock_filing_entity
        mock_analysis_repository.create.return_value = mock_analysis_entity
        mock_analysis_repository.get_by_id.return_value = mock_analysis_entity
        mock_analysis_repository.update.return_value = mock_analysis_entity

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.model_dump.return_value = {"test": "results"}
        mock_llm_response.confidence_score = 0.85
        mock_llm_response.section_analyses = []
        mock_llm_provider.analyze_filing.return_value = mock_llm_response

        # Mock section extraction
        mock_edgar_service.extract_filing_sections.return_value = {}

        with patch.object(
            orchestrator, 'validate_filing_access_and_get_data'
        ) as mock_validate:
            mock_validate.return_value = mock_filing_data

            result = await orchestrator.orchestrate_filing_analysis(sample_command)

        assert result == mock_analysis_entity

        # Verify filing status was updated
        mock_filing_entity.mark_as_completed.assert_called_once()
        mock_filing_repository.update.assert_called_with(mock_filing_entity)
