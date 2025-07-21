"""Tests for application layer exception infrastructure."""

import pytest

from src.application.base.exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    DependencyError,
    HandlerNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)


class TestApplicationError:
    """Test cases for base ApplicationError."""
    
    def test_application_error_inheritance(self):
        """Test that ApplicationError inherits from Exception."""
        assert issubclass(ApplicationError, Exception)
        
        error = ApplicationError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, ApplicationError)
    
    def test_application_error_message(self):
        """Test ApplicationError message handling."""
        message = "Something went wrong"
        error = ApplicationError(message)
        
        assert str(error) == message
        assert error.args == (message,)
    
    def test_application_error_can_be_raised(self):
        """Test that ApplicationError can be raised and caught."""
        with pytest.raises(ApplicationError, match="Test message"):
            raise ApplicationError("Test message")
        
        # Test catching as base Exception
        try:
            raise ApplicationError("Test error")
        except Exception as e:
            assert isinstance(e, ApplicationError)
            assert str(e) == "Test error"
    
    def test_application_error_subclass_inheritance(self):
        """Test that all specific errors inherit from ApplicationError."""
        error_classes = [
            HandlerNotFoundError,
            ValidationError,
            BusinessRuleViolationError,
            ResourceNotFoundError,
            DependencyError,
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
        """Test HandlerNotFoundError attributes."""
        error = HandlerNotFoundError("TestType")
        
        # Should have request_type attribute
        assert hasattr(error, "request_type")
        assert error.request_type == "TestType"
        
        # Should still have standard Exception attributes
        assert hasattr(error, "args")
        assert error.args == ("No handler registered for TestType",)


class TestValidationError:
    """Test cases for ValidationError."""
    
    def test_validation_error_creation_message_only(self):
        """Test creating ValidationError with message only."""
        message = "Invalid input data"
        error = ValidationError(message)
        
        assert str(error) == message
        assert error.field is None
        assert isinstance(error, ApplicationError)
    
    def test_validation_error_creation_with_field(self):
        """Test creating ValidationError with message and field."""
        message = "Email format is invalid"
        field = "email"
        error = ValidationError(message, field)
        
        assert str(error) == message
        assert error.field == field
        assert isinstance(error, ApplicationError)
    
    def test_validation_error_various_scenarios(self):
        """Test ValidationError with various scenarios."""
        test_cases = [
            ("Name cannot be empty", "name", "Name cannot be empty", "name"),
            ("Age must be positive", "age", "Age must be positive", "age"),
            ("Invalid date format", None, "Invalid date format", None),
            ("Required field missing", "required_field", "Required field missing", "required_field"),
        ]
        
        for message, field, expected_message, expected_field in test_cases:
            if field is not None:
                error = ValidationError(message, field)
            else:
                error = ValidationError(message)
            
            assert str(error) == expected_message
            assert error.field == expected_field
    
    def test_validation_error_raise_and_catch(self):
        """Test raising and catching ValidationError."""
        message = "Validation failed"
        field = "test_field"
        
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError(message, field)
        
        assert str(exc_info.value) == message
        assert exc_info.value.field == field
        
        # Test catching as ApplicationError
        try:
            raise ValidationError(message, field)
        except ApplicationError as e:
            assert isinstance(e, ValidationError)
            assert e.field == field
    
    def test_validation_error_field_types(self):
        """Test ValidationError with different field types."""
        # String field
        error1 = ValidationError("Error", "string_field")
        assert error1.field == "string_field"
        
        # None field (should be allowed)
        error2 = ValidationError("Error", None)
        assert error2.field is None
        
        # Field with special characters
        error3 = ValidationError("Error", "field.with.dots")
        assert error3.field == "field.with.dots"


class TestBusinessRuleViolationError:
    """Test cases for BusinessRuleViolationError."""
    
    def test_business_rule_violation_error_creation(self):
        """Test creating BusinessRuleViolationError."""
        message = "Cannot delete user with active orders"
        error = BusinessRuleViolationError(message)
        
        assert str(error) == message
        assert isinstance(error, ApplicationError)
    
    def test_business_rule_violation_error_scenarios(self):
        """Test BusinessRuleViolationError with various business scenarios."""
        test_cases = [
            "Cannot process filing while analysis is in progress",
            "User does not have permission to perform this action",
            "Company must have at least one active filing",
            "Maximum number of concurrent analyses exceeded",
            "Filing cannot be reprocessed within 24 hours",
        ]
        
        for message in test_cases:
            error = BusinessRuleViolationError(message)
            assert str(error) == message
            assert isinstance(error, ApplicationError)
    
    def test_business_rule_violation_error_raise_and_catch(self):
        """Test raising and catching BusinessRuleViolationError."""
        message = "Business rule violated"
        
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            raise BusinessRuleViolationError(message)
        
        assert str(exc_info.value) == message
        
        # Test catching as ApplicationError
        try:
            raise BusinessRuleViolationError(message)
        except ApplicationError as e:
            assert isinstance(e, BusinessRuleViolationError)
            assert str(e) == message
    
    def test_business_rule_violation_inheritance(self):
        """Test BusinessRuleViolationError inheritance chain."""
        error = BusinessRuleViolationError("Test")
        
        assert isinstance(error, BusinessRuleViolationError)
        assert isinstance(error, ApplicationError)
        assert isinstance(error, Exception)


class TestResourceNotFoundError:
    """Test cases for ResourceNotFoundError."""
    
    def test_resource_not_found_error_creation(self):
        """Test creating ResourceNotFoundError."""
        resource_type = "User"
        resource_id = "12345"
        error = ResourceNotFoundError(resource_type, resource_id)
        
        expected_message = f"{resource_type} with ID '{resource_id}' not found"
        assert str(error) == expected_message
        assert error.resource_type == resource_type
        assert error.resource_id == resource_id
        assert isinstance(error, ApplicationError)
    
    def test_resource_not_found_error_various_resources(self):
        """Test ResourceNotFoundError with various resource types."""
        test_cases = [
            ("Company", "AAPL", "Company with ID 'AAPL' not found"),
            ("Filing", "0000320193-24-000005", "Filing with ID '0000320193-24-000005' not found"),
            ("Analysis", "analysis-123", "Analysis with ID 'analysis-123' not found"),
            ("User", "user456", "User with ID 'user456' not found"),
        ]
        
        for resource_type, resource_id, expected_message in test_cases:
            error = ResourceNotFoundError(resource_type, resource_id)
            assert str(error) == expected_message
            assert error.resource_type == resource_type
            assert error.resource_id == resource_id
    
    def test_resource_not_found_error_raise_and_catch(self):
        """Test raising and catching ResourceNotFoundError."""
        resource_type = "TestResource"
        resource_id = "test123"
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            raise ResourceNotFoundError(resource_type, resource_id)
        
        assert exc_info.value.resource_type == resource_type
        assert exc_info.value.resource_id == resource_id
        assert f"{resource_type} with ID '{resource_id}' not found" in str(exc_info.value)
        
        # Test catching as ApplicationError
        try:
            raise ResourceNotFoundError(resource_type, resource_id)
        except ApplicationError as e:
            assert isinstance(e, ResourceNotFoundError)
            assert e.resource_type == resource_type
            assert e.resource_id == resource_id
    
    def test_resource_not_found_error_attributes(self):
        """Test ResourceNotFoundError attributes."""
        resource_type = "Document"
        resource_id = "doc789"
        error = ResourceNotFoundError(resource_type, resource_id)
        
        # Should have specific attributes
        assert hasattr(error, "resource_type")
        assert hasattr(error, "resource_id")
        assert error.resource_type == resource_type
        assert error.resource_id == resource_id
        
        # Should still have standard Exception attributes
        assert hasattr(error, "args")
        expected_message = f"{resource_type} with ID '{resource_id}' not found"
        assert error.args == (expected_message,)
    
    def test_resource_not_found_error_with_special_ids(self):
        """Test ResourceNotFoundError with special ID formats."""
        test_cases = [
            ("Company", "320193", "Company with ID '320193' not found"),
            ("Filing", "0000320193-24-000005", "Filing with ID '0000320193-24-000005' not found"),
            ("UUID", "550e8400-e29b-41d4-a716-446655440000", "UUID with ID '550e8400-e29b-41d4-a716-446655440000' not found"),
            ("Path", "/some/file/path.txt", "Path with ID '/some/file/path.txt' not found"),
        ]
        
        for resource_type, resource_id, expected_message in test_cases:
            error = ResourceNotFoundError(resource_type, resource_id)
            assert str(error) == expected_message
            assert error.resource_id == resource_id


class TestDependencyError:
    """Test cases for DependencyError."""
    
    def test_dependency_error_creation(self):
        """Test creating DependencyError."""
        dependency_name = "repository"
        error = DependencyError(dependency_name)
        
        expected_message = f"Required dependency '{dependency_name}' could not be resolved"
        assert str(error) == expected_message
        assert error.dependency_name == dependency_name
        assert isinstance(error, ApplicationError)
    
    def test_dependency_error_various_dependencies(self):
        """Test DependencyError with various dependency names."""
        test_cases = [
            ("repository", "Required dependency 'repository' could not be resolved"),
            ("service", "Required dependency 'service' could not be resolved"),
            ("logger", "Required dependency 'logger' could not be resolved"),
            ("config", "Required dependency 'config' could not be resolved"),
            ("database_session", "Required dependency 'database_session' could not be resolved"),
        ]
        
        for dependency_name, expected_message in test_cases:
            error = DependencyError(dependency_name)
            assert str(error) == expected_message
            assert error.dependency_name == dependency_name
    
    def test_dependency_error_raise_and_catch(self):
        """Test raising and catching DependencyError."""
        dependency_name = "missing_service"
        
        with pytest.raises(DependencyError) as exc_info:
            raise DependencyError(dependency_name)
        
        assert exc_info.value.dependency_name == dependency_name
        assert f"Required dependency '{dependency_name}' could not be resolved" in str(exc_info.value)
        
        # Test catching as ApplicationError
        try:
            raise DependencyError(dependency_name)
        except ApplicationError as e:
            assert isinstance(e, DependencyError)
            assert e.dependency_name == dependency_name
    
    def test_dependency_error_attributes(self):
        """Test DependencyError attributes."""
        dependency_name = "test_dependency"
        error = DependencyError(dependency_name)
        
        # Should have specific attributes
        assert hasattr(error, "dependency_name")
        assert error.dependency_name == dependency_name
        
        # Should still have standard Exception attributes
        assert hasattr(error, "args")
        expected_message = f"Required dependency '{dependency_name}' could not be resolved"
        assert error.args == (expected_message,)
    
    def test_dependency_error_with_special_names(self):
        """Test DependencyError with special dependency names."""
        test_cases = [
            "user_repository",
            "filing_analysis_service",
            "openai_llm_provider",
            "redis_cache_client",
            "postgresql_session_maker",
        ]
        
        for dependency_name in test_cases:
            error = DependencyError(dependency_name)
            expected_message = f"Required dependency '{dependency_name}' could not be resolved"
            assert str(error) == expected_message
            assert error.dependency_name == dependency_name


class TestErrorHierarchy:
    """Test cases for error hierarchy and inheritance."""
    
    def test_all_errors_inherit_from_application_error(self):
        """Test that all specific errors inherit from ApplicationError."""
        error_classes = [
            HandlerNotFoundError,
            ValidationError,
            BusinessRuleViolationError,
            ResourceNotFoundError,
            DependencyError,
        ]
        
        for error_class in error_classes:
            # Create instance with appropriate parameters
            if error_class == HandlerNotFoundError:
                error = error_class("TestType")
            elif error_class == ValidationError:
                error = error_class("Test message")
            elif error_class == ResourceNotFoundError:
                error = error_class("Resource", "123")
            elif error_class == DependencyError:
                error = error_class("dependency")
            else:
                error = error_class("Test message")
            
            assert isinstance(error, ApplicationError)
            assert isinstance(error, Exception)
    
    def test_error_catching_hierarchy(self):
        """Test that errors can be caught at different levels."""
        test_errors = [
            HandlerNotFoundError("TestCommand"),
            ValidationError("Invalid data", "field"),
            BusinessRuleViolationError("Rule violated"),
            ResourceNotFoundError("User", "123"),
            DependencyError("service"),
        ]
        
        for error in test_errors:
            # Should be catchable as specific type
            try:
                raise error
            except type(error) as e:
                assert e is error
            
            # Should be catchable as ApplicationError
            try:
                raise error
            except ApplicationError as e:
                assert e is error
            
            # Should be catchable as Exception
            try:
                raise error
            except Exception as e:
                assert e is error
    
    def test_error_message_consistency(self):
        """Test that all errors have consistent message handling."""
        test_cases = [
            (HandlerNotFoundError("TestCommand"), "No handler registered for TestCommand"),
            (ValidationError("Invalid data"), "Invalid data"),
            (ValidationError("Invalid data", "field"), "Invalid data"),
            (BusinessRuleViolationError("Rule violated"), "Rule violated"),
            (ResourceNotFoundError("User", "123"), "User with ID '123' not found"),
            (DependencyError("service"), "Required dependency 'service' could not be resolved"),
        ]
        
        for error, expected_message in test_cases:
            assert str(error) == expected_message
            # First arg should be the message
            assert error.args[0] == expected_message
    
    def test_error_attributes_preserved(self):
        """Test that error-specific attributes are preserved."""
        # HandlerNotFoundError
        handler_error = HandlerNotFoundError("TestType")
        assert handler_error.request_type == "TestType"
        
        # ValidationError
        validation_error = ValidationError("Test", "field")
        assert validation_error.field == "field"
        
        validation_error_no_field = ValidationError("Test")
        assert validation_error_no_field.field is None
        
        # ResourceNotFoundError
        resource_error = ResourceNotFoundError("User", "123")
        assert resource_error.resource_type == "User"
        assert resource_error.resource_id == "123"
        
        # DependencyError
        dependency_error = DependencyError("service")
        assert dependency_error.dependency_name == "service"
    
    def test_multiple_error_handling_in_single_try_block(self):
        """Test handling multiple error types in a single try block."""
        def raise_various_errors(error_type: str):
            if error_type == "handler":
                raise HandlerNotFoundError("TestCommand")
            elif error_type == "validation":
                raise ValidationError("Invalid data", "field")
            elif error_type == "business":
                raise BusinessRuleViolationError("Rule violated")
            elif error_type == "resource":
                raise ResourceNotFoundError("User", "123")
            elif error_type == "dependency":
                raise DependencyError("service")
            else:
                raise ApplicationError("Generic error")
        
        # Test catching specific errors
        for error_type in ["handler", "validation", "business", "resource", "dependency", "generic"]:
            try:
                raise_various_errors(error_type)
            except HandlerNotFoundError as e:
                assert error_type == "handler"
                assert e.request_type == "TestCommand"
            except ValidationError as e:
                assert error_type == "validation"
                assert e.field == "field"
            except BusinessRuleViolationError as e:
                assert error_type == "business"
                assert str(e) == "Rule violated"
            except ResourceNotFoundError as e:
                assert error_type == "resource"
                assert e.resource_type == "User"
                assert e.resource_id == "123"
            except DependencyError as e:
                assert error_type == "dependency"
                assert e.dependency_name == "service"
            except ApplicationError as e:
                assert error_type == "generic"
                assert str(e) == "Generic error"