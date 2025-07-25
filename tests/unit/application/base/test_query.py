"""Tests for BaseQuery infrastructure."""

import pytest
from dataclasses import dataclass

from src.application.base.query import BaseQuery


@dataclass(frozen=True)
class TestQuery(BaseQuery):
    """Test query implementation."""
    
    search_term: str = ""
    limit: int = 10


@dataclass(frozen=True)
class SimpleQuery(BaseQuery):
    """Simple query for testing."""
    
    filter_value: str = "default"


class TestBaseQuery:
    """Test cases for BaseQuery infrastructure."""
    
    def test_query_creation_with_defaults(self):
        """Test creating a query with default values."""
        query = SimpleQuery()
        
        assert query.user_id is None
        assert query.page == 1
        assert query.page_size == 20
        assert query.filter_value == "default"
    
    def test_query_creation_with_explicit_values(self):
        """Test creating a query with explicit values."""
        user_id = "user123"
        page = 2
        page_size = 50
        
        query = SimpleQuery(
            user_id=user_id,
            page=page,
            page_size=page_size,
            filter_value="custom"
        )
        
        assert query.user_id == user_id
        assert query.page == page
        assert query.page_size == page_size
        assert query.filter_value == "custom"
    
    def test_query_pagination_defaults(self):
        """Test default pagination values."""
        query = SimpleQuery()
        
        assert query.page == 1
        assert query.page_size == 20
    
    def test_query_pagination_validation(self):
        """Test that built-in pagination validation works."""
        # Valid query should succeed
        query = TestQuery(search_term="test", limit=50, page=1, page_size=20)
        assert query.search_term == "test"
        assert query.limit == 50
        assert query.page == 1
        assert query.page_size == 20
        
        # Invalid page - zero
        with pytest.raises(ValueError, match="Page must be >= 1"):
            TestQuery(page=0)
        
        # Invalid page - negative
        with pytest.raises(ValueError, match="Page must be >= 1"):
            TestQuery(page=-1)
        
        # Invalid page size - zero
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=0)
        
        # Invalid page size - too high
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=101)
    
    def test_query_immutability(self):
        """Test that queries are immutable (frozen dataclass)."""
        query = SimpleQuery(filter_value="original")
        
        # Should not be able to modify query attributes
        with pytest.raises(AttributeError):
            query.filter_value = "modified"
        
        with pytest.raises(AttributeError):
            query.page = 2
        
        with pytest.raises(AttributeError):
            query.user_id = "new_user"
    
    def test_query_equality_and_hashing(self):
        """Test query equality and hash behavior."""
        query1 = SimpleQuery(
            user_id="user1", 
            page=1, 
            page_size=20, 
            filter_value="test"
        )
        query2 = SimpleQuery(
            user_id="user1", 
            page=1, 
            page_size=20, 
            filter_value="test"
        )
        query3 = SimpleQuery(
            user_id="user1", 
            page=2,  # Different page
            page_size=20, 
            filter_value="test"
        )
        
        # Same data should be equal
        assert query1 == query2
        
        # Different data should not be equal
        assert query1 != query3
        
        # Same data should have same hash
        assert hash(query1) == hash(query2)
        
        # Can be used in sets
        query_set = {query1, query2, query3}
        assert len(query_set) == 2  # query1 and query2 are identical
    
    def test_offset_calculation(self):
        """Test that offset property calculates correctly."""
        # Page 1, page_size 20 = offset 0
        query1 = SimpleQuery(page=1, page_size=20)
        assert query1.offset == 0
        
        # Page 2, page_size 20 = offset 20
        query2 = SimpleQuery(page=2, page_size=20)
        assert query2.offset == 20
        
        # Page 3, page_size 50 = offset 100
        query3 = SimpleQuery(page=3, page_size=50)
        assert query3.offset == 100
        
        # Page 1, page_size 1 = offset 0
        query4 = SimpleQuery(page=1, page_size=1)
        assert query4.offset == 0
    
    def test_complex_query_example(self):
        """Test a more complex query with multiple parameters."""
        @dataclass(frozen=True)
        class FilingSearchQuery(BaseQuery):
            """Complex filing search query."""
            
            company_name: str = ""
            filing_type: str = ""
            date_from: str = ""
            date_to: str = ""
            include_archived: bool = False
            
            def __post_init__(self):
                """Validate search parameters after BaseQuery validation."""
                super().__post_init__()  # Call BaseQuery validation first
                if not any([self.company_name, self.filing_type, self.date_from]):
                    raise ValueError("At least one search criterion is required")
        
        # Valid complex query
        query = FilingSearchQuery(
            company_name="Apple Inc",
            filing_type="10-K",
            page=2,
            page_size=25,
            include_archived=True
        )
        
        assert query.company_name == "Apple Inc"
        assert query.filing_type == "10-K"
        assert query.page == 2
        assert query.page_size == 25
        assert query.include_archived is True
        assert query.user_id is None
        
        # Invalid - no search criteria
        with pytest.raises(ValueError, match="At least one search criterion is required"):
            FilingSearchQuery()
        
        # Test that BaseQuery pagination validation still works
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            FilingSearchQuery(company_name="Apple Inc", page_size=101)
    
    def test_base_query_direct_instantiation(self):
        """Test that BaseQuery can be instantiated directly."""
        # BaseQuery is not abstract in the right-sized implementation
        query = BaseQuery(user_id="test", page=1, page_size=10)
        assert query.user_id == "test"
        assert query.page == 1
        assert query.page_size == 10
        assert query.offset == 0
    
    def test_user_id_tracking(self):
        """Test user ID for query auditing."""
        user_id = "analyst123"
        
        query = SimpleQuery(user_id=user_id)
        assert query.user_id == user_id
        
        # Default should be None
        query_no_user = SimpleQuery()
        assert query_no_user.user_id is None