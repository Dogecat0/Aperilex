"""Integration tests for AnalysisTemplate filtering performance and correctness."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.queries.handlers.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.domain.entities.analysis import AnalysisType
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


class TestAnalysisTemplateFilteringIntegration:
    """Integration tests for analysis template filtering."""

    async def test_template_filtering_query_efficiency(
        self, async_session: AsyncSession
    ) -> None:
        """Test that template-based queries generate efficient SQL."""
        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create a query with template filtering
        query = ListAnalysesQuery(
            user_id="test_user",
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            page=1,
            page_size=20,
        )

        # Capture the SQL queries that would be executed
        executed_queries = []

        async def mock_execute(stmt):
            executed_queries.append(str(stmt))
            # Mock non-empty results to ensure both count and find queries are executed
            if "count(" in str(stmt).lower():

                class MockResult:
                    def scalar(self):
                        return 5  # Return non-zero count to trigger find query

                return MockResult()
            else:

                class MockResult:
                    def scalars(self):
                        class MockScalars:
                            def all(self):
                                return []  # Empty results for find query is fine

                        return MockScalars()

                return MockResult()

        # Mock the execute method to capture queries
        with patch.object(async_session, "execute", side_effect=mock_execute):
            await handler.handle(query)

        # Verify that queries were executed
        assert len(executed_queries) >= 2  # At least count and find queries

        # Check that the queries use efficient IN clause for analysis types
        find_query = executed_queries[-1]  # Last query should be the find query
        assert "analysis_type IN" in find_query or "analysis_type = " in find_query

        # Verify that template filtering is working by checking that analysis_type filter is applied
        # SQL uses parameterized queries so we won't see literal values, but we should see the structure
        assert any(
            "analyses.analysis_type IN" in query for query in executed_queries
        ), "Expected to find analysis_type IN clause in SQL queries"

    async def test_template_filtering_with_existing_data(
        self, async_session: AsyncSession
    ) -> None:
        """Test template filtering with actual database data."""
        from datetime import date

        from src.infrastructure.database.models import Company, Filing

        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create required parent records first
        test_company_id = uuid4()
        test_filing_id = uuid4()

        # Create Company record
        test_company = Company(
            id=test_company_id,
            cik="0000320193",
            name="Apple Inc.",
            meta_data={},
        )

        # Create Filing record
        test_filing = Filing(
            id=test_filing_id,
            company_id=test_company_id,
            accession_number="0000320193-24-000007",
            filing_type="10-K",
            filing_date=date.today(),
            processing_status="COMPLETED",
            meta_data={},
        )

        # Create test data with different analysis types
        test_analyses = [
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.FILING_ANALYSIS.value,
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.9,
                created_at=datetime.now(UTC),
            ),
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.85,
                created_at=datetime.now(UTC),
            ),
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.CUSTOM_QUERY.value,
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.8,
                created_at=datetime.now(UTC),
            ),
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.COMPARISON.value,  # Should NOT match FINANCIAL_FOCUSED
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.75,
                created_at=datetime.now(UTC),
            ),
        ]

        # Insert test data (company and filing first, then analyses)
        async_session.add(test_company)
        async_session.add(test_filing)
        async_session.add_all(test_analyses)
        await async_session.commit()

        try:
            # Query with FINANCIAL_FOCUSED template
            query = ListAnalysesQuery(
                user_id="test_user",
                analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
                page=1,
                page_size=20,
            )

            result = await handler.handle(query)

            # Should find 3 analyses (FILING_ANALYSIS, COMPREHENSIVE, CUSTOM_QUERY)
            # but NOT the COMPARISON analysis
            assert result.pagination.total_items == 3
            assert len(result.items) == 3

            # Verify the correct types are returned
            returned_types = {item.analysis_type for item in result.items}
            expected_types = {
                AnalysisType.FILING_ANALYSIS.value,
                AnalysisType.COMPREHENSIVE.value,
                AnalysisType.CUSTOM_QUERY.value,
            }
            assert returned_types == expected_types

            # Test another template
            risk_query = ListAnalysesQuery(
                user_id="test_user",
                analysis_template=AnalysisTemplate.RISK_FOCUSED,
                page=1,
                page_size=20,
            )

            risk_result = await handler.handle(risk_query)

            # RISK_FOCUSED should have the same mapping as FINANCIAL_FOCUSED in current implementation
            assert risk_result.pagination.total_items == 3
            assert len(risk_result.items) == 3

        finally:
            # Clean up test data
            await async_session.rollback()

    async def test_template_plus_explicit_types_filtering(
        self, async_session: AsyncSession
    ) -> None:
        """Test that explicit analysis_types take precedence over template mapping."""
        from datetime import date

        from src.infrastructure.database.models import Company, Filing

        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create required parent records first
        test_company_id = uuid4()
        test_filing_id = uuid4()

        # Create Company record
        test_company = Company(
            id=test_company_id,
            cik="0000789019",
            name="Microsoft Corporation",
            meta_data={},
        )

        # Create Filing record
        test_filing = Filing(
            id=test_filing_id,
            company_id=test_company_id,
            accession_number="0000789019-24-000008",
            filing_type="10-Q",
            filing_date=date.today(),
            processing_status="COMPLETED",
            meta_data={},
        )

        # Create test data
        test_analyses = [
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.FILING_ANALYSIS.value,
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.9,
                created_at=datetime.now(UTC),
            ),
            AnalysisModel(
                id=uuid4(),
                filing_id=test_filing_id,
                analysis_type=AnalysisType.COMPARISON.value,
                created_by="test_user",
                results={},
                llm_provider="openai",
                llm_model="dummy",
                confidence_score=0.85,
                created_at=datetime.now(UTC),
            ),
        ]

        async_session.add(test_company)
        async_session.add(test_filing)
        async_session.add_all(test_analyses)
        await async_session.commit()

        try:
            # Query with both explicit types AND template
            # Explicit types should take precedence
            query = ListAnalysesQuery(
                user_id="test_user",
                analysis_types=[AnalysisType.COMPARISON],  # Only COMPARISON
                analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,  # Should be ignored
                page=1,
                page_size=20,
            )

            result = await handler.handle(query)

            # Should only find the COMPARISON analysis, ignoring the template mapping
            assert result.pagination.total_items == 1
            assert len(result.items) == 1
            assert result.items[0].analysis_type == AnalysisType.COMPARISON.value

        finally:
            await async_session.rollback()

    async def test_template_filtering_performance_with_large_dataset(
        self, async_session: AsyncSession
    ) -> None:
        """Test template filtering performance with larger dataset."""
        from datetime import date

        from src.infrastructure.database.models import Company, Filing

        repository = AnalysisRepository(async_session)
        handler = ListAnalysesQueryHandler(repository)

        # Create required parent records first
        test_companies = []
        test_filings = []
        test_filing_ids = []

        for i in range(10):
            company_id = uuid4()
            filing_id = uuid4()
            test_filing_ids.append(filing_id)

            # Create Company record
            test_companies.append(
                Company(
                    id=company_id,
                    cik=f"000078901{i:01d}",
                    name=f"Test Company {i}",
                    meta_data={},
                )
            )

            # Create Filing record
            test_filings.append(
                Filing(
                    id=filing_id,
                    company_id=company_id,
                    accession_number=f"000078901{i:01d}-24-00000{i:01d}",
                    filing_type="10-K",
                    filing_date=date.today(),
                    processing_status="COMPLETED",
                    meta_data={},
                )
            )

        # Create larger test dataset
        test_analyses = []

        for filing_id in test_filing_ids:
            for analysis_type in AnalysisType:
                test_analyses.append(
                    AnalysisModel(
                        id=uuid4(),
                        filing_id=filing_id,
                        analysis_type=analysis_type.value,
                        created_by="test_user",
                        results={},
                        llm_provider="openai",
                        llm_model="dummy",
                        confidence_score=0.8,
                        created_at=datetime.now(UTC),
                    )
                )

        # Insert test data in batches (companies and filings first, then analyses)
        async_session.add_all(test_companies)
        async_session.add_all(test_filings)

        batch_size = 100
        for i in range(0, len(test_analyses), batch_size):
            batch = test_analyses[i : i + batch_size]
            async_session.add_all(batch)

        await async_session.commit()

        try:
            import time

            # Measure query performance
            start_time = time.time()

            query = ListAnalysesQuery(
                user_id="test_user",
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                page=1,
                page_size=20,
            )

            result = await handler.handle(query)

            end_time = time.time()
            query_duration = end_time - start_time

            # Query should complete reasonably quickly (less than 1 second for this dataset)
            assert (
                query_duration < 1.0
            ), f"Query took {query_duration:.2f} seconds, too slow"

            # Should find analyses matching the template types
            expected_count = (
                len(test_filing_ids) * 3
            )  # 3 types match COMPREHENSIVE template
            assert result.pagination.total_items == expected_count

        finally:
            await async_session.rollback()

    def test_query_template_mapping_consistency(self) -> None:
        """Test that query template mapping is consistent and covers all templates."""
        # Test all templates have mappings
        all_templates = [
            AnalysisTemplate.COMPREHENSIVE,
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        for template in all_templates:
            query = ListAnalysesQuery(
                user_id="test_user",
                analysis_template=template,
            )

            mapped_types = query.get_analysis_types_for_template()

            # Each template should map to some analysis types
            assert mapped_types is not None, f"Template {template.value} has no mapping"
            assert (
                len(mapped_types) > 0
            ), f"Template {template.value} maps to empty list"

            # All mapped types should be valid AnalysisType values
            for analysis_type in mapped_types:
                assert isinstance(
                    analysis_type, AnalysisType
                ), f"Template {template.value} maps to invalid type: {analysis_type}"

            # Core types should be included for logical templates
            if template in [
                AnalysisTemplate.COMPREHENSIVE,
                AnalysisTemplate.FINANCIAL_FOCUSED,
            ]:
                assert (
                    AnalysisType.FILING_ANALYSIS in mapped_types
                ), f"Template {template.value} should include FILING_ANALYSIS"
