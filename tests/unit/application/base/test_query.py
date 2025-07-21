"""Tests for BaseQuery infrastructure."""

import pytest
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import patch

from src.application.base.query import BaseQuery


@dataclass(frozen=True)
class TestQuery(BaseQuery):
    """Test query implementation for testing."""
    
    search_term: str = ""
    include_inactive: bool = False


@dataclass(frozen=True)
class FilingSearchQuery(BaseQuery):
    """Example filing search query."""
    
    company_name: str = ""
    filing_type: str = ""
    date_from: str = ""
    date_to: str = ""


class TestBaseQuery:
    """Test cases for BaseQuery infrastructure."""
    
    def test_query_creation_with_defaults(self):
        """Test creating a query with default values."""
        query = TestQuery()
        
        assert isinstance(query.query_id, UUID)
        assert isinstance(query.timestamp, datetime)
        assert query.user_id is None
        assert query.page == 1
        assert query.page_size == 20
        assert query.search_term == ""
        assert query.include_inactive is False
    
    def test_query_creation_with_explicit_values(self):
        """Test creating a query with explicit values."""
        query_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        user_id = "user123"
        
        query = TestQuery(
            query_id=query_id,
            timestamp=timestamp,
            user_id=user_id,
            page=3,
            page_size=50,
            search_term="financial",
            include_inactive=True
        )
        
        assert query.query_id == query_id
        assert query.timestamp == timestamp
        assert query.user_id == user_id
        assert query.page == 3
        assert query.page_size == 50
        assert query.search_term == "financial"
        assert query.include_inactive is True
    
    def test_query_immutability(self):
        """Test that queries are immutable (frozen dataclass)."""
        query = TestQuery(search_term="original", page=1)
        
        # Should not be able to modify query attributes
        with pytest.raises(AttributeError):
            query.search_term = "modified"
        
        with pytest.raises(AttributeError):
            query.page = 2
        
        with pytest.raises(AttributeError):
            query.query_id = uuid4()
    
    def test_pagination_validation_valid_values(self):
        """Test pagination validation with valid values."""
        # Minimum valid values
        query = TestQuery(page=1, page_size=1)
        assert query.page == 1
        assert query.page_size == 1
        
        # Maximum valid page size
        query = TestQuery(page=1, page_size=100)
        assert query.page_size == 100
        
        # Large page number (should be valid)
        query = TestQuery(page=1000, page_size=20)
        assert query.page == 1000
    
    def test_pagination_validation_invalid_page(self):
        """Test pagination validation with invalid page numbers."""
        # Page must be >= 1
        with pytest.raises(ValueError, match="Page must be >= 1"):
            TestQuery(page=0)
        
        with pytest.raises(ValueError, match="Page must be >= 1"):
            TestQuery(page=-1)
        
        with pytest.raises(ValueError, match="Page must be >= 1"):
            TestQuery(page=-100)
    
    def test_pagination_validation_invalid_page_size(self):
        """Test pagination validation with invalid page sizes."""
        # Page size must be >= 1
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=0)
        
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=-1)
        
        # Page size must be <= 100
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=101)
        
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            TestQuery(page_size=1000)
    
    def test_offset_calculation(self):
        """Test the offset property calculation."""
        # First page
        query = TestQuery(page=1, page_size=20)
        assert query.offset == 0
        
        # Second page
        query = TestQuery(page=2, page_size=20)
        assert query.offset == 20
        
        # Third page
        query = TestQuery(page=3, page_size=20)
        assert query.offset == 40
        
        # Different page size
        query = TestQuery(page=3, page_size=10)
        assert query.offset == 20
        
        # Large page number
        query = TestQuery(page=10, page_size=25)
        assert query.offset == 225
        
        # Minimum page size
        query = TestQuery(page=5, page_size=1)
        assert query.offset == 4
        
        # Maximum page size
        query = TestQuery(page=2, page_size=100)
        assert query.offset == 100
    
    def test_offset_calculation_edge_cases(self):
        """Test offset calculation edge cases."""
        # Page 1 should always have offset 0
        for page_size in [1, 10, 20, 50, 100]:
            query = TestQuery(page=1, page_size=page_size)
            assert query.offset == 0
        
        # Verify formula: offset = (page - 1) * page_size
        test_cases = [
            (1, 20, 0),     # (page - 1) * 20 = 0 * 20 = 0
            (2, 20, 20),    # (page - 1) * 20 = 1 * 20 = 20
            (5, 15, 60),    # (page - 1) * 15 = 4 * 15 = 60
            (10, 7, 63),    # (page - 1) * 7 = 9 * 7 = 63
        ]
        
        for page, page_size, expected_offset in test_cases:
            query = TestQuery(page=page, page_size=page_size)
            assert query.offset == expected_offset, \
                f"Page {page}, size {page_size} should have offset {expected_offset}, got {query.offset}"
    
    def test_query_id_uniqueness(self):
        """Test that each query gets a unique ID."""
        query1 = TestQuery()
        query2 = TestQuery()
        
        assert query1.query_id != query2.query_id
        assert isinstance(query1.query_id, UUID)
        assert isinstance(query2.query_id, UUID)
    
    def test_timestamp_generation(self):
        """Test that timestamps are automatically generated."""
        before = datetime.utcnow()
        query = TestQuery()
        after = datetime.utcnow()
        
        assert isinstance(query.timestamp, datetime)
        assert before <= query.timestamp <= after
    
    def test_user_id_tracking(self):
        """Test user ID for auditing purposes."""
        user_id = "user123"
        
        query = TestQuery(user_id=user_id)
        assert query.user_id == user_id
        
        # Default should be None
        query_no_user = TestQuery()
        assert query_no_user.user_id is None
    
    def test_query_equality_and_hashing(self):
        """Test query equality and hash behavior."""
        query_id = uuid4()
        timestamp = datetime.now()
        
        query1 = TestQuery(
            query_id=query_id,
            timestamp=timestamp,
            user_id="user1",
            page=2,
            page_size=30,
            search_term="test",
            include_inactive=True
        )
        
        query2 = TestQuery(
            query_id=query_id,
            timestamp=timestamp,
            user_id="user1",
            page=2,
            page_size=30,
            search_term="test",
            include_inactive=True
        )
        
        query3 = TestQuery(
            query_id=uuid4(),  # Different ID
            timestamp=timestamp,
            user_id="user1",
            page=2,
            page_size=30,
            search_term="test",
            include_inactive=True
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
    
    def test_pagination_combinations(self):
        """Test various pagination combinations."""
        # Common pagination scenarios
        scenarios = [
            (1, 10),    # First page, small size
            (1, 20),    # First page, default size
            (5, 20),    # Mid-range page
            (1, 100),   # First page, max size
            (100, 1),   # High page, min size
        ]
        
        for page, page_size in scenarios:
            query = TestQuery(page=page, page_size=page_size)
            assert query.page == page
            assert query.page_size == page_size
            expected_offset = (page - 1) * page_size
            assert query.offset == expected_offset
    
    def test_complex_query_example(self):
        """Test a more complex, realistic query."""
        query = FilingSearchQuery(
            user_id="analyst123",
            page=2,
            page_size=25,
            company_name="Apple Inc",
            filing_type="10-K",
            date_from="2023-01-01",
            date_to="2023-12-31"
        )
        
        assert query.user_id == "analyst123"
        assert query.page == 2
        assert query.page_size == 25
        assert query.offset == 25
        assert query.company_name == "Apple Inc"
        assert query.filing_type == "10-K"
        assert query.date_from == "2023-01-01"
        assert query.date_to == "2023-12-31"
        assert isinstance(query.query_id, UUID)
        assert isinstance(query.timestamp, datetime)
    
    def test_query_with_optional_filters(self):
        """Test queries with various optional filter combinations."""
        # Query with no filters
        query1 = FilingSearchQuery()
        assert query1.company_name == ""
        assert query1.filing_type == ""
        assert query1.date_from == ""
        assert query1.date_to == ""
        
        # Query with some filters
        query2 = FilingSearchQuery(
            company_name="Microsoft",
            filing_type="10-Q"
        )
        assert query2.company_name == "Microsoft"
        assert query2.filing_type == "10-Q"
        assert query2.date_from == ""
        assert query2.date_to == ""
        
        # Query with all filters
        query3 = FilingSearchQuery(
            company_name="Google",
            filing_type="8-K",
            date_from="2024-01-01",
            date_to="2024-06-30"
        )
        assert query3.company_name == "Google"
        assert query3.filing_type == "8-K"
        assert query3.date_from == "2024-01-01"
        assert query3.date_to == "2024-06-30"
    
    def test_post_init_validation_timing(self):
        """Test that __post_init__ is called during initialization."""
        validation_calls = []
        
        @dataclass(frozen=True)
        class TrackingQuery(BaseQuery):
            """Query that tracks post_init calls."""
            
            value: str = "test"
            
            def __post_init__(self):
                """Track when post_init is called and call parent."""
                validation_calls.append(f"Post init called with value: {self.value}")
                super().__post_init__()
        
        # Clear previous calls
        validation_calls.clear()
        
        # Create query - should trigger post_init
        query = TrackingQuery(value="tracked", page=2, page_size=30)
        
        assert len(validation_calls) == 1
        assert validation_calls[0] == "Post init called with value: tracked"
        assert query.value == "tracked"
        assert query.page == 2
        assert query.page_size == 30
        assert query.offset == 30
    
    def test_boundary_values_detailed(self):
        """Test boundary values in detail."""
        # Minimum valid values
        query = TestQuery(page=1, page_size=1)
        assert query.page == 1
        assert query.page_size == 1
        assert query.offset == 0
        
        # Maximum page size
        query = TestQuery(page=1, page_size=100)
        assert query.page == 1
        assert query.page_size == 100
        assert query.offset == 0
        
        # Large page with minimum size
        query = TestQuery(page=1000, page_size=1)
        assert query.page == 1000
        assert query.page_size == 1
        assert query.offset == 999
        
        # Large page with maximum size  
        query = TestQuery(page=50, page_size=100)
        assert query.page == 50
        assert query.page_size == 100
        assert query.offset == 4900
    
    def test_query_creation_performance(self):
        """Test that query creation is efficient for bulk operations."""
        # Create many queries to test performance
        queries = []
        for i in range(100):
            query = TestQuery(
                page=i + 1,
                page_size=20,
                search_term=f"term_{i}",
                include_inactive=i % 2 == 0
            )
            queries.append(query)
        
        # Verify all were created correctly
        assert len(queries) == 100
        
        # Check a few random ones
        assert queries[0].page == 1
        assert queries[0].search_term == "term_0"
        assert queries[0].include_inactive is True
        
        assert queries[50].page == 51
        assert queries[50].search_term == "term_50"
        assert queries[50].include_inactive is True  # 50 % 2 == 0, so True
        
        assert queries[99].page == 100
        assert queries[99].search_term == "term_99"
        assert queries[99].include_inactive is False  # 99 % 2 != 0, so False
        
        # All should have unique IDs
        query_ids = {q.query_id for q in queries}
        assert len(query_ids) == 100
    
    def test_query_string_representation(self):
        """Test query string representations."""
        query = TestQuery(
            page=3,
            page_size=25,
            search_term="financial analysis",
            include_inactive=True
        )
        
        # Should be able to convert to string
        query_str = str(query)
        assert "TestQuery" in query_str
        assert "page=3" in query_str
        assert "page_size=25" in query_str
        
        # Should be able to use repr
        query_repr = repr(query)
        assert "TestQuery" in query_repr