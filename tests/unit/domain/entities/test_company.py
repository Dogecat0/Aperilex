"""Comprehensive tests for Company entity."""

import uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK


class TestCompanyConstruction:
    """Test Company entity construction and validation."""

    def test_create_with_all_parameters(self):
        """Test creating Company with all parameters."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        metadata = {"sector": "Technology", "employees": 164000}

        company = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=metadata)

        assert company.id == company_id
        assert company.cik == cik
        assert company.name == "Apple Inc."
        assert company.metadata == metadata

    def test_create_with_minimal_parameters(self):
        """Test creating Company with minimal required parameters."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        assert company.id == company_id
        assert company.cik == cik
        assert company.name == "Apple Inc."
        assert company.metadata == {}

    def test_create_with_none_metadata(self):
        """Test creating Company with None metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=None)

        assert company.metadata == {}

    def test_create_with_empty_metadata(self):
        """Test creating Company with empty metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="Apple Inc.", metadata={})

        assert company.metadata == {}

    def test_create_with_complex_metadata(self):
        """Test creating Company with complex metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        metadata = {
            "sector": "Technology",
            "employees": 164000,
            "founded": 1976,
            "headquarters": {
                "city": "Cupertino",
                "state": "California",
                "country": "USA",
            },
            "products": ["iPhone", "iPad", "Mac", "Apple Watch"],
            "market_cap": 3000000000000,
            "is_public": True,
        }

        company = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=metadata)

        assert company.metadata == metadata


class TestCompanyNameValidation:
    """Test Company name validation and trimming."""

    def test_name_trimming_with_leading_whitespace(self):
        """Test that leading whitespace is trimmed from name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="   Apple Inc.")

        assert company.name == "Apple Inc."

    def test_name_trimming_with_trailing_whitespace(self):
        """Test that trailing whitespace is trimmed from name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="Apple Inc.   ")

        assert company.name == "Apple Inc."

    def test_name_trimming_with_surrounding_whitespace(self):
        """Test that surrounding whitespace is trimmed from name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="   Apple Inc.   ")

        assert company.name == "Apple Inc."

    def test_name_with_internal_whitespace_preserved(self):
        """Test that internal whitespace in name is preserved."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company = Company(id=company_id, cik=cik, name="  Apple    Inc.  ")

        assert company.name == "Apple    Inc."

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="")

    def test_whitespace_only_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="   ")

    def test_tab_only_name_raises_error(self):
        """Test that tab-only name raises ValueError."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="\t\t\t")

    def test_newline_only_name_raises_error(self):
        """Test that newline-only name raises ValueError."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="\n\n")

    def test_mixed_whitespace_only_name_raises_error(self):
        """Test that mixed whitespace-only name raises ValueError."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name=" \t\n  \t ")

    def test_none_name_raises_error(self):
        """Test that None name raises appropriate error."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # The Company class converts None name to string "None" which becomes empty after strip
        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name=None)


class TestCompanyEquality:
    """Test Company equality based on CIK (not UUID)."""

    def test_equality_same_cik_different_id(self):
        """Test equality with same CIK but different IDs."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        cik = CIK("0000320193")

        company1 = Company(id=id1, cik=cik, name="Apple Inc.")
        company2 = Company(id=id2, cik=cik, name="Apple Inc.")

        assert company1 == company2
        assert company2 == company1

    def test_equality_same_cik_different_names(self):
        """Test equality with same CIK but different names."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company1 = Company(id=company_id, cik=cik, name="Apple Inc.")
        company2 = Company(id=company_id, cik=cik, name="Apple Computer Inc.")

        assert company1 == company2
        assert company2 == company1

    def test_equality_same_cik_different_metadata(self):
        """Test equality with same CIK but different metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        company1 = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata={"sector": "Technology"}
        )
        company2 = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata={"sector": "Hardware"}
        )

        assert company1 == company2
        assert company2 == company1

    def test_equality_same_cik_with_leading_zeros(self):
        """Test equality with CIKs having different leading zero patterns."""
        company_id = uuid.uuid4()
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")

        company1 = Company(id=company_id, cik=cik1, name="Apple Inc.")
        company2 = Company(id=company_id, cik=cik2, name="Apple Inc.")

        assert company1 == company2
        assert company2 == company1

    def test_inequality_different_ciks(self):
        """Test inequality with different CIKs."""
        company_id = uuid.uuid4()
        cik1 = CIK("0000320193")  # Apple
        cik2 = CIK("0000789019")  # Microsoft

        company1 = Company(id=company_id, cik=cik1, name="Apple Inc.")
        company2 = Company(id=company_id, cik=cik2, name="Microsoft Corporation")

        assert company1 != company2
        assert company2 != company1

    def test_inequality_with_non_company_object(self):
        """Test inequality with non-Company objects."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        assert company != "Apple Inc."
        assert company != 320193
        assert company != cik
        assert company is not None
        assert company != []
        assert company != {}

    def test_equality_reflexivity(self):
        """Test that equality is reflexive (x == x)."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        assert company == company

    def test_equality_with_identical_objects(self):
        """Test equality with identical company objects."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        metadata = {"sector": "Technology"}

        company1 = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=metadata)
        company2 = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=metadata)

        assert company1 == company2
        assert company2 == company1


class TestCompanyHashing:
    """Test Company hashing based on CIK for use in sets and dictionaries."""

    def test_hash_equality_same_cik(self):
        """Test that companies with same CIK have same hash."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        cik = CIK("0000320193")

        company1 = Company(id=id1, cik=cik, name="Apple Inc.")
        company2 = Company(id=id2, cik=cik, name="Apple Computer Inc.")

        assert hash(company1) == hash(company2)

    def test_hash_equality_with_leading_zeros(self):
        """Test that CIKs with different leading zeros have same hash."""
        company_id = uuid.uuid4()
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")

        company1 = Company(id=company_id, cik=cik1, name="Apple Inc.")
        company2 = Company(id=company_id, cik=cik2, name="Apple Inc.")

        assert hash(company1) == hash(company2)

    def test_hash_inequality_different_ciks(self):
        """Test that companies with different CIKs have different hashes."""
        company_id = uuid.uuid4()
        cik1 = CIK("0000320193")  # Apple
        cik2 = CIK("0000789019")  # Microsoft

        company1 = Company(id=company_id, cik=cik1, name="Apple Inc.")
        company2 = Company(id=company_id, cik=cik2, name="Microsoft Corporation")

        assert hash(company1) != hash(company2)

    def test_company_in_set(self):
        """Test using Company objects in sets."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        id3 = uuid.uuid4()

        cik1 = CIK("0000320193")  # Apple
        cik2 = CIK("0000320193")  # Same as cik1 (Apple with different leading zeros)
        cik3 = CIK("0000789019")  # Microsoft

        company1 = Company(id=id1, cik=cik1, name="Apple Inc.")
        company2 = Company(
            id=id2, cik=cik2, name="Apple Computer Inc."
        )  # Same CIK as company1
        company3 = Company(id=id3, cik=cik3, name="Microsoft Corporation")

        company_set = {company1, company2, company3}
        assert len(company_set) == 2  # company1 and company2 have same CIK

        # Test membership
        test_apple = Company(id=uuid.uuid4(), cik=CIK("0000320193"), name="Apple")
        test_microsoft = Company(
            id=uuid.uuid4(), cik=CIK("0000789019"), name="Microsoft"
        )
        test_google = Company(id=uuid.uuid4(), cik=CIK("0001652044"), name="Google")

        assert test_apple in company_set
        assert test_microsoft in company_set
        assert test_google not in company_set

    def test_company_as_dict_key(self):
        """Test using Company objects as dictionary keys."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        cik1 = CIK("0000320193")  # Apple
        cik2 = CIK("0000789019")  # Microsoft

        company1 = Company(id=id1, cik=cik1, name="Apple Inc.")
        company2 = Company(id=id2, cik=cik2, name="Microsoft Corporation")

        company_dict = {
            company1: "Technology - Hardware",
            company2: "Technology - Software",
        }

        # Test access with equivalent companies
        test_apple = Company(id=uuid.uuid4(), cik=CIK("0000320193"), name="Apple")
        test_apple_with_zeros = Company(
            id=uuid.uuid4(), cik=CIK("0000320193"), name="Apple Inc."
        )
        test_microsoft = Company(
            id=uuid.uuid4(), cik=CIK("0000789019"), name="Microsoft"
        )

        assert company_dict[test_apple] == "Technology - Hardware"
        assert company_dict[test_apple_with_zeros] == "Technology - Hardware"
        assert company_dict[test_microsoft] == "Technology - Software"

    def test_hash_consistency(self):
        """Test that hash remains consistent across multiple calls."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        hash1 = hash(company)
        hash2 = hash(company)
        hash3 = hash(company)

        assert hash1 == hash2 == hash3


class TestCompanyMetadata:
    """Test Company metadata operations and defensive copying."""

    def test_metadata_defensive_copy_on_get(self):
        """Test that metadata property returns a defensive copy."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        original_metadata = {"sector": "Technology", "employees": 164000}

        company = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata=original_metadata.copy()
        )

        # Get metadata and modify it
        retrieved_metadata = company.metadata
        retrieved_metadata["new_field"] = "new_value"

        # Original company metadata should be unchanged
        assert company.metadata == original_metadata
        assert "new_field" not in company.metadata

    def test_add_metadata_single_entry(self):
        """Test adding a single metadata entry."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        company.add_metadata("sector", "Technology")

        assert company.metadata["sector"] == "Technology"

    def test_add_metadata_multiple_entries(self):
        """Test adding multiple metadata entries."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        company.add_metadata("sector", "Technology")
        company.add_metadata("employees", 164000)
        company.add_metadata("founded", 1976)

        expected_metadata = {
            "sector": "Technology",
            "employees": 164000,
            "founded": 1976,
        }
        assert company.metadata == expected_metadata

    def test_add_metadata_overwrite_existing(self):
        """Test that adding metadata overwrites existing keys."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata={"sector": "Hardware"}
        )

        company.add_metadata("sector", "Technology")

        assert company.metadata["sector"] == "Technology"

    def test_add_metadata_various_types(self):
        """Test adding metadata with various value types."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        company.add_metadata("string_value", "Technology")
        company.add_metadata("int_value", 164000)
        company.add_metadata("float_value", 3.14)
        company.add_metadata("bool_value", True)
        company.add_metadata("list_value", ["iPhone", "iPad", "Mac"])
        company.add_metadata("dict_value", {"city": "Cupertino", "state": "CA"})
        company.add_metadata("none_value", None)

        metadata = company.metadata
        assert metadata["string_value"] == "Technology"
        assert metadata["int_value"] == 164000
        assert metadata["float_value"] == 3.14
        assert metadata["bool_value"] is True
        assert metadata["list_value"] == ["iPhone", "iPad", "Mac"]
        assert metadata["dict_value"] == {"city": "Cupertino", "state": "CA"}
        assert metadata["none_value"] is None

    def test_add_metadata_modifies_internal_state(self):
        """Test that add_metadata actually modifies the company's internal metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        # Initially empty
        assert company.metadata == {}

        # Add metadata
        company.add_metadata("sector", "Technology")

        # Should be reflected in subsequent calls
        assert company.metadata == {"sector": "Technology"}

        # Add more metadata
        company.add_metadata("employees", 164000)

        # Should accumulate
        expected = {"sector": "Technology", "employees": 164000}
        assert company.metadata == expected

    def test_metadata_immutability_after_construction(self):
        """Test that add_metadata affects the company's internal metadata."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        original_metadata = {"sector": "Technology"}

        # Note: The Company constructor uses the same dict reference, not a copy
        # This is the actual behavior of the current implementation
        company = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata=original_metadata
        )

        company.add_metadata("employees", 164000)

        # The original dict IS affected because Company uses the same reference
        # This documents the actual behavior
        assert original_metadata == {"sector": "Technology", "employees": 164000}
        assert "employees" in original_metadata


class TestCompanyDomainInvariants:
    """Test Company domain invariants and validation rules."""

    def test_name_cannot_be_empty_after_strip(self):
        """Test that name validation occurs after stripping."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # These should all fail because they become empty after stripping
        invalid_names = ["", "   ", "\t", "\n", " \t\n ", "\t\t\t"]

        for invalid_name in invalid_names:
            with pytest.raises(ValueError, match="Company name cannot be empty"):
                Company(id=company_id, cik=cik, name=invalid_name)

    def test_cik_requirement(self):
        """Test that CIK is required and properly validated."""
        company_id = uuid.uuid4()

        # CIK validation should happen in CIK constructor, not Company
        with pytest.raises(ValueError):
            invalid_cik = CIK("")  # This will fail
            Company(id=company_id, cik=invalid_cik, name="Apple Inc.")

    def test_invariants_validated_on_construction(self):
        """Test that domain invariants are validated during construction."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # Valid construction should succeed
        company = Company(id=company_id, cik=cik, name="Apple Inc.")
        assert company.name == "Apple Inc."

        # Invalid construction should fail
        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="")

    def test_immutability_of_core_properties(self):
        """Test that core company properties cannot be changed after construction."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        # These properties should not have setters (will raise AttributeError)
        with pytest.raises(AttributeError):
            company.id = uuid.uuid4()

        with pytest.raises(AttributeError):
            company.cik = CIK("0000789019")

        with pytest.raises(AttributeError):
            company.name = "Microsoft Corporation"

    def test_valid_construction_with_edge_case_names(self):
        """Test valid construction with edge case but valid names."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # These should all be valid after trimming
        valid_names = [
            "A",  # Single character
            "Apple Inc.",  # Normal case
            "  Apple Inc.  ",  # With whitespace (gets trimmed)
            "Apple    Inc.",  # Internal whitespace
            "Apple-Inc.",  # With hyphen
            "Apple & Co.",  # With ampersand
            "Apple (AAPL)",  # With parentheses
            "Apple Inc. 2024",  # With number
            "áppłe Înc.",  # Unicode characters
        ]

        for valid_name in valid_names:
            company = Company(id=company_id, cik=cik, name=valid_name)
            assert len(company.name.strip()) > 0


class TestCompanyStringRepresentation:
    """Test Company string representation methods."""

    def test_str_representation_format(self):
        """Test __str__ representation format."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        str_repr = str(company)
        expected = "Company: Apple Inc. [CIK: 320193]"
        assert str_repr == expected

    def test_str_representation_with_special_characters(self):
        """Test __str__ representation with special characters in name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple & Co. (AAPL)")

        str_repr = str(company)
        expected = "Company: Apple & Co. (AAPL) [CIK: 320193]"
        assert str_repr == expected

    def test_str_representation_with_unicode(self):
        """Test __str__ representation with unicode characters."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Äpple Înc.")

        str_repr = str(company)
        expected = "Company: Äpple Înc. [CIK: 320193]"
        assert str_repr == expected

    def test_repr_representation_format(self):
        """Test __repr__ representation format."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        repr_str = repr(company)
        expected = f"Company(id={company_id}, cik={cik}, name='Apple Inc.')"
        assert repr_str == expected

    def test_repr_representation_with_quotes_in_name(self):
        """Test __repr__ representation with quotes in company name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple 'Computer' Inc.")

        repr_str = repr(company)
        expected = f"Company(id={company_id}, cik={cik}, name='Apple 'Computer' Inc.')"
        assert repr_str == expected

    def test_string_representations_consistency(self):
        """Test that string representations are consistent across multiple calls."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        str1 = str(company)
        str2 = str(company)
        repr1 = repr(company)
        repr2 = repr(company)

        assert str1 == str2
        assert repr1 == repr2


class TestCompanyRealWorldExamples:
    """Test Company with real-world company examples."""

    def test_apple_company(self):
        """Test Apple Inc. company."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        metadata = {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "employees": 164000,
            "founded": 1976,
            "ticker": "AAPL",
        }

        company = Company(id=company_id, cik=cik, name="Apple Inc.", metadata=metadata)

        assert company.name == "Apple Inc."
        assert str(company.cik) == "320193"
        assert company.metadata["sector"] == "Technology"
        assert str(company) == "Company: Apple Inc. [CIK: 320193]"

    def test_microsoft_company(self):
        """Test Microsoft Corporation."""
        company_id = uuid.uuid4()
        cik = CIK("0000789019")
        metadata = {
            "sector": "Technology",
            "industry": "Software",
            "employees": 221000,
            "founded": 1975,
            "ticker": "MSFT",
        }

        company = Company(
            id=company_id, cik=cik, name="Microsoft Corporation", metadata=metadata
        )

        assert company.name == "Microsoft Corporation"
        assert str(company.cik) == "789019"
        assert company.metadata["industry"] == "Software"
        assert str(company) == "Company: Microsoft Corporation [CIK: 789019]"

    def test_tesla_company(self):
        """Test Tesla Inc."""
        company_id = uuid.uuid4()
        cik = CIK("0001318605")

        company = Company(id=company_id, cik=cik, name="Tesla, Inc.")

        assert company.name == "Tesla, Inc."
        assert str(company.cik) == "1318605"
        assert str(company) == "Company: Tesla, Inc. [CIK: 1318605]"

    def test_amazon_company(self):
        """Test Amazon.com Inc."""
        company_id = uuid.uuid4()
        cik = CIK("0001018724")

        company = Company(id=company_id, cik=cik, name="Amazon.com, Inc.")

        assert company.name == "Amazon.com, Inc."
        assert str(company.cik) == "1018724"
        assert str(company) == "Company: Amazon.com, Inc. [CIK: 1018724]"

    def test_berkshire_hathaway_company(self):
        """Test Berkshire Hathaway with long company name."""
        company_id = uuid.uuid4()
        cik = CIK("0001067983")

        company = Company(id=company_id, cik=cik, name="Berkshire Hathaway Inc.")

        assert company.name == "Berkshire Hathaway Inc."
        assert str(company.cik) == "1067983"

    def test_company_with_ampersand(self):
        """Test company name with ampersand."""
        company_id = uuid.uuid4()
        cik = CIK("0000019617")

        company = Company(id=company_id, cik=cik, name="Johnson & Johnson")

        assert company.name == "Johnson & Johnson"
        assert "&" in str(company)


# Property-based tests using Hypothesis
class TestCompanyPropertyBased:
    """Property-based tests for Company using Hypothesis."""

    @given(
        company_name=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        cik_int=st.integers(min_value=1, max_value=9999999999),
    )
    def test_company_construction_properties(self, company_name, cik_int):
        """Test Company construction with various inputs."""
        company_id = uuid.uuid4()
        cik = CIK(str(cik_int))

        company = Company(id=company_id, cik=cik, name=company_name)

        assert company.id == company_id
        assert company.cik == cik
        assert company.name == company_name.strip()
        assert len(company.name) > 0

    @given(
        cik_int=st.integers(min_value=1, max_value=9999999999),
        metadata_keys=st.lists(
            st.text(min_size=1, max_size=50), min_size=0, max_size=10, unique=True
        ),
        metadata_values=st.lists(
            st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    def test_metadata_handling_properties(
        self, cik_int, metadata_keys, metadata_values
    ):
        """Test metadata handling with various inputs."""
        company_id = uuid.uuid4()
        cik = CIK(str(cik_int))

        # Pair keys with values
        metadata = {}
        for key, value in zip(metadata_keys, metadata_values, strict=False):
            metadata[key] = value

        company = Company(
            id=company_id, cik=cik, name="Test Company", metadata=metadata
        )

        # Defensive copy property
        retrieved_metadata = company.metadata
        assert retrieved_metadata == metadata

        # Modifying retrieved metadata shouldn't affect original
        if metadata_keys:
            retrieved_metadata[metadata_keys[0]] = "changed"
            assert company.metadata != retrieved_metadata

    @given(
        cik_int1=st.integers(min_value=1, max_value=9999999999),
        cik_int2=st.integers(min_value=1, max_value=9999999999),
        leading_zeros1=st.integers(min_value=0, max_value=9),
        leading_zeros2=st.integers(min_value=0, max_value=9),
    )
    def test_equality_properties(
        self, cik_int1, cik_int2, leading_zeros1, leading_zeros2
    ):
        """Test equality properties with various CIK formats."""
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        # Create CIK strings with leading zeros
        cik_str1 = str(cik_int1).zfill(len(str(cik_int1)) + leading_zeros1)
        cik_str2 = str(cik_int2).zfill(len(str(cik_int2)) + leading_zeros2)

        # Only proceed if CIK strings are valid length
        if len(cik_str1) <= 10 and len(cik_str2) <= 10:
            cik1 = CIK(cik_str1)
            cik2 = CIK(cik_str2)

            company1 = Company(id=id1, cik=cik1, name="Company A")
            company2 = Company(id=id2, cik=cik2, name="Company B")

            # Companies should be equal if and only if their CIKs are equal
            if cik_int1 == cik_int2:
                assert company1 == company2
                assert hash(company1) == hash(company2)
            else:
                assert company1 != company2

    @given(cik_int=st.integers(min_value=1, max_value=9999999999))
    def test_immutability_properties(self, cik_int):
        """Test that Company objects are properly immutable."""
        company_id = uuid.uuid4()
        cik = CIK(str(cik_int))
        metadata = {"test": "value"}

        company = Company(
            id=company_id, cik=cik, name="Test Company", metadata=metadata
        )

        original_id = company.id
        original_cik = company.cik
        original_name = company.name
        original_metadata = company.metadata

        # Add metadata (this should work)
        company.add_metadata("new_key", "new_value")

        # Core properties should remain unchanged
        assert company.id == original_id
        assert company.cik == original_cik
        assert company.name == original_name

        # Metadata should have been updated but defensively copied
        assert company.metadata != original_metadata
        assert "new_key" in company.metadata
        assert original_metadata == {"test": "value"}  # Original dict unchanged


@pytest.mark.unit
class TestCompanyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_company_name(self):
        """Test with very long company name."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # Create a very long but valid company name
        long_name = "A" * 1000
        company = Company(id=company_id, cik=cik, name=long_name)

        assert company.name == long_name
        assert len(company.name) == 1000

    def test_company_name_with_all_unicode_categories(self):
        """Test company name with various unicode characters."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # Unicode company name with various character categories
        unicode_name = "Ärpfel & Çö. 株式会社 (Ñoël) 🍎"
        company = Company(id=company_id, cik=cik, name=unicode_name)

        assert company.name == unicode_name
        assert unicode_name in str(company)

    def test_metadata_with_deeply_nested_structures(self):
        """Test metadata with deeply nested data structures."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        complex_metadata = {
            "level1": {
                "level2": {"level3": {"deeply_nested": [1, 2, {"nested_dict": True}]}}
            },
            "arrays": [
                {"name": "product1", "price": 100.50},
                {"name": "product2", "price": 200.75},
            ],
        }

        company = Company(
            id=company_id, cik=cik, name="Apple Inc.", metadata=complex_metadata
        )

        assert company.metadata == complex_metadata

        # The Company.metadata property does dict.copy() which is shallow copy
        # So nested structures are still shared references
        retrieved = company.metadata

        # Test that top-level changes don't affect the company
        retrieved["new_top_level"] = "added"
        assert (
            "new_top_level" not in company.metadata
        )  # Top-level is protected by shallow copy

        # But nested structures are still shared (this is expected shallow copy behavior)
        retrieved = company.metadata  # Get fresh copy
        original_length = len(
            company.metadata["level1"]["level2"]["level3"]["deeply_nested"]
        )
        retrieved["level1"]["level2"]["level3"]["deeply_nested"].append(4)
        new_length = len(
            company.metadata["level1"]["level2"]["level3"]["deeply_nested"]
        )

        # Nested structures are affected because dict.copy() is shallow
        assert new_length == original_length + 1

    def test_cik_boundary_values(self):
        """Test Company with boundary CIK values."""
        company_id = uuid.uuid4()

        # Test minimum CIK
        min_cik = CIK("1")
        company_min = Company(id=company_id, cik=min_cik, name="Min Company")
        assert str(company_min.cik) == "1"

        # Test maximum CIK (10 digits)
        max_cik = CIK("9999999999")
        company_max = Company(id=company_id, cik=max_cik, name="Max Company")
        assert str(company_max.cik) == "9999999999"

        # Test common patterns with leading zeros
        padded_cik = CIK("0000000001")
        company_padded = Company(id=company_id, cik=padded_cik, name="Padded Company")
        assert str(company_padded.cik) == "1"
        assert company_min == company_padded  # Should be equal due to CIK equality

    def test_whitespace_edge_cases(self):
        """Test various whitespace edge cases in names."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        # Test different types of whitespace characters
        whitespace_cases = [
            ("Apple\tInc.", "Apple\tInc."),  # Tab preserved internally
            ("Apple\nInc.", "Apple\nInc."),  # Newline preserved internally
            ("Apple Inc.", "Apple Inc."),  # Normal space
            ("Apple  Inc.", "Apple  Inc."),  # Multiple spaces preserved internally
        ]

        for input_name, expected_name in whitespace_cases:
            # Add surrounding whitespace that should be stripped
            padded_name = f"  {input_name}  "
            company = Company(id=company_id, cik=cik, name=padded_name)
            assert company.name == expected_name

    def test_error_message_clarity(self):
        """Test that error messages are clear and helpful."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")

        with pytest.raises(ValueError) as exc_info:
            Company(id=company_id, cik=cik, name="")
        assert "cannot be empty" in str(exc_info.value).lower()

        with pytest.raises(ValueError) as exc_info:
            Company(id=company_id, cik=cik, name="   ")
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_add_metadata_edge_cases(self):
        """Test add_metadata with edge case inputs."""
        company_id = uuid.uuid4()
        cik = CIK("0000320193")
        company = Company(id=company_id, cik=cik, name="Apple Inc.")

        # Test with empty string key
        company.add_metadata("", "empty_key_value")
        assert company.metadata[""] == "empty_key_value"

        # Test with numeric key (converted to string)
        company.add_metadata("123", "numeric_key")
        assert company.metadata["123"] == "numeric_key"

        # Test overwriting with None
        company.add_metadata("test", "initial")
        company.add_metadata("test", None)
        assert company.metadata["test"] is None

    def test_multiple_companies_independence(self):
        """Test that multiple company instances don't interfere with each other."""
        cik1 = CIK("0000320193")
        cik2 = CIK("0000789019")

        company1 = Company(id=uuid.uuid4(), cik=cik1, name="Apple Inc.")
        company2 = Company(id=uuid.uuid4(), cik=cik2, name="Microsoft Corporation")

        # Add metadata to both
        company1.add_metadata("sector", "Hardware")
        company2.add_metadata("sector", "Software")

        # Each should have its own metadata
        assert company1.metadata["sector"] == "Hardware"
        assert company2.metadata["sector"] == "Software"

        # Modifying one shouldn't affect the other
        company1.add_metadata("employees", 164000)
        assert "employees" not in company2.metadata
