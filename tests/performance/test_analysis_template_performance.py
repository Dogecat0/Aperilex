"""Performance tests for analysis template filtering."""

import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.queries.handlers.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


@pytest.mark.asyncio
class TestAnalysisTemplatePerformance:
    """Performance tests for analysis template filtering."""

    async def test_template_filtering_query_performance(
        self, async_session: AsyncSession
    ) -> None:
        """Test template filtering performance with realistic dataset size."""
        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create test data: 100 companies, each with 10 filings, each with 3 analyses
        companies = []
        filings = []
        analyses = []

        for i in range(100):
            # Create company
            company = CompanyModel(
                id=uuid4(),
                cik=f"{1000000 + i:010d}",
                name=f"Test Company {i}",
                created_at=datetime.now(UTC),
            )
            companies.append(company)

            # Create filings for this company
            for j in range(10):
                filing = FilingModel(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=f"0001000000-24-{i:06d}-{j:02d}",
                    filing_type="10-K",
                    filing_date=datetime.now(UTC).date(),
                    processing_status="completed",
                    created_at=datetime.now(UTC),
                )
                filings.append(filing)

                # Create analyses for this filing
                for analysis_type in [
                    AnalysisType.FILING_ANALYSIS,
                    AnalysisType.COMPREHENSIVE,
                    AnalysisType.COMPARISON,
                ]:
                    analysis = AnalysisModel(
                        id=uuid4(),
                        filing_id=filing.id,
                        analysis_type=analysis_type.value,
                        created_by="performance_test",
                        llm_provider="openai",
                        llm_model="gpt-4",
                        confidence_score=0.8 + (i % 3) * 0.05,  # Vary confidence scores
                        created_at=datetime.now(UTC),
                    )
                    analyses.append(analysis)

        # Insert data in batches to avoid memory issues
        batch_size = 500

        # Insert companies
        for i in range(0, len(companies), batch_size):
            async_session.add_all(companies[i : i + batch_size])
            await async_session.flush()

        # Insert filings
        for i in range(0, len(filings), batch_size):
            async_session.add_all(filings[i : i + batch_size])
            await async_session.flush()

        # Insert analyses
        for i in range(0, len(analyses), batch_size):
            async_session.add_all(analyses[i : i + batch_size])
            await async_session.flush()

        await async_session.commit()

        try:
            # Performance test scenarios
            test_scenarios = [
                (
                    "Basic template query",
                    {
                        "analysis_template": AnalysisTemplate.FINANCIAL_FOCUSED,
                        "page": 1,
                        "page_size": 20,
                    },
                ),
                (
                    "Template with company filter",
                    {
                        "analysis_template": AnalysisTemplate.COMPREHENSIVE,
                        "company_cik": CIK(companies[0].cik),
                        "page": 1,
                        "page_size": 20,
                    },
                ),
                (
                    "Template with confidence filter",
                    {
                        "analysis_template": AnalysisTemplate.RISK_FOCUSED,
                        "min_confidence_score": 0.82,
                        "page": 1,
                        "page_size": 20,
                    },
                ),
                (
                    "Large page size",
                    {
                        "analysis_template": AnalysisTemplate.BUSINESS_FOCUSED,
                        "page": 1,
                        "page_size": 100,
                    },
                ),
                (
                    "Deep pagination",
                    {
                        "analysis_template": AnalysisTemplate.COMPREHENSIVE,
                        "page": 10,
                        "page_size": 50,
                    },
                ),
            ]

            performance_results = []

            for scenario_name, query_params in test_scenarios:
                query = ListAnalysesQuery(user_id="performance_test", **query_params)

                # Warm up query (first run often slower due to caching)
                await handler.handle(query)

                # Measure actual performance (average of 3 runs)
                times = []
                for _ in range(3):
                    start_time = time.time()
                    result = await handler.handle(query)
                    end_time = time.time()
                    times.append(end_time - start_time)

                avg_time = sum(times) / len(times)
                performance_results.append(
                    (scenario_name, avg_time, result.pagination.total_items)
                )

                # Assert reasonable performance (< 500ms for these dataset sizes)
                assert (
                    avg_time < 0.5
                ), f"{scenario_name} took {avg_time:.3f}s, exceeds 500ms threshold"

            # Print performance results for analysis
            print("\nPerformance Test Results:")
            print("=" * 60)
            for scenario, avg_time, total_items in performance_results:
                print(f"{scenario:30} {avg_time*1000:6.1f}ms {total_items:6d} items")

        finally:
            await async_session.rollback()

    async def test_complex_template_filtering_performance(
        self, async_session: AsyncSession
    ) -> None:
        """Test performance of complex filtering scenarios with templates."""
        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create smaller but more diverse dataset
        companies = []
        filings = []
        analyses = []

        # Create 20 companies
        for i in range(20):
            company = CompanyModel(
                id=uuid4(),
                cik=f"{2000000 + i:010d}",
                name=f"Complex Test Company {i}",
                created_at=datetime.now(UTC),
            )
            companies.append(company)

            # Each company has 5 filings
            for j in range(5):
                filing = FilingModel(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=f"0002000000-24-{i:06d}-{j:02d}",
                    filing_type="10-Q" if j % 2 == 0 else "10-K",
                    filing_date=datetime.now(UTC).date(),
                    processing_status="completed",
                    created_at=datetime.now(UTC),
                )
                filings.append(filing)

                # Each filing has all analysis types
                for analysis_type in AnalysisType:
                    analysis = AnalysisModel(
                        id=uuid4(),
                        filing_id=filing.id,
                        analysis_type=analysis_type.value,
                        created_by=f"user_{i % 5}",  # Vary users
                        llm_provider="openai",
                        llm_model="gpt-4",
                        confidence_score=0.7
                        + (hash(f"{i}-{j}") % 30) / 100,  # Pseudo-random scores
                        created_at=datetime.now(UTC),
                    )
                    analyses.append(analysis)

        # Insert all data
        async_session.add_all(companies + filings + analyses)
        await async_session.commit()

        try:
            # Test complex filtering combinations
            complex_scenarios = [
                (
                    "All filters combined",
                    {
                        "analysis_template": AnalysisTemplate.COMPREHENSIVE,
                        "company_cik": CIK(companies[0].cik),
                        "min_confidence_score": 0.75,
                        "created_from": datetime(2024, 1, 1, tzinfo=UTC),
                        "page": 1,
                        "page_size": 50,
                    },
                ),
                (
                    "Multiple templates effect",
                    {
                        "analysis_template": AnalysisTemplate.FINANCIAL_FOCUSED,
                        "page": 1,
                        "page_size": 100,
                    },
                ),
            ]

            for scenario_name, query_params in complex_scenarios:
                query = ListAnalysesQuery(user_id="complex_test", **query_params)

                start_time = time.time()
                result = await handler.handle(query)
                end_time = time.time()

                query_time = end_time - start_time

                # Complex queries should still be reasonably fast
                assert (
                    query_time < 1.0
                ), f"Complex scenario '{scenario_name}' took {query_time:.3f}s, too slow"

                print(
                    f"Complex scenario '{scenario_name}': {query_time*1000:.1f}ms, {result.pagination.total_items} results"
                )

        finally:
            await async_session.rollback()

    async def test_template_vs_explicit_type_performance(
        self, async_session: AsyncSession
    ) -> None:
        """Compare performance between template-based and explicit type filtering."""
        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create moderate dataset
        companies = []
        filings = []
        analyses = []

        for i in range(50):
            company = CompanyModel(
                id=uuid4(),
                cik=f"{3000000 + i:010d}",
                name=f"Perf Compare Company {i}",
                created_at=datetime.now(UTC),
            )
            companies.append(company)

            for j in range(3):
                filing = FilingModel(
                    id=uuid4(),
                    company_id=company.id,
                    accession_number=f"0003000000-24-{i:06d}-{j:02d}",
                    filing_type="10-K",
                    filing_date=datetime.now(UTC).date(),
                    processing_status="completed",
                    created_at=datetime.now(UTC),
                )
                filings.append(filing)

                for analysis_type in AnalysisType:
                    analysis = AnalysisModel(
                        id=uuid4(),
                        filing_id=filing.id,
                        analysis_type=analysis_type.value,
                        created_by="perf_test",
                        llm_provider="openai",
                        llm_model="gpt-4",
                        confidence_score=0.8,
                        created_at=datetime.now(UTC),
                    )
                    analyses.append(analysis)

        async_session.add_all(companies + filings + analyses)
        await async_session.commit()

        try:
            # Template-based query
            template_query = ListAnalysesQuery(
                user_id="perf_test",
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                page=1,
                page_size=50,
            )

            start_time = time.time()
            template_result = await handler.handle(template_query)
            template_time = time.time() - start_time

            # Explicit type query (equivalent to template mapping)
            explicit_query = ListAnalysesQuery(
                user_id="perf_test",
                analysis_types=[
                    AnalysisType.FILING_ANALYSIS,
                    AnalysisType.COMPREHENSIVE,
                    AnalysisType.CUSTOM_QUERY,
                ],
                page=1,
                page_size=50,
            )

            start_time = time.time()
            explicit_result = await handler.handle(explicit_query)
            explicit_time = time.time() - start_time

            # Results should be identical
            assert (
                template_result.pagination.total_items
                == explicit_result.pagination.total_items
            )

            # Performance should be similar (within 50% of each other)
            performance_ratio = (
                template_time / explicit_time if explicit_time > 0 else 1.0
            )
            assert 0.5 <= performance_ratio <= 2.0, (
                f"Template performance significantly different from explicit types: "
                f"{template_time:.3f}s vs {explicit_time:.3f}s (ratio: {performance_ratio:.2f})"
            )

            print(f"Template query: {template_time*1000:.1f}ms")
            print(f"Explicit query: {explicit_time*1000:.1f}ms")
            print(f"Performance ratio: {performance_ratio:.2f}")

        finally:
            await async_session.rollback()
