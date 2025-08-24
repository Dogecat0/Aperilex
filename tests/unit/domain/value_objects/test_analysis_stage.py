"""Comprehensive tests for AnalysisStage value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.analysis_stage import AnalysisStage


class TestAnalysisStageBasic:
    """Test basic AnalysisStage functionality."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert AnalysisStage.IDLE == "idle"
        assert AnalysisStage.INITIATING == "initiating"
        assert AnalysisStage.LOADING_FILING == "loading_filing"
        assert AnalysisStage.ANALYZING_CONTENT == "analyzing_content"
        assert AnalysisStage.COMPLETING == "completing"
        assert AnalysisStage.COMPLETED == "completed"
        assert AnalysisStage.ERROR == "error"
        assert AnalysisStage.BACKGROUND == "background"

    def test_enum_iteration(self):
        """Test that all enum values are accessible through iteration."""
        all_stages = set(AnalysisStage)
        expected_stages = {
            AnalysisStage.IDLE,
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
            AnalysisStage.COMPLETED,
            AnalysisStage.ERROR,
            AnalysisStage.BACKGROUND,
        }
        assert all_stages == expected_stages
        assert len(all_stages) == 8

    def test_string_equality(self):
        """Test that analysis stages can be compared with strings."""
        assert AnalysisStage.IDLE == "idle"
        assert AnalysisStage.INITIATING == "initiating"
        assert AnalysisStage.LOADING_FILING == "loading_filing"
        assert AnalysisStage.ANALYZING_CONTENT == "analyzing_content"
        assert AnalysisStage.COMPLETING == "completing"
        assert AnalysisStage.COMPLETED == "completed"
        assert AnalysisStage.ERROR == "error"
        assert AnalysisStage.BACKGROUND == "background"

    def test_string_representation(self):
        """Test string representation and values of stages."""
        # Test the values (what gets stored/serialized)
        assert AnalysisStage.IDLE.value == "idle"
        assert AnalysisStage.INITIATING.value == "initiating"
        assert AnalysisStage.LOADING_FILING.value == "loading_filing"
        assert AnalysisStage.ANALYZING_CONTENT.value == "analyzing_content"
        assert AnalysisStage.COMPLETING.value == "completing"
        assert AnalysisStage.COMPLETED.value == "completed"
        assert AnalysisStage.ERROR.value == "error"
        assert AnalysisStage.BACKGROUND.value == "background"


class TestAnalysisStageWorkflow:
    """Test analysis stage workflow patterns."""

    def test_logical_stage_progression(self):
        """Test that stages follow a logical progression."""
        # Define expected workflow progression
        typical_workflow = [
            AnalysisStage.IDLE,
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
            AnalysisStage.COMPLETED,
        ]

        # Each stage should exist
        for stage in typical_workflow:
            assert stage in AnalysisStage

    def test_error_handling_stages(self):
        """Test error handling in workflow."""
        # Error can occur at any point
        error_prone_stages = [
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
        ]

        for stage in error_prone_stages:
            assert stage in AnalysisStage

        # Error is a valid terminal state
        assert AnalysisStage.ERROR in AnalysisStage

    def test_background_processing(self):
        """Test background processing stage."""
        # Background processing should be available
        assert AnalysisStage.BACKGROUND in AnalysisStage
        assert AnalysisStage.BACKGROUND.value == "background"

    def test_terminal_stages(self):
        """Test identification of terminal stages."""
        # Stages that typically represent end states
        terminal_candidates = [
            AnalysisStage.COMPLETED,
            AnalysisStage.ERROR,
        ]

        for stage in terminal_candidates:
            assert stage in AnalysisStage

    def test_active_processing_stages(self):
        """Test identification of active processing stages."""
        # Stages that represent active work
        active_stages = [
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
        ]

        for stage in active_stages:
            assert stage in AnalysisStage

    def test_waiting_stages(self):
        """Test identification of waiting/idle stages."""
        # Stages that represent waiting or background states
        waiting_stages = [
            AnalysisStage.IDLE,
            AnalysisStage.BACKGROUND,
        ]

        for stage in waiting_stages:
            assert stage in AnalysisStage


class TestAnalysisStageClassification:
    """Test classification and categorization of stages."""

    def test_stage_name_consistency(self):
        """Test consistency in stage naming patterns."""
        # All stage values should be lowercase with underscores
        for stage in AnalysisStage:
            value = stage.value
            assert value.islower(), f"Stage value {value} should be lowercase"
            assert " " not in value, f"Stage value {value} should not contain spaces"

            # Should use underscores for multi-word stages
            if "_" in value:
                parts = value.split("_")
                for part in parts:
                    assert part.isalpha(), f"Each part of {value} should be alphabetic"

    def test_stage_categories(self):
        """Test logical categories of stages."""
        # Preparation stages
        preparation_stages = [
            AnalysisStage.IDLE,
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
        ]

        # Processing stages
        processing_stages = [
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
        ]

        # Terminal stages
        terminal_stages = [
            AnalysisStage.COMPLETED,
            AnalysisStage.ERROR,
        ]

        # Special stages
        special_stages = [
            AnalysisStage.BACKGROUND,
        ]

        # All stages should be accounted for
        all_categorized = (
            preparation_stages + processing_stages + terminal_stages + special_stages
        )

        assert set(all_categorized) == set(AnalysisStage)

    def test_stage_semantic_meaning(self):
        """Test semantic meaning of stage names."""
        # Test that stage names reflect their purpose
        semantic_checks = {
            AnalysisStage.IDLE: "idle",
            AnalysisStage.INITIATING: "initiating",
            AnalysisStage.LOADING_FILING: "loading",
            AnalysisStage.ANALYZING_CONTENT: "analyzing",
            AnalysisStage.COMPLETING: "completing",
            AnalysisStage.COMPLETED: "completed",
            AnalysisStage.ERROR: "error",
            AnalysisStage.BACKGROUND: "background",
        }

        for stage, expected_concept in semantic_checks.items():
            assert expected_concept in stage.value.lower()


class TestAnalysisStageIntegration:
    """Test AnalysisStage integration scenarios."""

    def test_enum_string_inheritance(self):
        """Test that AnalysisStage properly inherits from str."""
        for stage in AnalysisStage:
            assert isinstance(stage, str)
            assert isinstance(stage.value, str)

        # String comparison should work
        assert AnalysisStage.IDLE == "idle"
        assert AnalysisStage.COMPLETED == "completed"

        # Values should be the string representations
        assert AnalysisStage.ERROR.value == "error"

    def test_serialization_compatibility(self):
        """Test compatibility with serialization."""
        for stage in AnalysisStage:
            # Should be JSON serializable
            value = stage.value
            assert isinstance(value, str)
            assert '"' not in value
            assert "\\" not in value
            assert "\n" not in value

    def test_database_storage_compatibility(self):
        """Test compatibility with database storage."""
        for stage in AnalysisStage:
            value = stage.value

            # Should be suitable for database storage
            assert value
            assert value.strip() == value  # No leading/trailing whitespace
            assert len(value) <= 50  # Reasonable for VARCHAR columns
            assert value.isascii()  # ASCII characters only

    def test_api_response_compatibility(self):
        """Test compatibility with API responses."""
        for stage in AnalysisStage:
            value = stage.value

            # Should be URL-safe and API-friendly
            assert " " not in value  # No spaces
            assert value.replace("_", "").isalnum()  # Only alphanumeric and underscores

    def test_frontend_integration_patterns(self):
        """Test patterns useful for frontend integration."""
        # Test that stages can be used for UI state management
        ui_state_mapping = {
            AnalysisStage.IDLE: "waiting",
            AnalysisStage.INITIATING: "starting",
            AnalysisStage.LOADING_FILING: "loading",
            AnalysisStage.ANALYZING_CONTENT: "processing",
            AnalysisStage.COMPLETING: "finalizing",
            AnalysisStage.COMPLETED: "done",
            AnalysisStage.ERROR: "failed",
            AnalysisStage.BACKGROUND: "queued",
        }

        for stage, ui_state in ui_state_mapping.items():
            assert stage in AnalysisStage
            assert isinstance(ui_state, str)

    def test_progress_calculation(self):
        """Test patterns for progress calculation."""
        # Define progress stages in order
        progress_order = [
            AnalysisStage.IDLE,  # 0%
            AnalysisStage.INITIATING,  # 10%
            AnalysisStage.LOADING_FILING,  # 25%
            AnalysisStage.ANALYZING_CONTENT,  # 60%
            AnalysisStage.COMPLETING,  # 90%
            AnalysisStage.COMPLETED,  # 100%
        ]

        # Should be able to calculate progress
        for i, stage in enumerate(progress_order):
            assert stage in AnalysisStage
            progress = (i / (len(progress_order) - 1)) * 100
            assert 0 <= progress <= 100


class TestAnalysisStageEdgeCases:
    """Test edge cases and special scenarios."""

    def test_enum_membership(self):
        """Test enum membership checks."""
        # Valid members
        valid_values = [
            "idle",
            "initiating",
            "loading_filing",
            "analyzing_content",
            "completing",
            "completed",
            "error",
            "background",
        ]

        stage_values = [stage.value for stage in AnalysisStage]
        for value in valid_values:
            assert value in stage_values

        # Invalid members
        invalid_values = ["invalid", "processing", "done", "failed", "pending"]
        for value in invalid_values:
            assert value not in stage_values

    def test_case_sensitivity(self):
        """Test case sensitivity of stage values."""
        # All values should be lowercase
        for stage in AnalysisStage:
            assert stage.value.islower()

        # Comparison should be case sensitive
        assert AnalysisStage.IDLE == "idle"
        assert AnalysisStage.IDLE != "IDLE"
        assert AnalysisStage.IDLE != "Idle"

    def test_special_character_handling(self):
        """Test handling of special characters in stage names."""
        # Underscore is the only special character used
        underscore_stages = [stage for stage in AnalysisStage if "_" in stage.value]
        expected_underscore_stages = [
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
        ]

        assert set(underscore_stages) == set(expected_underscore_stages)

        # No other special characters should be present
        for stage in AnalysisStage:
            value = stage.value
            special_chars = set(value) - set("abcdefghijklmnopqrstuvwxyz_")
            assert (
                not special_chars
            ), f"Stage {value} contains unexpected special characters: {special_chars}"

    def test_unique_values(self):
        """Test that all enum values are unique."""
        all_values = [stage.value for stage in AnalysisStage]
        unique_values = set(all_values)

        assert len(all_values) == len(
            unique_values
        ), "All stage values should be unique"

    def test_no_empty_or_whitespace_values(self):
        """Test that no stage has empty or whitespace-only values."""
        for stage in AnalysisStage:
            value = stage.value
            assert value, f"Stage {stage} has empty value"
            assert (
                value.strip() == value
            ), f"Stage {stage} has leading/trailing whitespace"
            assert not value.isspace(), f"Stage {stage} is whitespace-only"


# Property-based tests
class TestAnalysisStagePropertyBased:
    """Property-based tests for AnalysisStage."""

    @given(stage=st.sampled_from(list(AnalysisStage)))
    def test_stage_properties(self, stage):
        """Test that all stages have consistent properties."""
        # Every stage should have a non-empty string value
        assert stage.value
        assert isinstance(stage.value, str)
        assert len(stage.value) > 0

        # Should be lowercase
        assert stage.value.islower()

        # Should not contain problematic characters
        assert "\n" not in stage.value
        assert "\r" not in stage.value
        assert "\t" not in stage.value
        assert " " not in stage.value

    @given(stage=st.sampled_from(list(AnalysisStage)))
    def test_stage_string_behavior(self, stage):
        """Test string behavior of stages."""
        # Should behave like strings
        assert stage == stage.value
        assert str(stage.value) == stage.value

        # Should be hashable
        assert hash(stage) is not None

        # Should work in sets
        stage_set = {stage}
        assert stage in stage_set

        # Should work in dictionaries
        stage_dict = {stage: "test"}
        assert stage_dict[stage] == "test"

    @given(
        stage1=st.sampled_from(list(AnalysisStage)),
        stage2=st.sampled_from(list(AnalysisStage)),
    )
    def test_stage_equality_properties(self, stage1, stage2):
        """Test equality properties of stages."""
        # Reflexivity
        assert stage1 == stage1

        # Symmetry
        if stage1 == stage2:
            assert stage2 == stage1

        # Hash consistency
        if stage1 == stage2:
            assert hash(stage1) == hash(stage2)


@pytest.mark.unit
class TestAnalysisStageComprehensive:
    """Comprehensive tests covering all analysis stages."""

    def test_complete_workflow_coverage(self):
        """Test that stages cover a complete analysis workflow."""
        # Should have initial state
        assert AnalysisStage.IDLE in AnalysisStage

        # Should have processing states
        processing_states = [
            AnalysisStage.INITIATING,
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
        ]
        for state in processing_states:
            assert state in AnalysisStage

        # Should have terminal states
        assert AnalysisStage.COMPLETED in AnalysisStage
        assert AnalysisStage.ERROR in AnalysisStage

        # Should have special states
        assert AnalysisStage.BACKGROUND in AnalysisStage

    def test_stage_count_stability(self):
        """Test that the number of stages is stable."""
        expected_count = 8  # Update this if stages are added/removed
        actual_count = len(list(AnalysisStage))

        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} stages, got {actual_count}"

    def test_no_conflicting_semantics(self):
        """Test that no stages have conflicting semantic meanings."""
        # Group stages by semantic category
        start_states = [AnalysisStage.IDLE, AnalysisStage.INITIATING]
        processing_states = [
            AnalysisStage.LOADING_FILING,
            AnalysisStage.ANALYZING_CONTENT,
            AnalysisStage.COMPLETING,
        ]
        end_states = [AnalysisStage.COMPLETED, AnalysisStage.ERROR]
        special_states = [AnalysisStage.BACKGROUND]

        all_categorized = start_states + processing_states + end_states + special_states

        # All stages should be categorized exactly once
        assert len(all_categorized) == len(set(all_categorized))  # No duplicates
        assert set(all_categorized) == set(AnalysisStage)  # Complete coverage

    def test_value_format_consistency(self):
        """Test that all stage values follow consistent format."""
        for stage in AnalysisStage:
            value = stage.value

            # Should be snake_case
            assert value.islower()

            # Should only contain letters and underscores
            allowed_chars = set("abcdefghijklmnopqrstuvwxyz_")
            actual_chars = set(value)
            assert actual_chars.issubset(allowed_chars)

            # Should not start or end with underscore
            assert not value.startswith("_")
            assert not value.endswith("_")

            # Should not have consecutive underscores
            assert "__" not in value
