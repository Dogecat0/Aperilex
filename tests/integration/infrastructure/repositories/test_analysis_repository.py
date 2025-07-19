"""Integration tests for AnalysisRepository."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.analysis import Analysis, AnalysisType


@pytest.mark.asyncio
class TestAnalysisRepository:
    """Test AnalysisRepository database operations."""

    async def test_create_analysis(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test creating a new analysis."""
        # Arrange - Create company and filing first
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)
        await filing_repository.commit()

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=sample_filing.id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-api-key",
            results={"summary": "Test analysis"},
            llm_provider="openai",
            llm_model="gpt-4",
            confidence_score=0.85,
            metadata={"test": True},
            created_at=datetime.now(UTC),
        )

        # Act
        created = await analysis_repository.create(analysis)
        await analysis_repository.commit()

        # Assert
        assert created.id == analysis.id
        assert created.filing_id == analysis.filing_id
        assert created.analysis_type == analysis.analysis_type
        assert created.results == analysis.results
        assert created.confidence_score == analysis.confidence_score

    async def test_get_by_filing_id(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test retrieving analyses by filing ID."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        analyses = []
        for i, analysis_type in enumerate(
            [
                AnalysisType.FILING_ANALYSIS,
                AnalysisType.CUSTOM_QUERY,
                AnalysisType.FILING_ANALYSIS,
            ]
        ):
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=sample_filing.id,
                analysis_type=analysis_type,
                created_by="test-user",
                results={"index": i},
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime.now(UTC) - timedelta(hours=i),
            )
            await analysis_repository.create(analysis)
            analyses.append(analysis)

        await analysis_repository.commit()

        # Act
        all_analyses = await analysis_repository.get_by_filing_id(sample_filing.id)
        filing_analyses = await analysis_repository.get_by_filing_id(
            sample_filing.id, analysis_type=AnalysisType.FILING_ANALYSIS
        )

        # Assert
        assert len(all_analyses) == 3
        assert all_analyses[0].results["index"] == 0  # Most recent first
        assert len(filing_analyses) == 2
        assert all(
            a.analysis_type == AnalysisType.FILING_ANALYSIS for a in filing_analyses
        )

    async def test_get_by_type(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test retrieving analyses by type."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        # Create different types of analyses
        types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.CUSTOM_QUERY,
            AnalysisType.COMPARISON,
        ]

        for _i, analysis_type in enumerate(types):
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=sample_filing.id,
                analysis_type=analysis_type,
                created_by="test-user",
                results={},
                llm_provider="openai",
                llm_model="gpt-4",
            )
            await analysis_repository.create(analysis)

        await analysis_repository.commit()

        # Act
        filing_analyses = await analysis_repository.get_by_type(
            AnalysisType.FILING_ANALYSIS
        )
        custom_queries = await analysis_repository.get_by_type(
            AnalysisType.CUSTOM_QUERY, limit=1
        )

        # Assert
        assert len(filing_analyses) == 2
        assert len(custom_queries) == 1

    async def test_get_by_user(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test retrieving analyses by user."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        users = ["user-1", "user-2", "user-1"]
        base_time = datetime.now(UTC)

        for i, user in enumerate(users):
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=sample_filing.id,
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by=user,
                results={},
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=base_time - timedelta(days=i),
            )
            await analysis_repository.create(analysis)

        await analysis_repository.commit()

        # Act
        user1_analyses = await analysis_repository.get_by_user("user-1")
        user1_filtered = await analysis_repository.get_by_user(
            "user-1",
            start_date=base_time - timedelta(days=1),
            end_date=base_time,
        )

        # Assert
        assert len(user1_analyses) == 2
        assert len(user1_filtered) == 1

    async def test_get_high_confidence_analyses(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test retrieving high confidence analyses."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        confidence_scores = [0.95, 0.85, 0.75, 0.65, 0.55]

        for _i, score in enumerate(confidence_scores):
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=sample_filing.id,
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                results={},
                llm_provider="openai",
                llm_model="gpt-4",
                confidence_score=score,
            )
            await analysis_repository.create(analysis)

        await analysis_repository.commit()

        # Act
        high_confidence = await analysis_repository.get_high_confidence_analyses()
        very_high = await analysis_repository.get_high_confidence_analyses(
            min_confidence=0.9, limit=2
        )

        # Assert
        assert len(high_confidence) == 2  # 0.95 and 0.85
        assert high_confidence[0].confidence_score == 0.95
        assert len(very_high) == 1
        assert very_high[0].confidence_score == 0.95

    async def test_get_latest_analysis_for_filing(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test retrieving latest analysis for a filing."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        # Create multiple analyses at different times
        base_time = datetime.now(UTC)
        for i in range(3):
            analysis = Analysis(
                id=uuid.uuid4(),
                filing_id=sample_filing.id,
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                results={"version": i},
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=base_time
                - timedelta(hours=2 - i),  # Latest has highest version
            )
            await analysis_repository.create(analysis)

        await analysis_repository.commit()

        # Act
        latest = await analysis_repository.get_latest_analysis_for_filing(
            sample_filing.id
        )

        # Assert
        assert latest is not None
        assert latest.results["version"] == 2  # Latest version

    async def test_count_by_type(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test counting analyses by type."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        # Create analyses of different types
        type_counts = {
            AnalysisType.FILING_ANALYSIS: 5,
            AnalysisType.CUSTOM_QUERY: 3,
            AnalysisType.COMPARISON: 2,
            AnalysisType.HISTORICAL_TREND: 1,
        }

        for analysis_type, count in type_counts.items():
            for _i in range(count):
                analysis = Analysis(
                    id=uuid.uuid4(),
                    filing_id=sample_filing.id,
                    analysis_type=analysis_type,
                    created_by="test-user",
                    results={},
                    llm_provider="openai",
                    llm_model="gpt-4",
                )
                await analysis_repository.create(analysis)

        await analysis_repository.commit()

        # Act
        counts = await analysis_repository.count_by_type()

        # Assert
        assert counts[AnalysisType.FILING_ANALYSIS.value] == 5
        assert counts[AnalysisType.CUSTOM_QUERY.value] == 3
        assert counts[AnalysisType.COMPARISON.value] == 2
        assert counts[AnalysisType.HISTORICAL_TREND.value] == 1

    async def test_analysis_with_none_created_by(
        self,
        analysis_repository,
        filing_repository,
        company_repository,
        sample_company,
        sample_filing,
    ):
        """Test creating analysis with None created_by field."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)

        analysis = Analysis(
            id=uuid.uuid4(),
            filing_id=sample_filing.id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by=None,  # Anonymous analysis
            results={"summary": "Test"},
            llm_provider="openai",
            llm_model="gpt-4",
        )

        # Act
        await analysis_repository.create(analysis)
        await analysis_repository.commit()

        retrieved = await analysis_repository.get_by_id(analysis.id)

        # Assert
        assert retrieved is not None
        assert retrieved.created_by is None
