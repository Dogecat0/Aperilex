"""Tests for Company entity."""

from uuid import uuid4

import pytest

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK


class TestCompany:
    """Test cases for Company entity."""

    def test_init_with_valid_data(self):
        """Test Company initialization with valid data."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        assert company.id == company_id
        assert company.cik == cik
        assert company.name == name
        assert company.metadata == {}

    def test_init_with_metadata(self):
        """Test Company initialization with metadata."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."
        metadata = {"sector": "Technology", "industry": "Consumer Electronics"}

        company = Company(id=company_id, cik=cik, name=name, metadata=metadata)

        assert company.id == company_id
        assert company.cik == cik
        assert company.name == name
        assert company.metadata == metadata

    def test_init_with_invalid_name(self):
        """Test Company initialization with invalid name."""
        company_id = uuid4()
        cik = CIK("0000320193")

        # Empty name
        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="")

        # Whitespace only name
        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(id=company_id, cik=cik, name="   ")

    def test_name_trimming(self):
        """Test that company name is trimmed of whitespace."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "  Apple Inc.  "

        company = Company(id=company_id, cik=cik, name=name)

        assert company.name == "Apple Inc."

    def test_add_metadata(self):
        """Test adding metadata to company."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        company.add_metadata("sector", "Technology")
        company.add_metadata("founded", "1976")

        assert company.metadata["sector"] == "Technology"
        assert company.metadata["founded"] == "1976"

    def test_metadata_isolation(self):
        """Test that metadata property returns a copy."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)
        company.add_metadata("sector", "Technology")

        # Get metadata copy
        metadata = company.metadata
        metadata["sector"] = "Modified"

        # Original metadata should be unchanged
        assert company.metadata["sector"] == "Technology"

    def test_equality(self):
        """Test Company equality based on CIK."""
        company_id_1 = uuid4()
        company_id_2 = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company1 = Company(id=company_id_1, cik=cik, name=name)
        company2 = Company(id=company_id_2, cik=cik, name=name)

        # Same CIK should be equal
        assert company1 == company2

        # Different CIK should not be equal
        different_cik = CIK("0000789019")
        company3 = Company(id=uuid4(), cik=different_cik, name="Microsoft Corp.")
        assert company1 != company3

        # Different type should not be equal
        assert company1 != "Apple Inc."
        assert company1 is not None

    def test_hash(self):
        """Test Company hash based on CIK."""
        company_id_1 = uuid4()
        company_id_2 = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company1 = Company(id=company_id_1, cik=cik, name=name)
        company2 = Company(id=company_id_2, cik=cik, name=name)

        # Same CIK should have same hash
        assert hash(company1) == hash(company2)

        # Different CIK should have different hash
        different_cik = CIK("0000789019")
        company3 = Company(id=uuid4(), cik=different_cik, name="Microsoft Corp.")
        assert hash(company1) != hash(company3)

        # Test in set
        company_set = {company1, company2, company3}
        assert len(company_set) == 2  # company1 and company2 are same CIK

    def test_str_representation(self):
        """Test Company string representation."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        expected = f"Company: {name} [CIK: {cik}]"
        assert str(company) == expected

    def test_repr_representation(self):
        """Test Company repr representation."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        expected = f"Company(id={company_id}, cik={cik}, name='{name}')"
        assert repr(company) == expected

    def test_real_world_examples(self):
        """Test with real-world company examples."""
        # Apple Inc.
        apple_id = uuid4()
        apple_cik = CIK("0000320193")
        apple = Company(id=apple_id, cik=apple_cik, name="Apple Inc.")

        assert apple.name == "Apple Inc."
        assert apple.cik.value == "0000320193"

        # Microsoft Corp.
        msft_id = uuid4()
        msft_cik = CIK("0000789019")
        msft = Company(id=msft_id, cik=msft_cik, name="Microsoft Corporation")

        assert msft.name == "Microsoft Corporation"
        assert msft.cik.value == "0000789019"

        # Different companies should not be equal
        assert apple != msft

    def test_edge_cases(self):
        """Test edge cases for Company."""
        # Very short name
        short_name_id = uuid4()
        short_cik = CIK("1")
        short_company = Company(id=short_name_id, cik=short_cik, name="A")
        assert short_company.name == "A"

        # Very long name
        long_name_id = uuid4()
        long_cik = CIK("1234567890")
        long_name = "A" * 500
        long_company = Company(id=long_name_id, cik=long_cik, name=long_name)
        assert long_company.name == long_name

    def test_metadata_operations(self):
        """Test various metadata operations."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        # Add various metadata types
        company.add_metadata("sector", "Technology")
        company.add_metadata("employees", 147000)
        company.add_metadata("founded", 1976)
        company.add_metadata("public", True)
        company.add_metadata("subsidiaries", ["Apple Services", "Apple Retail"])

        metadata = company.metadata
        assert metadata["sector"] == "Technology"
        assert metadata["employees"] == 147000
        assert metadata["founded"] == 1976
        assert metadata["public"] is True
        assert metadata["subsidiaries"] == ["Apple Services", "Apple Retail"]

    def test_immutability_of_core_attributes(self):
        """Test that core attributes are immutable after construction."""
        company_id = uuid4()
        cik = CIK("0000320193")
        name = "Apple Inc."

        company = Company(id=company_id, cik=cik, name=name)

        # Core attributes should be accessible but not modifiable
        assert company.id == company_id
        assert company.cik == cik
        assert company.name == name

        # The company should not have public setters for core attributes
        assert not hasattr(company, 'set_id')
        assert not hasattr(company, 'set_cik')
        assert not hasattr(company, 'set_name')
