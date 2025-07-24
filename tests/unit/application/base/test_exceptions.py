"""Tests for application layer exception infrastructure."""

import pytest

from src.application.base.exceptions import (
    ApplicationError,
    HandlerNotFoundError,
)


class TestApplicationError:
    """Test cases for base ApplicationError."""
    
    def test_application_error_creation(self):
        """Test creating a basic ApplicationError."""
        error = ApplicationError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_application_error_inheritance(self):
        """Test ApplicationError inherits from Exception."""
        error = ApplicationError("Test error")
        assert isinstance(error, Exception)
    
    def test_application_error_empty_message(self):
        """Test ApplicationError with empty message."""
        error = ApplicationError("")
        assert str(error) == ""
    
    def test_application_error_none_message(self):
        """Test ApplicationError with None message."""
        error = ApplicationError()
        assert isinstance(error, Exception)
    
    def test_application_error_raise_and_catch(self):
        """Test raising and catching ApplicationError."""
        with pytest.raises(ApplicationError) as exc_info:
            raise ApplicationError("Test error")
        
        assert str(exc_info.value) == "Test error"
        
        # Test catching as Exception
        try:
            raise ApplicationError("Test error")
        except Exception as e:
            assert isinstance(e, ApplicationError)
            assert str(e) == "Test error"
    
    def test_application_error_subclass_inheritance(self):
        """Test that all specific errors inherit from ApplicationError."""
        error_classes = [
            HandlerNotFoundError,
        ]
        
        for error_class in error_classes:
            assert issubclass(error_class, ApplicationError)
            assert issubclass(error_class, Exception)


class TestHandlerNotFoundError:
    """Test cases for HandlerNotFoundError."""
    
    def test_handler_not_found_error_creation(self):
        """Test creating HandlerNotFoundError."""
        request_type = "TestCommand"
        error = HandlerNotFoundError(request_type)
        
        assert error.request_type == request_type
        assert str(error) == f"No handler registered for {request_type}"
        assert isinstance(error, ApplicationError)
    
    def test_handler_not_found_error_with_different_types(self):
        """Test HandlerNotFoundError with various request types."""
        test_cases = [
            ("CreateUserCommand", "No handler registered for CreateUserCommand"),
            ("SearchFilingsQuery", "No handler registered for SearchFilingsQuery"),
            ("AnalyzeFilingCommand", "No handler registered for AnalyzeFilingCommand"),
            ("GetCompanyQuery", "No handler registered for GetCompanyQuery"),
        ]
        
        for request_type, expected_message in test_cases:
            error = HandlerNotFoundError(request_type)
            assert error.request_type == request_type
            assert str(error) == expected_message
    
    def test_handler_not_found_error_raise_and_catch(self):
        """Test raising and catching HandlerNotFoundError."""
        request_type = "UnknownCommand"
        
        with pytest.raises(HandlerNotFoundError) as exc_info:
            raise HandlerNotFoundError(request_type)
        
        assert exc_info.value.request_type == request_type
        assert "No handler registered for UnknownCommand" in str(exc_info.value)
        
        # Test catching as ApplicationError
        try:
            raise HandlerNotFoundError(request_type)
        except ApplicationError as e:
            assert isinstance(e, HandlerNotFoundError)
            assert e.request_type == request_type
    
    def test_handler_not_found_error_attributes(self):
        """Test HandlerNotFoundError attributes are correctly set."""
        request_type = "ComplexCommand"
        error = HandlerNotFoundError(request_type)
        
        assert hasattr(error, 'request_type')
        assert error.request_type == request_type
        
        # Test that it behaves like a regular exception
        assert str(error)
        assert repr(error)