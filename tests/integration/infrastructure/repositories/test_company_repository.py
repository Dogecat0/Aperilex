"""Integration tests for CompanyRepository."""

import uuid

import pytest

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK


@pytest.mark.asyncio
class TestCompanyRepository:
    """Test CompanyRepository database operations."""

    async def test_create_company(self, company_repository, sample_company):
        """Test creating a new company."""
        # Act
        created = await company_repository.create(sample_company)
        await company_repository.commit()

        # Assert
        assert created.id == sample_company.id
        assert created.cik == sample_company.cik
        assert created.name == sample_company.name
        assert created.metadata == sample_company.metadata

    async def test_get_by_id(self, company_repository, sample_company):
        """Test retrieving company by ID."""
        # Arrange
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Act
        retrieved = await company_repository.get_by_id(sample_company.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == sample_company.id
        assert retrieved.cik == sample_company.cik
        assert retrieved.name == sample_company.name

    async def test_get_by_id_not_found(self, company_repository):
        """Test retrieving non-existent company."""
        # Act
        result = await company_repository.get_by_id(uuid.uuid4())

        # Assert
        assert result is None

    async def test_get_by_cik(self, company_repository, sample_company):
        """Test retrieving company by CIK."""
        # Arrange
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Act
        retrieved = await company_repository.get_by_cik(sample_company.cik)

        # Assert
        assert retrieved is not None
        assert retrieved.id == sample_company.id
        assert retrieved.cik == sample_company.cik

    async def test_find_by_name(self, company_repository):
        """Test finding companies by name."""
        # Arrange
        companies = [
            Company(
                id=uuid.uuid4(),
                cik=CIK("111111"),
                name="Apple Inc.",
                metadata={},
            ),
            Company(
                id=uuid.uuid4(),
                cik=CIK("222222"),
                name="Apple Bank",
                metadata={},
            ),
            Company(
                id=uuid.uuid4(),
                cik=CIK("333333"),
                name="Microsoft Corporation",
                metadata={},
            ),
        ]

        for company in companies:
            await company_repository.create(company)
        await company_repository.commit()

        # Act
        apple_companies = await company_repository.find_by_name("Apple")

        # Assert
        assert len(apple_companies) == 2
        assert all("Apple" in c.name for c in apple_companies)
        assert apple_companies[0].name == "Apple Bank"  # Sorted alphabetically
        assert apple_companies[1].name == "Apple Inc."

    async def test_find_by_name_case_insensitive(
        self, company_repository, sample_company
    ):
        """Test case-insensitive name search."""
        # Arrange
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Act
        results = await company_repository.find_by_name("APPLE")

        # Assert
        assert len(results) == 1
        assert results[0].name == sample_company.name

    async def test_update_company(self, company_repository, sample_company):
        """Test updating company information."""
        # Arrange
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Modify company
        sample_company._metadata["updated"] = True
        sample_company._metadata["sic_code"] = "3572"

        # Act
        await company_repository.update(sample_company)
        await company_repository.commit()

        # Retrieve and verify
        retrieved = await company_repository.get_by_id(sample_company.id)

        # Assert
        assert retrieved is not None
        assert retrieved.metadata["updated"] is True
        assert retrieved.metadata["sic_code"] == "3572"

    async def test_delete_company(self, company_repository, sample_company):
        """Test deleting a company."""
        # Arrange
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Act
        deleted = await company_repository.delete(sample_company.id)
        await company_repository.commit()

        # Assert
        assert deleted is True
        retrieved = await company_repository.get_by_id(sample_company.id)
        assert retrieved is None

    async def test_delete_non_existent(self, company_repository):
        """Test deleting non-existent company."""
        # Act
        result = await company_repository.delete(uuid.uuid4())

        # Assert
        assert result is False

    async def test_rollback(self, company_repository, sample_company):
        """Test transaction rollback."""
        # Act
        await company_repository.create(sample_company)
        await company_repository.rollback()

        # Assert
        retrieved = await company_repository.get_by_id(sample_company.id)
        assert retrieved is None
