"""End-to-end integration test for template filtering."""

from unittest.mock import AsyncMock

import pytest

from src.application.queries.handlers.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.domain.entities.analysis import AnalysisType
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


@pytest.mark.asyncio
class TestTemplateFilteringEndToEnd:
    """End-to-end tests for template filtering functionality."""

    async def test_template_filtering_complete_flow(self) -> None:
        """Test complete template filtering flow without database."""
        # Mock repository
        mock_repository = AsyncMock(spec=AnalysisRepository)

        # Create handler
        handler = ListAnalysesQueryHandler(mock_repository)

        # Setup mock responses
        mock_repository.count_with_filters.return_value = 5
        mock_repository.find_with_filters.return_value = []

        # Test query with template
        query = ListAnalysesQuery(
            user_id="test_user",
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            page=1,
            page_size=20,
        )

        # Execute
        result = await handler.handle(query)

        # Verify repository was called with correct analysis types from template mapping
        expected_types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.COMPREHENSIVE,
            AnalysisType.CUSTOM_QUERY,
        ]

        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

        mock_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
            page=1,
            page_size=20,
        )

        assert result.pagination.total_items == 5

    def test_all_templates_have_valid_mappings(self) -> None:
        """Ensure all AnalysisTemplate values have corresponding database type mappings."""
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

            # Verify mapping exists and is non-empty
            assert mapped_types is not None, f"Template {template.value} has no mapping"
            assert (
                len(mapped_types) > 0
            ), f"Template {template.value} maps to empty list"

            # Verify all mapped types are valid
            for analysis_type in mapped_types:
                assert isinstance(
                    analysis_type, AnalysisType
                ), f"Template {template.value} maps to invalid type: {analysis_type}"
                # Verify the type value exists in the enum
                assert analysis_type.value in [
                    t.value for t in AnalysisType
                ], f"Template {template.value} maps to non-existent AnalysisType: {analysis_type.value}"

    def test_template_query_properties(self) -> None:
        """Test template-related query properties work correctly."""
        # Query without template
        no_template_query = ListAnalysesQuery(user_id="test_user")
        assert not no_template_query.has_template_filter
        assert no_template_query.get_analysis_types_for_template() is None

        # Query with template
        template_query = ListAnalysesQuery(
            user_id="test_user",
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
        )
        assert template_query.has_template_filter
        assert template_query.get_analysis_types_for_template() is not None
        assert len(template_query.get_analysis_types_for_template()) > 0

    async def test_explicit_types_override_template(self) -> None:
        """Test that explicit analysis_types take precedence over template mapping."""
        mock_repository = AsyncMock(spec=AnalysisRepository)
        handler = ListAnalysesQueryHandler(mock_repository)

        mock_repository.count_with_filters.return_value = 0

        # Query with both explicit types and template
        explicit_types = [AnalysisType.COMPARISON, AnalysisType.HISTORICAL_TREND]
        query = ListAnalysesQuery(
            user_id="test_user",
            analysis_types=explicit_types,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,  # Should be ignored
        )

        await handler.handle(query)

        # Should use explicit types, not template mapping
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=explicit_types,  # Explicit types used
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

    def test_template_mapping_consistency(self) -> None:
        """Test that template mappings are internally consistent."""
        # All templates should include core analysis types
        core_types = [AnalysisType.FILING_ANALYSIS, AnalysisType.COMPREHENSIVE]

        for template in AnalysisTemplate:
            query = ListAnalysesQuery(
                user_id="test_user",
                analysis_template=template,
            )

            mapped_types = query.get_analysis_types_for_template()
            assert mapped_types is not None

            # Each template should include at least the core analysis types
            for core_type in core_types:
                assert (
                    core_type in mapped_types
                ), f"Template {template.value} should include core type {core_type.value}"
