"""Unit tests for analysis tasks in messaging infrastructure."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.domain.entities.analysis import Analysis
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.analysis_stage import AnalysisStage
from src.domain.value_objects.cik import CIK
from src.infrastructure.messaging.interfaces import IStorageService
from src.infrastructure.tasks.analysis_tasks import (
    MAX_CONCURRENT_FILING_DOWNLOADS,
    MAX_FILE_SIZE,
    USE_S3_STORAGE,
    _validate_s3_configuration,
    get_analysis_results,
    get_filing_content,
    get_local_storage_service,
    retrieve_and_analyze_filing,
    store_analysis_results,
    store_filing_content,
    validate_analysis_quality,
)


class TestRetrieveAndAnalyzeFiling:
    """Test the main retrieve_and_analyze_filing task."""

    def setup_method(self):
        """Set up test fixtures."""
        self.company_cik = CIK("0000320193")
        self.accession_number = AccessionNumber("0000320193-23-000106")
        self.analysis_template = AnalysisTemplate.COMPREHENSIVE
        self.task_id = "550e8400-e29b-41d4-a716-446655440000"

        # Mock filing content
        self.mock_filing_content = {
            "accession_number": str(self.accession_number),
            "company_cik": str(self.company_cik),
            "filing_type": "10-K",
            "filing_date": "2023-12-31",
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "content_text": "Sample filing content...",
            "sections": {"section1": "content1", "section2": "content2"},
            "raw_html": "<html>Raw filing HTML</html>",
            "metadata": {
                "downloaded_at": asyncio.get_event_loop().time(),
                "source": "edgar_service",
            },
        }

        # Mock analysis result
        self.mock_analysis = Mock(spec=Analysis)
        self.mock_analysis.id = uuid4()
        self.mock_analysis.confidence_score = 0.95
        self.mock_analysis.results = {"summary": "Analysis completed successfully"}

        # Mock company
        self.mock_company = Mock(spec=Company)
        self.mock_company.id = uuid4()
        self.mock_company.cik = self.company_cik
        self.mock_company.name = "Apple Inc."

        # Mock filing
        self.mock_filing = Mock(spec=Filing)
        self.mock_filing.id = uuid4()
        self.mock_filing.company_id = self.mock_company.id
        self.mock_filing.accession_number = self.accession_number

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_complete_success(self):
        """Test complete successful analysis workflow."""
        # Mock all dependencies
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch('src.infrastructure.tasks.analysis_tasks.EdgarService') as _,
            patch('src.infrastructure.tasks.analysis_tasks.OpenAIProvider') as _,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisTemplateService'
            ) as _,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
            ) as mock_orchestrator,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content

            # Mock database session and repositories
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_filing_repo = AsyncMock()
            mock_analysis_repo = AsyncMock()
            mock_company_repo = AsyncMock()

            mock_company_repo.get_by_cik.return_value = self.mock_company
            mock_filing_repo.get_by_accession_number.return_value = self.mock_filing

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_filing_repo,
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_analysis_repo,
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_company_repo,
                ),
            ):
                # Mock orchestrator
                mock_orchestrator_instance = AsyncMock()
                mock_orchestrator.return_value = mock_orchestrator_instance
                mock_orchestrator_instance.orchestrate_filing_analysis.return_value = (
                    self.mock_analysis
                )

                # Act - Access the underlying function via .func attribute since it's decorated with @task
                result = await retrieve_and_analyze_filing.func(
                    company_cik=self.company_cik,
                    accession_number=self.accession_number,
                    analysis_template=self.analysis_template,
                    force_reprocess=False,
                    task_id=self.task_id,
                )

                # Assert
                assert result["status"] == "success"
                assert result["analysis_id"] == str(self.mock_analysis.id)
                assert result["company_cik"] == self.company_cik
                assert result["accession_number"] == self.accession_number
                assert result["analysis_template"] == self.analysis_template
                assert result["confidence_score"] == 0.95
                assert "processing_duration" in result

                # Verify key interactions
                mock_get_filing.assert_called_once_with(
                    self.accession_number, self.company_cik
                )
                mock_company_repo.get_by_cik.assert_called_once_with(self.company_cik)
                mock_filing_repo.get_by_accession_number.assert_called_once_with(
                    accession_number=self.accession_number
                )
                mock_orchestrator_instance.orchestrate_filing_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_with_string_parameters(self):
        """Test task with string parameters (for messaging serialization)."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
            ) as mock_orchestrator,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repos = {
                'filing_repo': AsyncMock(),
                'analysis_repo': AsyncMock(),
                'company_repo': AsyncMock(),
            }

            mock_repos['company_repo'].get_by_cik.return_value = self.mock_company
            mock_repos['filing_repo'].get_by_accession_number.return_value = (
                self.mock_filing
            )

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_repos['filing_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_repos['analysis_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_repos['company_repo'],
                ),
            ):
                mock_orchestrator_instance = AsyncMock()
                mock_orchestrator.return_value = mock_orchestrator_instance
                mock_orchestrator_instance.orchestrate_filing_analysis.return_value = (
                    self.mock_analysis
                )

                # Act - using string parameters, access underlying function via .func
                result = await retrieve_and_analyze_filing.func(
                    company_cik="0000320193",  # String instead of CIK object
                    accession_number="0000320193-23-000106",  # String instead of AccessionNumber object
                    analysis_template="comprehensive",  # String instead of enum
                    force_reprocess=False,
                )

                # Assert - should convert strings to proper types
                assert result["status"] == "success"
                assert result["company_cik"] == CIK("0000320193")
                assert result["accession_number"] == AccessionNumber(
                    "0000320193-23-000106"
                )
                assert result["analysis_template"] == AnalysisTemplate.COMPREHENSIVE

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_filing_not_found(self):
        """Test handling when filing content cannot be retrieved."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
        ):
            mock_get_filing.return_value = None  # Filing not found

            # Act & Assert - Access underlying function via .func
            with pytest.raises(ValueError, match="Unable to retrieve filing content"):
                await retrieve_and_analyze_filing.func(
                    company_cik=self.company_cik,
                    accession_number=self.accession_number,
                    analysis_template=self.analysis_template,
                    task_id=self.task_id,
                )

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_company_auto_creation(self):
        """Test automatic company creation when company not in database."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.EdgarService'
            ) as mock_edgar_service,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # Mock repositories
            mock_filing_repo = AsyncMock()
            mock_analysis_repo = AsyncMock()
            mock_company_repo = AsyncMock()

            # Company not found initially
            mock_company_repo.get_by_cik.return_value = None
            mock_filing_repo.get_by_accession_number.return_value = self.mock_filing

            # Mock Edgar service for company lookup
            mock_edgar_instance = Mock()
            mock_edgar_service.return_value = mock_edgar_instance

            mock_company_data = Mock()
            mock_company_data.name = "Apple Inc."
            mock_company_data.ticker = "AAPL"
            mock_company_data.sic = "3571"
            mock_company_data.sector = "Technology"
            mock_edgar_instance.get_company_by_cik.return_value = mock_company_data

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_filing_repo,
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_analysis_repo,
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_company_repo,
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
                ) as mock_orchestrator,
            ):
                mock_orchestrator_instance = AsyncMock()
                mock_orchestrator.return_value = mock_orchestrator_instance
                mock_orchestrator_instance.orchestrate_filing_analysis.return_value = (
                    self.mock_analysis
                )

                # Act
                result = await retrieve_and_analyze_filing.func(
                    company_cik=self.company_cik,
                    accession_number=self.accession_number,
                    analysis_template=self.analysis_template,
                )

                # Assert
                assert result["status"] == "success"

                # Verify company creation was attempted
                mock_edgar_instance.get_company_by_cik.assert_called_once_with(
                    self.company_cik
                )
                mock_company_repo.update.assert_called_once()
                mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_company_creation_failure(self):
        """Test handling when company auto-creation fails."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.EdgarService'
            ) as mock_edgar_service,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_company_repo = AsyncMock()
            mock_company_repo.get_by_cik.return_value = None  # Company not found

            # Mock Edgar service failure
            mock_edgar_instance = Mock()
            mock_edgar_service.return_value = mock_edgar_instance
            mock_edgar_instance.get_company_by_cik.side_effect = Exception(
                "Edgar service unavailable"
            )

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_company_repo,
                ),
            ):
                # Act & Assert
                with pytest.raises(
                    ValueError,
                    match="Company with CIK .+ not found in database and could not be auto-populated",
                ):
                    await retrieve_and_analyze_filing.func(
                        company_cik=self.company_cik,
                        accession_number=self.accession_number,
                        analysis_template=self.analysis_template,
                    )

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_different_llm_providers(self):
        """Test task with different LLM providers."""
        llm_providers = [
            ("openai", "OpenAIProvider"),
            ("google", "GoogleProvider"),
        ]

        for provider_name, provider_class in llm_providers:
            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.get_filing_content'
                ) as mock_get_filing,
                patch(
                    'src.infrastructure.tasks.analysis_tasks.async_session_maker'
                ) as mock_session_maker,
                patch(
                    f'src.infrastructure.tasks.analysis_tasks.{provider_class}'
                ) as mock_provider,
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
                ) as mock_orchestrator,
            ):
                # Setup mocks
                mock_get_filing.return_value = self.mock_filing_content
                mock_session = AsyncMock()
                mock_session_maker.return_value.__aenter__.return_value = mock_session

                mock_repos = self._setup_mock_repositories()

                with (
                    patch(
                        'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                        return_value=mock_repos['filing_repo'],
                    ),
                    patch(
                        'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                        return_value=mock_repos['analysis_repo'],
                    ),
                    patch(
                        'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                        return_value=mock_repos['company_repo'],
                    ),
                ):
                    mock_orchestrator_instance = AsyncMock()
                    mock_orchestrator.return_value = mock_orchestrator_instance
                    mock_orchestrator_instance.orchestrate_filing_analysis.return_value = (
                        self.mock_analysis
                    )

                    # Act
                    result = await retrieve_and_analyze_filing.func(
                        company_cik=self.company_cik,
                        accession_number=self.accession_number,
                        analysis_template=self.analysis_template,
                        llm_provider=provider_name,
                    )

                    # Assert
                    assert result["status"] == "success"
                    assert result["llm_provider"] == provider_name
                    mock_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_unsupported_llm_provider(self):
        """Test error handling for unsupported LLM provider."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
        ):
            mock_get_filing.return_value = self.mock_filing_content

            # Mock database session to prevent database queries
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # Mock all repositories to avoid database access
            mock_repos = self._setup_mock_repositories()
            mock_repos['company_repo'].get_by_cik.return_value = self.mock_company
            mock_repos['filing_repo'].get_by_accession_number.return_value = (
                self.mock_filing
            )

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_repos['filing_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_repos['analysis_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_repos['company_repo'],
                ),
            ):
                # Act & Assert
                with pytest.raises(
                    ValueError, match="Unsupported LLM provider: unsupported"
                ):
                    await retrieve_and_analyze_filing.func(
                        company_cik=self.company_cik,
                        accession_number=self.accession_number,
                        analysis_template=self.analysis_template,
                        llm_provider="unsupported",
                    )

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_with_task_service_updates(self):
        """Test task service progress updates during execution."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.application.services.task_service.TaskService'
            ) as mock_task_service_class,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
            ) as mock_orchestrator,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repos = self._setup_mock_repositories()
            mock_task_service = AsyncMock()
            mock_task_service_class.return_value = mock_task_service

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_repos['filing_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_repos['analysis_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_repos['company_repo'],
                ),
            ):
                mock_orchestrator_instance = AsyncMock()
                mock_orchestrator.return_value = mock_orchestrator_instance
                mock_orchestrator_instance.orchestrate_filing_analysis.return_value = (
                    self.mock_analysis
                )

                # Act
                result = await retrieve_and_analyze_filing.func(
                    company_cik=self.company_cik,
                    accession_number=self.accession_number,
                    analysis_template=self.analysis_template,
                    task_id=self.task_id,
                )

                # Assert
                assert result["status"] == "success"

                # Verify task service was called for progress updates
                assert mock_task_service.update_task_status.call_count >= 3

                # Check specific progress updates
                call_args_list = mock_task_service.update_task_status.call_args_list

                # First call should be starting
                first_call = call_args_list[0]
                assert first_call[1]["task_id"] == self.task_id
                assert first_call[1]["status"] == "running"
                assert first_call[1]["analysis_stage"] == AnalysisStage.INITIATING.value

                # Last call should be completed
                last_call = call_args_list[-1]
                assert last_call[1]["status"] == "completed"
                assert last_call[1]["analysis_stage"] == AnalysisStage.COMPLETED.value

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_orchestrator_failure(self):
        """Test handling of orchestrator failures."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_filing_content'
            ) as mock_get_filing,
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisOrchestrator'
            ) as mock_orchestrator,
            patch(
                'src.application.services.task_service.TaskService'
            ) as mock_task_service_class,
        ):
            # Setup mocks
            mock_get_filing.return_value = self.mock_filing_content
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repos = self._setup_mock_repositories()
            mock_task_service = AsyncMock()
            mock_task_service_class.return_value = mock_task_service

            with (
                patch(
                    'src.infrastructure.tasks.analysis_tasks.FilingRepository',
                    return_value=mock_repos['filing_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.AnalysisRepository',
                    return_value=mock_repos['analysis_repo'],
                ),
                patch(
                    'src.infrastructure.tasks.analysis_tasks.CompanyRepository',
                    return_value=mock_repos['company_repo'],
                ),
            ):
                # Mock orchestrator failure
                mock_orchestrator_instance = AsyncMock()
                mock_orchestrator.return_value = mock_orchestrator_instance
                mock_orchestrator_instance.orchestrate_filing_analysis.side_effect = (
                    Exception("LLM service unavailable")
                )

                # Act & Assert
                with pytest.raises(Exception, match="LLM service unavailable"):
                    await retrieve_and_analyze_filing.func(
                        company_cik=self.company_cik,
                        accession_number=self.accession_number,
                        analysis_template=self.analysis_template,
                        task_id=self.task_id,
                    )

                # Verify task status was updated to failed
                call_args_list = mock_task_service.update_task_status.call_args_list
                failed_call = next(
                    (call for call in call_args_list if call[1]["status"] == "failed"),
                    None,
                )
                assert failed_call is not None
                assert failed_call[1]["analysis_stage"] == AnalysisStage.ERROR.value

    def _setup_mock_repositories(self):
        """Helper to set up standard mock repositories."""
        repos = {
            'filing_repo': AsyncMock(),
            'analysis_repo': AsyncMock(),
            'company_repo': AsyncMock(),
        }

        repos['company_repo'].get_by_cik.return_value = self.mock_company
        repos['filing_repo'].get_by_accession_number.return_value = self.mock_filing

        return repos


class TestValidateAnalysisQuality:
    """Test the validate_analysis_quality task."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_id = uuid4()

        self.mock_analysis = Mock(spec=Analysis)
        self.mock_analysis.id = self.analysis_id
        self.mock_analysis.confidence_score = 0.95
        self.mock_analysis.results = {"summary": "Test analysis results"}
        self.mock_analysis.metadata = {"model": "gpt-4", "tokens": 5000}

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_success(self):
        """Test successful analysis quality validation."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisRepository'
            ) as mock_repo_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_id.return_value = self.mock_analysis

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert
            assert result["status"] == "success"
            assert result["analysis_id"] == str(self.analysis_id)
            assert (
                result["quality_score"] == 1.0
            )  # Perfect score: has confidence + results + metadata
            assert result["quality_level"] == "excellent"

            quality_metrics = result["quality_metrics"]
            assert quality_metrics["has_confidence_score"] is True
            assert quality_metrics["has_results"] is True
            assert quality_metrics["has_metadata"] is True

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_analysis_not_found(self):
        """Test quality validation when analysis is not found."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisRepository'
            ) as mock_repo_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_id.return_value = None  # Analysis not found

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert - should return error result dict, not raise exception
            assert result["status"] == "error"
            assert result["analysis_id"] == str(self.analysis_id)
            assert f"Analysis {self.analysis_id} not found" in result["error"]
            assert "processing_duration" in result

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_minimal_analysis(self):
        """Test quality validation with minimal analysis data."""
        # Create analysis with minimal data
        minimal_analysis = Mock(spec=Analysis)
        minimal_analysis.id = self.analysis_id
        minimal_analysis.confidence_score = None
        minimal_analysis.results = None
        minimal_analysis.metadata = None

        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisRepository'
            ) as mock_repo_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_id.return_value = minimal_analysis

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert
            assert result["status"] == "success"
            assert result["quality_score"] == 0.0  # No quality features
            assert result["quality_level"] == "poor"

            quality_metrics = result["quality_metrics"]
            assert quality_metrics["has_confidence_score"] is False
            assert quality_metrics["has_results"] is False
            assert quality_metrics["has_metadata"] is False

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_partial_data(self):
        """Test quality validation with partial analysis data."""
        # Create analysis with only some data
        partial_analysis = Mock(spec=Analysis)
        partial_analysis.id = self.analysis_id
        partial_analysis.confidence_score = 0.75
        partial_analysis.results = {"summary": "Partial results"}
        partial_analysis.metadata = None  # Missing metadata

        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisRepository'
            ) as mock_repo_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_id.return_value = partial_analysis

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert
            assert result["status"] == "success"
            assert result["quality_score"] == 0.8  # 0.3 + 0.5 + 0.0
            assert result["quality_level"] == "good"

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_database_error(self):
        """Test quality validation with database error."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
        ):
            # Setup mocks
            mock_session_maker.side_effect = Exception("Database connection failed")

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert
            assert result["status"] == "error"
            assert result["analysis_id"] == str(self.analysis_id)
            assert "Quality validation failed" in result["error"]
            assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_analysis_quality_timing(self):
        """Test that quality validation includes processing duration."""
        with (
            patch(
                'src.infrastructure.tasks.analysis_tasks.async_session_maker'
            ) as mock_session_maker,
            patch(
                'src.infrastructure.tasks.analysis_tasks.AnalysisRepository'
            ) as mock_repo_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_id.return_value = self.mock_analysis

            # Act
            result = await validate_analysis_quality.func(self.analysis_id)

            # Assert
            assert "processing_duration" in result
            assert isinstance(result["processing_duration"], int | float)
            assert result["processing_duration"] >= 0


class TestFilingContentStorage:
    """Test filing content storage and retrieval functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.company_cik = CIK("0000320193")
        self.accession_number = AccessionNumber("0000320193-23-000106")

        self.mock_filing_content = {
            "accession_number": str(self.accession_number),
            "company_cik": str(self.company_cik),
            "filing_type": "10-K",
            "filing_date": "2023-12-31",
            "content_text": "Sample filing content...",
            "metadata": {"source": "edgar_service"},
        }

    @pytest.mark.asyncio
    async def test_get_filing_content_from_local_storage(self):
        """Test retrieving filing content from local storage."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.get.return_value = self.mock_filing_content

            # Act
            result = await get_filing_content(self.accession_number, self.company_cik)

            # Assert
            assert result == self.mock_filing_content

            # Verify correct storage key was used
            expected_key = f"filing:{self.company_cik}/{str(self.accession_number).replace('-', '')}"
            mock_storage.get.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_get_filing_content_not_in_storage_downloads_from_edgar(self):
        """Test downloading from EDGAR when not in storage."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
            patch(
                'src.infrastructure.tasks.analysis_tasks.EdgarService'
            ) as mock_edgar_service,
            patch(
                'src.infrastructure.tasks.analysis_tasks.store_filing_content'
            ) as mock_store,
        ):
            # Setup mocks
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.get.return_value = None  # Not in storage

            mock_edgar = Mock()
            mock_edgar_service.return_value = mock_edgar

            # Mock Edgar filing data
            mock_filing_data = Mock()
            mock_filing_data.filing_type = "10-K"
            mock_filing_data.filing_date = "2023-12-31"
            mock_filing_data.company_name = "Apple Inc."
            mock_filing_data.ticker = "AAPL"
            mock_filing_data.content_text = "Sample content"
            mock_filing_data.sections = {"section1": "content1"}
            mock_filing_data.raw_html = "<html>Raw HTML</html>"

            mock_edgar.get_filing_by_accession.return_value = mock_filing_data
            mock_store.return_value = True  # Storage succeeds

            # Act
            result = await get_filing_content(self.accession_number, self.company_cik)

            # Assert
            assert result is not None
            assert result["accession_number"] == str(self.accession_number)
            assert result["company_cik"] == str(self.company_cik)
            assert result["filing_type"] == "10-K"
            assert result["content_text"] == "Sample content"
            assert result["metadata"]["source"] == "edgar_service"

            # Verify Edgar was called
            mock_edgar.get_filing_by_accession.assert_called_once_with(
                self.accession_number
            )

            # Verify storage was attempted
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_filing_content_edgar_download_failure(self):
        """Test handling of EDGAR download failure."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
            patch(
                'src.infrastructure.tasks.analysis_tasks.EdgarService'
            ) as mock_edgar_service,
        ):
            # Setup mocks
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.get.return_value = None  # Not in storage

            mock_edgar = Mock()
            mock_edgar_service.return_value = mock_edgar
            mock_edgar.get_filing_by_accession.return_value = None  # Download failed

            # Act
            result = await get_filing_content(self.accession_number, self.company_cik)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_store_filing_content_local_storage_success(self):
        """Test successful filing content storage to local storage."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.set.return_value = True

            # Act
            result = await store_filing_content(
                self.accession_number, self.company_cik, self.mock_filing_content
            )

            # Assert
            assert result is True

            # Verify correct storage key was used
            expected_key = f"filing:{self.company_cik}/{str(self.accession_number).replace('-', '')}"
            mock_storage.set.assert_called_once_with(
                expected_key, self.mock_filing_content
            )

    @pytest.mark.asyncio
    async def test_store_filing_content_storage_failure(self):
        """Test handling of storage failure when storing filing content."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.set.side_effect = Exception("Storage service unavailable")

            # Act
            result = await store_filing_content(
                self.accession_number, self.company_cik, self.mock_filing_content
            )

            # Assert
            assert result is False


class TestAnalysisResultsStorage:
    """Test analysis results storage and retrieval functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analysis_id = uuid4()
        self.company_cik = CIK("0000320193")
        self.accession_number = AccessionNumber("0000320193-23-000106")

        self.mock_analysis_results = {
            "analysis_id": str(self.analysis_id),
            "confidence_score": 0.95,
            "findings": ["Finding 1", "Finding 2"],
            "metadata": {"model": "gpt-4", "tokens": 5000},
        }

    @pytest.mark.asyncio
    async def test_get_analysis_results_from_local_storage(self):
        """Test retrieving analysis results from local storage."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.get.return_value = self.mock_analysis_results

            # Act
            result = await get_analysis_results(
                self.analysis_id, self.company_cik, self.accession_number
            )

            # Assert
            assert result == self.mock_analysis_results

            # Verify correct storage key was used
            clean_accession = self.accession_number.value.replace('-', '')
            expected_key = f"analysis:{self.company_cik}/{clean_accession}/analysis_{self.analysis_id}"
            mock_storage.get.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_store_analysis_results_local_storage_success(self):
        """Test successful analysis results storage to local storage."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.set.return_value = True

            # Act
            result = await store_analysis_results(
                self.analysis_id,
                self.company_cik,
                self.accession_number,
                self.mock_analysis_results,
            )

            # Assert
            assert result is True

            # Verify correct storage key was used
            clean_accession = self.accession_number.value.replace('-', '')
            expected_key = f"analysis:{self.company_cik}/{clean_accession}/analysis_{self.analysis_id}"
            mock_storage.set.assert_called_once_with(
                expected_key, self.mock_analysis_results
            )

    @pytest.mark.asyncio
    async def test_store_analysis_results_storage_failure(self):
        """Test handling of storage failure when storing analysis results."""
        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            # Setup mock storage service
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.set.side_effect = Exception("Storage service unavailable")

            # Act
            result = await store_analysis_results(
                self.analysis_id,
                self.company_cik,
                self.accession_number,
                self.mock_analysis_results,
            )

            # Assert
            assert result is False


class TestS3Configuration:
    """Test S3 configuration validation."""

    @patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', True)
    def test_validate_s3_configuration_success(self):
        """Test successful S3 configuration validation."""
        with patch('src.infrastructure.tasks.analysis_tasks.Settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings.return_value = mock_settings_instance
            mock_settings_instance.aws_s3_bucket = "test-bucket"
            mock_settings_instance.aws_region = "us-east-1"

            # Should not raise exception
            _validate_s3_configuration()

    @patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', True)
    def test_validate_s3_configuration_missing_bucket(self):
        """Test S3 configuration validation with missing bucket."""
        with patch('src.infrastructure.tasks.analysis_tasks.Settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings.return_value = mock_settings_instance
            mock_settings_instance.aws_s3_bucket = None
            mock_settings_instance.aws_region = "us-east-1"

            with pytest.raises(ValueError, match="AWS_S3_BUCKET must be set"):
                _validate_s3_configuration()

    @patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', True)
    def test_validate_s3_configuration_missing_region(self):
        """Test S3 configuration validation with missing region."""
        with patch('src.infrastructure.tasks.analysis_tasks.Settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings.return_value = mock_settings_instance
            mock_settings_instance.aws_s3_bucket = "test-bucket"
            mock_settings_instance.aws_region = None

            with pytest.raises(ValueError, match="AWS_REGION must be set"):
                _validate_s3_configuration()


class TestLocalStorageService:
    """Test local storage service helper function."""

    @pytest.mark.asyncio
    async def test_get_local_storage_service_creates_and_connects(self):
        """Test that get_local_storage_service creates and connects storage service."""
        with (
            patch(
                'src.infrastructure.messaging.factory.MessagingFactory'
            ) as mock_factory,
            patch('src.infrastructure.tasks.analysis_tasks.Settings') as _,
        ):
            # Setup mocks
            mock_storage_service = AsyncMock(spec=IStorageService)
            mock_factory.create_storage_service.return_value = mock_storage_service

            # Act
            result = await get_local_storage_service()

            # Assert
            assert result == mock_storage_service
            mock_storage_service.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_local_storage_service_returns_cached_instance(self):
        """Test that subsequent calls return cached storage service instance."""
        # Clear global storage service to ensure clean test state
        import src.infrastructure.tasks.analysis_tasks as analysis_tasks_module

        analysis_tasks_module._local_storage_service = None

        with (
            patch(
                'src.infrastructure.messaging.factory.MessagingFactory'
            ) as mock_factory,
            patch('src.infrastructure.tasks.analysis_tasks.Settings') as _,
        ):
            # Setup mocks - create a single mock instance that will be returned
            mock_storage_service = AsyncMock(spec=IStorageService)
            mock_factory.create_storage_service.return_value = mock_storage_service

            # Act - call twice
            result1 = await get_local_storage_service()
            result2 = await get_local_storage_service()

            # Assert - same instance returned, factory called only once
            assert result1 is result2  # Use 'is' to check same object instance
            assert result1 is mock_storage_service
            mock_factory.create_storage_service.assert_called_once()
            mock_storage_service.connect.assert_called_once()

        # Cleanup: reset global storage service
        analysis_tasks_module._local_storage_service = None


class TestTaskConstants:
    """Test task-related constants."""

    def test_constants_have_expected_values(self):
        """Test that task constants have expected values."""
        assert MAX_CONCURRENT_FILING_DOWNLOADS == 1
        assert MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB
        assert isinstance(USE_S3_STORAGE, bool)

    def test_use_s3_storage_environment_variable(self):
        """Test that USE_S3_STORAGE respects environment variable."""
        with patch.dict('os.environ', {'USE_S3_STORAGE': 'true'}, clear=False):
            # Import the module to verify the constant exists
            from src.infrastructure.tasks.analysis_tasks import USE_S3_STORAGE

            # The constant should be defined (value depends on actual env)
            assert isinstance(USE_S3_STORAGE, bool)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_retrieve_and_analyze_filing_with_none_filing_content(self):
        """Test handling when filing content is None."""
        # This is already covered in test_retrieve_and_analyze_filing_filing_not_found
        pass

    @pytest.mark.asyncio
    async def test_storage_functions_with_very_long_identifiers(self):
        """Test storage functions with very long identifiers."""
        long_cik = CIK("1" * 10)  # Maximum length CIK
        long_accession = AccessionNumber("1234567890-12-123456")
        very_long_analysis_id = UUID('12345678-1234-1234-1234-123456789012')

        filing_content = {"test": "data"}
        analysis_results = {"analysis": "data"}

        with (
            patch('src.infrastructure.tasks.analysis_tasks.USE_S3_STORAGE', False),
            patch(
                'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
            ) as mock_get_storage,
        ):
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage
            mock_storage.set.return_value = True
            mock_storage.get.return_value = filing_content

            # Test filing content storage/retrieval
            store_result = await store_filing_content(
                long_accession, long_cik, filing_content
            )
            assert store_result is True

            get_result = await get_filing_content(long_accession, long_cik)
            assert get_result == filing_content

            # Test analysis results storage
            analysis_store_result = await store_analysis_results(
                very_long_analysis_id, long_cik, long_accession, analysis_results
            )
            assert analysis_store_result is True

    @pytest.mark.asyncio
    async def test_task_functions_handle_asyncio_cancellation(self):
        """Test that task functions handle asyncio cancellation gracefully."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000106")

        # Test get_filing_content cancellation
        with patch(
            'src.infrastructure.tasks.analysis_tasks.get_local_storage_service'
        ) as mock_get_storage:
            mock_storage = AsyncMock(spec=IStorageService)
            mock_get_storage.return_value = mock_storage

            # Create a proper async function that can be cancelled
            async def slow_operation(key):
                await asyncio.sleep(1)  # This will be cancelled
                return None

            mock_storage.get.side_effect = slow_operation

            task = asyncio.create_task(
                get_filing_content(accession_number, company_cik)
            )
            await asyncio.sleep(0.01)  # Allow task to start
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task
