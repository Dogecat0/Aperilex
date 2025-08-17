"""Integration tests for AnalysisRepository advanced filtering and querying methods."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.schemas.queries.list_analyses import (
    AnalysisSortField,
    SortDirection,
)
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository


@pytest.mark.integration
class TestAnalysisRepositoryAdvancedQueries:
    """Integration tests for AnalysisRepository advanced filtering methods."""

    @pytest.fixture
    def analysis_repository(self, async_session: AsyncSession) -> AnalysisRepository:
        """Create AnalysisRepository with test session."""
        return AnalysisRepository(async_session)

    @pytest.fixture
    def company_repository(self, async_session: AsyncSession) -> CompanyRepository:
        """Create CompanyRepository for test data setup."""
        return CompanyRepository(async_session)

    @pytest.fixture
    def filing_repository(self, async_session: AsyncSession) -> FilingRepository:
        """Create FilingRepository for test data setup."""
        return FilingRepository(async_session)

    async def create_test_data(
        self,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
        analysis_repository: AnalysisRepository,
        base_cik: int = 8000000000,
    ) -> tuple[list[Company], list[Filing], list[Analysis]]:
        """Create test data in a single transaction scope."""
        # Create companies
        companies = [
            Company(
                id=uuid4(),
                cik=CIK(str(base_cik + 1).zfill(10)),
                name="Test Apple Inc.",
                metadata={"ticker": "AAPL", "sector": "Technology"},
            ),
            Company(
                id=uuid4(),
                cik=CIK(str(base_cik + 2).zfill(10)),
                name="Test Microsoft Corporation",
                metadata={"ticker": "MSFT", "sector": "Technology"},
            ),
            Company(
                id=uuid4(),
                cik=CIK(str(base_cik + 3).zfill(10)),
                name="Test Alphabet Inc.",
                metadata={"ticker": "GOOGL", "sector": "Technology"},
            ),
        ]

        for company in companies:
            await company_repository.create(company)
        await company_repository.commit()

        # Create filings
        filings = []
        for i, company in enumerate(companies):
            for j in range(2):
                filing = Filing(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=AccessionNumber(
                        f"{company.cik.value}-23-{str(j).zfill(6)}"
                    ),
                    filing_type=FilingType.FORM_10K,
                    processing_status=ProcessingStatus.COMPLETED,
                    filing_date=(
                        datetime.now(UTC) - timedelta(days=30 * (i * 2 + j))
                    ).date(),
                )
                filings.append(filing)
                await filing_repository.create(filing)

        await filing_repository.commit()

        # Create analyses
        analyses = []
        analysis_types = [AnalysisType.FILING_ANALYSIS, AnalysisType.FILING_ANALYSIS]
        confidence_scores = [0.85, 0.92, 0.78, 0.88, 0.95, 0.83]
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        for i, filing in enumerate(filings):
            for j in range(2 if i < 3 else 1):
                analysis_time = base_time + timedelta(days=i * 7 + j * 2)

                analysis = Analysis(
                    id=uuid4(),
                    filing_id=filing.id,
                    analysis_type=analysis_types[i % len(analysis_types)],
                    created_by=f"analyst_{(i + j) % 3 + 1}",
                    results={
                        "summary": f"Test analysis {i}-{j}",
                        "key_metrics": {"metric1": i * 10},
                    },
                    llm_provider="openai",
                    llm_model=f"gpt-{4 if i % 2 == 0 else 3.5}-turbo",
                    confidence_score=confidence_scores[i % len(confidence_scores)],
                    created_at=analysis_time,
                    metadata={
                        "processing_time": 30.5 + i * 5.2,
                        "tokens_used": 5000 + i * 500,
                        "template_used": (
                            "COMPREHENSIVE" if i % 2 == 0 else "FINANCIAL_FOCUSED"
                        ),
                    },
                )
                analyses.append(analysis)
                await analysis_repository.create(analysis)

        await analysis_repository.commit()
        return companies, filings, analyses

    @pytest.mark.asyncio
    async def test_find_by_filing_id_integration(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_by_filing_id method integration."""
        # Create test data
        companies, filings, analyses = await self.create_test_data(
            company_repository, filing_repository, analysis_repository
        )

        # Get first filing's analyses
        first_filing = filings[0]
        analyses_for_filing = await analysis_repository.find_by_filing_id(
            first_filing.id
        )

        # Verify results
        assert (
            len(analyses_for_filing) == 2
        )  # We created 2 analyses for first few filings
        for analysis in analyses_for_filing:
            assert analysis.filing_id == first_filing.id

    @pytest.mark.asyncio
    async def test_count_with_filters_no_filters(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test count_with_filters without any filters."""
        # Create test data with different base CIK to avoid conflicts
        companies, filings, analyses = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9000000000,
        )

        # Now test the count method
        total_count = await analysis_repository.count_with_filters()

        # Should return total number of analyses
        expected_count = len(analyses)
        assert total_count == expected_count

    @pytest.mark.asyncio
    async def test_count_with_filters_company_cik_filter(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test count_with_filters with company CIK filter."""
        # Create test data
        companies, filings, analyses = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9100000000,
        )

        # Filter by Apple Inc. (first company)
        apple_cik = companies[0].cik
        count = await analysis_repository.count_with_filters(company_cik=apple_cik)

        # Should return analyses for Apple's filings only
        # Apple has 2 filings, each with 2 analyses = 4 analyses
        assert count == 4

    @pytest.mark.asyncio
    async def test_count_with_filters_analysis_types_filter(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test count_with_filters with analysis types filter."""
        # Create test data
        companies, filings, analyses = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9200000000,
        )

        # Filter by FILING_ANALYSIS type
        count = await analysis_repository.count_with_filters(
            analysis_types=[AnalysisType.FILING_ANALYSIS]
        )

        # Should return all analyses since they're all FILING_ANALYSIS
        assert count == len(analyses)

    @pytest.mark.asyncio
    async def test_count_with_filters_date_range_filter(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test count_with_filters with date range filter."""
        # Create test data
        companies, filings, analyses = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9300000000,
        )

        # Filter by a specific date range
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 15, tzinfo=UTC)  # 2 weeks from start

        count = await analysis_repository.count_with_filters(
            created_from=start_date, created_to=end_date
        )

        # Should return analyses created within the first 2 weeks of January 2024
        # Based on our test data creation logic, this should be a subset
        assert 0 < count < len(analyses)

    @pytest.mark.asyncio
    async def test_count_with_filters_multiple_filters(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test count_with_filters with multiple filters combined."""
        # Create test data
        companies, filings, analyses = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9400000000,
        )

        # Combine company filter with date range
        apple_cik = companies[0].cik
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 10, tzinfo=UTC)

        count = await analysis_repository.count_with_filters(
            company_cik=apple_cik,
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=start_date,
            created_to=end_date,
        )

        # Should be more restrictive than individual filters
        apple_only_count = await analysis_repository.count_with_filters(
            company_cik=apple_cik
        )
        assert count <= apple_only_count

    @pytest.mark.asyncio
    async def test_find_with_filters_no_filters(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters without any filters."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9500000000,
        )

        analyses = await analysis_repository.find_with_filters(page=1, page_size=10)

        # Should return up to 10 analyses from page 1
        assert len(analyses) <= 10
        assert len(analyses) > 0

    @pytest.mark.asyncio
    async def test_find_with_filters_company_cik_filter(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters with company CIK filter."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9600000000,
        )

        # Filter by Microsoft (second company)
        microsoft_cik = companies[1].cik
        analyses = await analysis_repository.find_with_filters(
            company_cik=microsoft_cik, page=1, page_size=10
        )

        # Should return only Microsoft analyses
        assert len(analyses) > 0
        # Verify all returned analyses belong to Microsoft filings
        # (We can't directly check this without joining, but count should match)
        expected_count = await analysis_repository.count_with_filters(
            company_cik=microsoft_cik
        )
        assert len(analyses) == min(expected_count, 10)

    @pytest.mark.asyncio
    async def test_find_with_filters_sorting_by_created_at(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters with sorting by created_at."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9800000000,
        )

        # Sort by created_at ascending
        analyses_asc = await analysis_repository.find_with_filters(
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.ASC,
            page=1,
            page_size=5,
        )

        # Sort by created_at descending
        analyses_desc = await analysis_repository.find_with_filters(
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=5,
        )

        # Verify sorting
        assert len(analyses_asc) > 0
        assert len(analyses_desc) > 0

        # Verify ascending order
        for i in range(1, len(analyses_asc)):
            assert analyses_asc[i - 1].created_at <= analyses_asc[i].created_at

        # Verify descending order
        for i in range(1, len(analyses_desc)):
            assert analyses_desc[i - 1].created_at >= analyses_desc[i].created_at

    @pytest.mark.asyncio
    async def test_find_with_filters_sorting_by_confidence_score(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters with sorting by confidence_score."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9850000000,
        )

        # Sort by confidence_score descending (highest first)
        analyses = await analysis_repository.find_with_filters(
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=10,
        )

        assert len(analyses) > 0

        # Verify descending order by confidence score
        for i in range(1, len(analyses)):
            assert analyses[i - 1].confidence_score >= analyses[i].confidence_score

    @pytest.mark.asyncio
    async def test_find_with_filters_pagination(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters pagination functionality."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9700000000,
        )

        page_size = 3

        # Get first page
        page1 = await analysis_repository.find_with_filters(
            page=1,
            page_size=page_size,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.ASC,
        )

        # Get second page
        page2 = await analysis_repository.find_with_filters(
            page=2,
            page_size=page_size,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.ASC,
        )

        # Verify pagination
        assert len(page1) <= page_size
        assert len(page2) <= page_size

        if len(page1) == page_size and len(page2) > 0:
            # Verify no overlap between pages
            page1_ids = {analysis.id for analysis in page1}
            page2_ids = {analysis.id for analysis in page2}
            assert page1_ids.isdisjoint(page2_ids)

            # Verify ordering across pages
            assert page1[-1].created_at <= page2[0].created_at

    @pytest.mark.asyncio
    async def test_find_with_filters_complex_scenario(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters with complex filtering scenario."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9900000000,
        )

        # Complex filter: Apple analyses, high confidence, recent dates
        apple_cik = companies[0].cik
        recent_date = datetime(2024, 1, 5, tzinfo=UTC)

        # First, get all Apple analyses to understand the data
        all_apple_analyses = await analysis_repository.find_with_filters(
            company_cik=apple_cik, page=1, page_size=100
        )

        # Filter for high confidence, recent Apple analyses
        filtered_analyses = await analysis_repository.find_with_filters(
            company_cik=apple_cik,
            created_from=recent_date,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=10,
        )

        # Verify filtering worked
        assert len(filtered_analyses) <= len(all_apple_analyses)

        # Verify sorting by confidence score
        if len(filtered_analyses) > 1:
            for i in range(1, len(filtered_analyses)):
                assert (
                    filtered_analyses[i - 1].confidence_score
                    >= filtered_analyses[i].confidence_score
                )

    @pytest.mark.asyncio
    async def test_find_with_filters_edge_cases(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test find_with_filters edge cases."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9950000000,
        )

        # Test with very early date (should return all)
        all_analyses = await analysis_repository.find_with_filters(
            created_from=datetime(2020, 1, 1, tzinfo=UTC), page=1, page_size=100
        )
        assert len(all_analyses) == len(analyses_list)

        # Test with future date (should return none)
        future_analyses = await analysis_repository.find_with_filters(
            created_from=datetime(2025, 1, 1, tzinfo=UTC), page=1, page_size=100
        )
        assert len(future_analyses) == 0

        # Test with very large page number (should return empty)
        empty_page = await analysis_repository.find_with_filters(
            page=1000, page_size=10
        )
        assert len(empty_page) == 0

    @pytest.mark.asyncio
    async def test_repository_methods_consistency(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test consistency between count_with_filters and find_with_filters."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9975000000,
        )

        # Test with same filters
        apple_cik = companies[0].cik

        count = await analysis_repository.count_with_filters(
            company_cik=apple_cik, analysis_types=[AnalysisType.FILING_ANALYSIS]
        )

        # Get all matching analyses
        all_matching = await analysis_repository.find_with_filters(
            company_cik=apple_cik,
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            page=1,
            page_size=1000,  # Large enough to get all
        )

        # Count should match the number of returned analyses
        assert count == len(all_matching)

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Test performance characteristics with filtering and pagination."""
        # Create test data
        companies, filings, analyses_list = await self.create_test_data(
            company_repository,
            filing_repository,
            analysis_repository,
            base_cik=9990000000,
        )

        import time

        # Test that complex queries complete in reasonable time
        start_time = time.time()

        # Complex query with multiple filters and sorting
        analyses = await analysis_repository.find_with_filters(
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=5,
        )

        end_time = time.time()
        query_time = end_time - start_time

        # Verify results
        assert len(analyses) > 0

        # Verify reasonable performance (should complete in under 1 second for test data)
        assert (
            query_time < 1.0
        ), f"Query took {query_time:.2f} seconds, which is too slow"

    @pytest.mark.asyncio
    async def test_integration_with_real_database_operations(
        self,
        analysis_repository: AnalysisRepository,
        company_repository: CompanyRepository,
        filing_repository: FilingRepository,
    ) -> None:
        """Integration test with real database operations and relationships."""
        # Create a complete data set with relationships
        company = Company(
            id=uuid4(),
            cik=CIK("9999000001"),
            name="Integration Test Corp",
            metadata={"ticker": "ITC", "sector": "Testing"},
        )
        await company_repository.create(company)
        await company_repository.commit()

        filing = Filing(
            id=uuid4(),
            company_id=company.id,
            accession_number=AccessionNumber("9999000001-24-000001"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2024, 1, 15),
            processing_status=ProcessingStatus.COMPLETED,
        )
        await filing_repository.create(filing)
        await filing_repository.commit()

        analysis1 = Analysis(
            id=uuid4(),
            filing_id=filing.id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="integration_test",
            results={"summary": "Integration test analysis 1", "score": 90},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.90,
            created_at=datetime.now(UTC),
        )
        analysis2 = Analysis(
            id=uuid4(),
            filing_id=filing.id,
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="integration_test",
            results={"summary": "Integration test analysis 2", "score": 87},
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.87,
            created_at=datetime.now(UTC) + timedelta(minutes=5),
        )

        await analysis_repository.create(analysis1)
        await analysis_repository.create(analysis2)
        await analysis_repository.commit()

        # Test that we can filter by the new company
        count = await analysis_repository.count_with_filters(company_cik=company.cik)
        assert count == 2

        # Test that we can retrieve the analyses with filtering
        analyses = await analysis_repository.find_with_filters(
            company_cik=company.cik,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=10,
        )

        assert len(analyses) == 2
        assert analyses[0].confidence_score >= analyses[1].confidence_score
        assert all(analysis.filing_id == filing.id for analysis in analyses)
