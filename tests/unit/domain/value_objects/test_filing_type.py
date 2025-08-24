"""Comprehensive tests for FilingType value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.filing_type import FilingType


class TestFilingTypeBasic:
    """Test basic FilingType functionality."""

    def test_enum_values_annual_quarterly(self):
        """Test annual and quarterly report enum values."""
        assert FilingType.FORM_10K == "10-K"
        assert FilingType.FORM_10Q == "10-Q"

    def test_enum_values_current_reports(self):
        """Test current report enum values."""
        assert FilingType.FORM_8K == "8-K"

    def test_enum_values_investment_management(self):
        """Test investment management form enum values."""
        assert FilingType.FORM_13F == "13F"

    def test_enum_values_insider_trading(self):
        """Test insider trading form enum values."""
        assert FilingType.FORM_3 == "3"
        assert FilingType.FORM_4 == "4"
        assert FilingType.FORM_5 == "5"

    def test_enum_values_registration(self):
        """Test registration statement enum values."""
        assert FilingType.FORM_S1 == "S-1"
        assert FilingType.FORM_S3 == "S-3"
        assert FilingType.FORM_S4 == "S-4"

    def test_enum_values_proxy(self):
        """Test proxy statement enum values."""
        assert FilingType.DEF_14A == "DEF 14A"
        assert FilingType.DEFA14A == "DEFA14A"

    def test_enum_values_amendments(self):
        """Test amendment form enum values."""
        assert FilingType.FORM_10K_A == "10-K/A"
        assert FilingType.FORM_10Q_A == "10-Q/A"
        assert FilingType.FORM_8K_A == "8-K/A"

    def test_enum_iteration(self):
        """Test that all enum values are accessible through iteration."""
        all_filing_types = set(FilingType)
        expected_types = {
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_8K,
            FilingType.FORM_13F,
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
            FilingType.FORM_S1,
            FilingType.FORM_S3,
            FilingType.FORM_S4,
            FilingType.DEF_14A,
            FilingType.DEFA14A,
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
            FilingType.FORM_8K_A,
        }
        assert all_filing_types == expected_types
        assert len(all_filing_types) == 15

    def test_string_equality(self):
        """Test that filing types can be compared with strings."""
        assert FilingType.FORM_10K == "10-K"
        assert FilingType.FORM_10Q == "10-Q"
        assert FilingType.FORM_8K == "8-K"
        assert FilingType.FORM_13F == "13F"
        assert FilingType.DEF_14A == "DEF 14A"


class TestFilingTypeAmendments:
    """Test amendment detection functionality."""

    def test_amendment_detection_positive(self):
        """Test that amendment forms are correctly identified."""
        amendment_types = [
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
            FilingType.FORM_8K_A,
        ]

        for filing_type in amendment_types:
            assert (
                filing_type.is_amendment()
            ), f"{filing_type} should be identified as amendment"

    def test_amendment_detection_negative(self):
        """Test that non-amendment forms are correctly identified."""
        non_amendment_types = [
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_8K,
            FilingType.FORM_13F,
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
            FilingType.FORM_S1,
            FilingType.FORM_S3,
            FilingType.FORM_S4,
            FilingType.DEF_14A,
            FilingType.DEFA14A,
        ]

        for filing_type in non_amendment_types:
            assert (
                not filing_type.is_amendment()
            ), f"{filing_type} should not be identified as amendment"

    def test_amendment_pattern(self):
        """Test that amendment detection is based on '/A' pattern."""
        # All amendments should contain "/A"
        for filing_type in FilingType:
            if filing_type.is_amendment():
                assert "/A" in filing_type.value
            else:
                assert "/A" not in filing_type.value


class TestFilingTypeClassification:
    """Test filing type classification by category."""

    def test_annual_quarterly_reports(self):
        """Test identification of annual and quarterly reports."""
        annual_quarterly = {
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
        }

        for filing_type in annual_quarterly:
            # These should contain "10-" pattern
            assert "10-" in filing_type.value or "10-" in filing_type.value.replace(
                "/A", ""
            )

    def test_current_reports(self):
        """Test identification of current reports."""
        current_reports = {
            FilingType.FORM_8K,
            FilingType.FORM_8K_A,
        }

        for filing_type in current_reports:
            # These should contain "8-" pattern
            assert "8-" in filing_type.value or "8-" in filing_type.value.replace(
                "/A", ""
            )

    def test_insider_trading_forms(self):
        """Test identification of insider trading forms."""
        insider_forms = {
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
        }

        for filing_type in insider_forms:
            # These should be single digits
            base_value = filing_type.value.replace("/A", "")
            assert base_value in ["3", "4", "5"]

    def test_registration_statements(self):
        """Test identification of registration statements."""
        registration_forms = {
            FilingType.FORM_S1,
            FilingType.FORM_S3,
            FilingType.FORM_S4,
        }

        for filing_type in registration_forms:
            # These should start with "S-"
            assert filing_type.value.startswith("S-")

    def test_proxy_statements(self):
        """Test identification of proxy statements."""
        proxy_forms = {
            FilingType.DEF_14A,
            FilingType.DEFA14A,
        }

        for filing_type in proxy_forms:
            # These should contain "14A"
            assert "14A" in filing_type.value

    def test_investment_management_forms(self):
        """Test identification of investment management forms."""
        investment_forms = {
            FilingType.FORM_13F,
        }

        for filing_type in investment_forms:
            # These should contain "13"
            assert "13" in filing_type.value


class TestFilingTypeBusinessLogic:
    """Test business logic and real-world usage scenarios."""

    def test_most_common_forms(self):
        """Test the most commonly used filing types."""
        common_forms = [
            FilingType.FORM_10K,  # Annual report
            FilingType.FORM_10Q,  # Quarterly report
            FilingType.FORM_8K,  # Current report
        ]

        for form in common_forms:
            assert form in FilingType
            assert not form.is_amendment()

    def test_amendment_relationships(self):
        """Test relationships between base forms and their amendments."""
        amendment_pairs = [
            (FilingType.FORM_10K, FilingType.FORM_10K_A),
            (FilingType.FORM_10Q, FilingType.FORM_10Q_A),
            (FilingType.FORM_8K, FilingType.FORM_8K_A),
        ]

        for base_form, amendment_form in amendment_pairs:
            assert not base_form.is_amendment()
            assert amendment_form.is_amendment()

            # Amendment should be base form + "/A"
            assert amendment_form.value == f"{base_form.value}/A"

    def test_filing_frequency_expectations(self):
        """Test filing frequency expectations based on form type."""
        # Annual forms
        annual_forms = [FilingType.FORM_10K]
        for form in annual_forms:
            assert "10-K" in form.value

        # Quarterly forms
        quarterly_forms = [FilingType.FORM_10Q]
        for form in quarterly_forms:
            assert "10-Q" in form.value

        # Event-driven forms (no regular schedule)
        event_driven_forms = [
            FilingType.FORM_8K,
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
        ]
        for form in event_driven_forms:
            assert form.value in ["8-K", "3", "4", "5"]

    def test_regulatory_compliance_forms(self):
        """Test forms used for regulatory compliance."""
        # Major periodic reports
        periodic_reports = {
            FilingType.FORM_10K,  # Annual
            FilingType.FORM_10Q,  # Quarterly
            FilingType.FORM_8K,  # Current events
        }

        for form in periodic_reports:
            assert form in FilingType
            # These are core compliance forms
            assert not form.is_amendment()

    def test_insider_reporting_workflow(self):
        """Test insider reporting workflow forms."""
        insider_forms = [
            FilingType.FORM_3,  # Initial statement
            FilingType.FORM_4,  # Statement of changes
            FilingType.FORM_5,  # Annual statement
        ]

        # Should be in chronological/logical order
        form_values = [form.value for form in insider_forms]
        assert form_values == ["3", "4", "5"]


class TestFilingTypeEdgeCases:
    """Test edge cases and special scenarios."""

    def test_enum_membership(self):
        """Test enum membership checks."""
        # Valid members
        assert "10-K" in [ft.value for ft in FilingType]
        assert "10-Q" in [ft.value for ft in FilingType]
        assert "8-K" in [ft.value for ft in FilingType]

        # Invalid members
        assert "10-X" not in [ft.value for ft in FilingType]
        assert "9-K" not in [ft.value for ft in FilingType]
        assert "invalid" not in [ft.value for ft in FilingType]

    def test_string_comparison_edge_cases(self):
        """Test string comparison edge cases."""
        # Case sensitivity
        assert FilingType.FORM_10K == "10-K"
        assert FilingType.FORM_10K != "10-k"  # Case sensitive
        assert FilingType.FORM_10K != "10K"  # Hyphen matters

        # Exact match required
        assert FilingType.DEF_14A == "DEF 14A"
        assert FilingType.DEF_14A != "DEF14A"  # Space matters
        assert FilingType.DEFA14A == "DEFA14A"
        assert FilingType.DEFA14A != "DEF A14A"  # No space in this one

    def test_amendment_pattern_robustness(self):
        """Test robustness of amendment pattern detection."""
        # All amendment forms should have exactly one "/A"
        amendment_forms = [
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
            FilingType.FORM_8K_A,
        ]

        for form in amendment_forms:
            assert form.value.count("/A") == 1
            assert form.value.endswith("/A")

    def test_form_name_consistency(self):
        """Test consistency in form naming patterns."""
        # Forms with numbers should have consistent patterns
        numbered_forms = [
            (FilingType.FORM_10K, "10-K"),
            (FilingType.FORM_10Q, "10-Q"),
            (FilingType.FORM_8K, "8-K"),
            (FilingType.FORM_13F, "13F"),
            (FilingType.FORM_3, "3"),
            (FilingType.FORM_4, "4"),
            (FilingType.FORM_5, "5"),
        ]

        for form_enum, expected_value in numbered_forms:
            assert form_enum.value == expected_value

    def test_unique_values(self):
        """Test that all enum values are unique."""
        all_values = [ft.value for ft in FilingType]
        unique_values = set(all_values)

        assert len(all_values) == len(
            unique_values
        ), "All filing type values should be unique"


class TestFilingTypeIntegration:
    """Test FilingType integration scenarios."""

    def test_enum_string_inheritance(self):
        """Test that FilingType properly inherits from str."""
        for filing_type in FilingType:
            assert isinstance(filing_type, str)
            assert isinstance(filing_type.value, str)

        # String operations should work
        assert FilingType.FORM_10K.upper() == "10-K"
        assert FilingType.FORM_10K.lower() == "10-k"

        # Length should work
        assert len(FilingType.FORM_10K) == len("10-K")

    def test_serialization_compatibility(self):
        """Test that filing types can be serialized as strings."""
        for filing_type in FilingType:
            # Should be serializable as string value
            assert str(filing_type.value) == filing_type.value

            # Should work in string contexts
            assert f"{filing_type.value}" == filing_type.value

    def test_database_storage_compatibility(self):
        """Test compatibility with database storage patterns."""
        # All values should be suitable for database storage
        for filing_type in FilingType:
            value = filing_type.value

            # Should not be empty
            assert value
            assert value.strip() == value  # No leading/trailing whitespace

            # Should be reasonable length for database columns
            assert len(value) <= 20  # Reasonable for VARCHAR columns

    def test_api_response_compatibility(self):
        """Test compatibility with API response patterns."""
        # Values should be suitable for JSON serialization
        for filing_type in FilingType:
            value = filing_type.value

            # Should not contain problematic characters for JSON
            assert '"' not in value
            assert "\\" not in value
            assert "\n" not in value
            assert "\r" not in value

    def test_real_world_filing_scenarios(self):
        """Test real-world filing scenarios."""
        # Quarterly reporting cycle
        quarterly_cycle = [FilingType.FORM_10Q] * 3 + [FilingType.FORM_10K]
        assert len(quarterly_cycle) == 4

        # Amendment scenarios
        original_and_amendments = [
            (FilingType.FORM_10K, FilingType.FORM_10K_A),
            (FilingType.FORM_10Q, FilingType.FORM_10Q_A),
            (FilingType.FORM_8K, FilingType.FORM_8K_A),
        ]

        for original, amendment in original_and_amendments:
            assert not original.is_amendment()
            assert amendment.is_amendment()
            assert f"{original.value}/A" == amendment.value


# Property-based tests
class TestFilingTypePropertyBased:
    """Property-based tests for FilingType."""

    @given(filing_type=st.sampled_from(list(FilingType)))
    def test_filing_type_properties(self, filing_type):
        """Test that filing type properties are consistent."""
        # Every filing type should have a non-empty string value
        assert filing_type.value
        assert isinstance(filing_type.value, str)
        assert len(filing_type.value) > 0

        # Amendment detection should be consistent
        is_amendment = filing_type.is_amendment()
        contains_slash_a = "/A" in filing_type.value
        assert is_amendment == contains_slash_a

    @given(filing_type=st.sampled_from(list(FilingType)))
    def test_filing_type_string_behavior(self, filing_type):
        """Test string behavior of filing types."""
        # Should behave like strings
        assert filing_type == filing_type.value
        assert str(filing_type.value) == filing_type.value

        # Should be hashable
        assert hash(filing_type) is not None

        # Should work in sets
        filing_set = {filing_type}
        assert filing_type in filing_set

    @given(filing_type=st.sampled_from([ft for ft in FilingType if ft.is_amendment()]))
    def test_amendment_properties(self, filing_type):
        """Test properties specific to amendment filing types."""
        assert filing_type.is_amendment()
        assert "/A" in filing_type.value
        assert filing_type.value.endswith("/A")

        # Should have a corresponding base form
        base_value = filing_type.value.replace("/A", "")
        assert base_value  # Should not be empty
        assert len(base_value) > 0

    @given(
        filing_type=st.sampled_from([ft for ft in FilingType if not ft.is_amendment()])
    )
    def test_non_amendment_properties(self, filing_type):
        """Test properties specific to non-amendment filing types."""
        assert not filing_type.is_amendment()
        assert "/A" not in filing_type.value

        # Value should not end with /A
        assert not filing_type.value.endswith("/A")


@pytest.mark.unit
class TestFilingTypeComprehensive:
    """Comprehensive tests covering all filing types."""

    def test_all_forms_accounted_for(self):
        """Test that all expected SEC forms are accounted for."""
        expected_count = 15  # Update this if more forms are added
        actual_count = len(list(FilingType))

        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} filing types, got {actual_count}"

    def test_amendment_coverage(self):
        """Test that major forms have amendment versions."""
        major_forms_with_amendments = [
            ("10-K", "10-K/A"),
            ("10-Q", "10-Q/A"),
            ("8-K", "8-K/A"),
        ]

        all_values = [ft.value for ft in FilingType]

        for base_form, amendment_form in major_forms_with_amendments:
            assert base_form in all_values, f"Missing base form: {base_form}"
            assert (
                amendment_form in all_values
            ), f"Missing amendment form: {amendment_form}"

    def test_form_categories_complete(self):
        """Test that all major SEC form categories are represented."""
        categories_and_examples = {
            "periodic_reports": ["10-K", "10-Q"],
            "current_reports": ["8-K"],
            "insider_trading": ["3", "4", "5"],
            "investment_management": ["13F"],
            "registration": ["S-1", "S-3", "S-4"],
            "proxy": ["DEF 14A", "DEFA14A"],
        }

        all_values = [ft.value for ft in FilingType]

        for category, examples in categories_and_examples.items():
            for example in examples:
                assert example in all_values, f"Missing {category} form: {example}"

    def test_no_duplicate_functionality(self):
        """Test that there are no duplicate or overlapping form definitions."""
        # Each form should serve a distinct purpose
        all_forms = list(FilingType)
        all_values = [ft.value for ft in all_forms]

        # No duplicate values
        assert len(all_values) == len(set(all_values))

        # No overlapping amendment relationships
        amendments = [ft for ft in all_forms if ft.is_amendment()]
        non_amendments = [ft for ft in all_forms if not ft.is_amendment()]

        # Each amendment should correspond to exactly one base form
        for amendment in amendments:
            base_value = amendment.value.replace("/A", "")
            matching_base_forms = [
                ft for ft in non_amendments if ft.value == base_value
            ]
            assert (
                len(matching_base_forms) == 1
            ), f"Amendment {amendment.value} should have exactly one base form"
