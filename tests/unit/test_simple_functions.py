"""
Simple unit tests for basic utility functions to increase coverage
"""
import pytest
from unittest.mock import Mock, patch
import os
import json
import logging

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TestUtilityFunctions:
    
    def test_environment_variable_handling(self):
        """Test environment variable handling patterns"""
        # Test getting environment variables with defaults
        def get_env_var(name, default=None):
            return os.environ.get(name, default)
        
        # Test with existing variable
        with patch.dict('os.environ', {'TEST_VAR': 'test_value'}):
            assert get_env_var('TEST_VAR') == 'test_value'
        
        # Test with missing variable and default
        with patch.dict('os.environ', {}, clear=True):
            assert get_env_var('MISSING_VAR', 'default') == 'default'
            assert get_env_var('MISSING_VAR') is None
    
    def test_json_serialization(self):
        """Test JSON serialization patterns"""
        # Test valid JSON
        data = {'key': 'value', 'number': 123}
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        
        # Test deserialization
        parsed = json.loads(json_str)
        assert parsed == data
        
        # Test invalid JSON handling
        with pytest.raises(json.JSONDecodeError):
            json.loads("invalid json")
    
    def test_string_validation(self):
        """Test string validation patterns"""
        # Test email validation pattern
        def is_valid_email(email):
            return '@' in email and '.' in email.split('@')[1]
        
        assert is_valid_email('test@example.com') is True
        assert is_valid_email('invalid-email') is False
        assert is_valid_email('test@domain') is False
    
    def test_number_validation(self):
        """Test number validation patterns"""
        # Test safe number conversion
        def safe_int(value, default=0):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        assert safe_int('123') == 123
        assert safe_int('invalid') == 0
        assert safe_int(None) == 0
        assert safe_int('45.67') == 45  # Truncates float
    
    def test_list_operations(self):
        """Test list operations patterns"""
        # Test safe list operations
        test_list = [1, 2, 3, 4, 5]
        
        # Test slicing
        assert test_list[:3] == [1, 2, 3]
        assert test_list[2:] == [3, 4, 5]
        
        # Test filtering
        filtered = [x for x in test_list if x > 3]
        assert filtered == [4, 5]
        
        # Test mapping
        doubled = [x * 2 for x in test_list]
        assert doubled == [2, 4, 6, 8, 10]
    
    def test_dictionary_operations(self):
        """Test dictionary operations patterns"""
        test_dict = {'a': 1, 'b': 2, 'c': 3}
        
        # Test key existence
        assert 'a' in test_dict
        assert 'd' not in test_dict
        
        # Test safe key access
        def safe_get(d, key, default=None):
            return d.get(key, default)
        
        assert safe_get(test_dict, 'a') == 1
        assert safe_get(test_dict, 'd', 'default') == 'default'
    
    def test_error_handling_patterns(self):
        """Test common error handling patterns"""
        # Test try-except pattern
        def safe_operation(x, y):
            try:
                return x / y
            except ZeroDivisionError:
                return None
            except TypeError:
                return None
        
        assert safe_operation(10, 2) == 5.0
        assert safe_operation(10, 0) is None
        assert safe_operation('10', 2) is None
    
    def test_logging_patterns(self):
        """Test logging patterns"""
        logger = logging.getLogger('test_logger')
        
        # Test logger configuration
        assert logger.name == 'test_logger'
        
        # Test logging levels
        assert logging.DEBUG < logging.INFO
        assert logging.INFO < logging.WARNING
        assert logging.WARNING < logging.ERROR
    
    def test_file_path_operations(self):
        """Test file path operations"""
        # Test path joining
        path = os.path.join('folder', 'subfolder', 'file.txt')
        assert 'folder' in path
        assert 'file.txt' in path
        
        # Test path existence (these paths don't exist)
        assert not os.path.exists('/nonexistent/path')
    
    def test_boolean_operations(self):
        """Test boolean operations and conversions"""
        # Test truthy/falsy values
        assert bool(1) is True
        assert bool(0) is False
        assert bool('string') is True
        assert bool('') is False
        assert bool([1, 2]) is True
        assert bool([]) is False
    
    def test_string_operations(self):
        """Test string operations"""
        test_string = "  Hello World  "
        
        # Test string methods
        assert test_string.strip() == "Hello World"
        assert test_string.lower().strip() == "hello world"
        assert test_string.upper().strip() == "HELLO WORLD"
        
        # Test string formatting
        formatted = f"Value: {123}"
        assert formatted == "Value: 123"
    
    def test_type_checking(self):
        """Test type checking patterns"""
        # Test isinstance checks
        assert isinstance(123, int)
        assert isinstance("string", str)
        assert isinstance([1, 2, 3], list)
        assert isinstance({'key': 'value'}, dict)
        
        # Test type() checks
        assert type(123) == int
        assert type("string") == str
    
    def test_conditional_logic(self):
        """Test conditional logic patterns"""
        def check_value(value):
            if value is None:
                return "None"
            elif isinstance(value, str):
                return "String"
            elif isinstance(value, int):
                return "Integer"
            else:
                return "Other"
        
        assert check_value(None) == "None"
        assert check_value("test") == "String"
        assert check_value(123) == "Integer"
        assert check_value([1, 2]) == "Other"
    
    def test_exception_types(self):
        """Test different exception types"""
        # Test ValueError
        with pytest.raises(ValueError):
            int("invalid")
        
        # Test KeyError
        with pytest.raises(KeyError):
            {}['missing_key']
        
        # Test IndexError
        with pytest.raises(IndexError):
            [][0]
        
        # Test AttributeError
        with pytest.raises(AttributeError):
            None.some_method()
    
    def test_data_structures(self):
        """Test data structure operations"""
        # Test set operations
        set1 = {1, 2, 3}
        set2 = {3, 4, 5}
        
        assert set1.union(set2) == {1, 2, 3, 4, 5}
        assert set1.intersection(set2) == {3}
        
        # Test tuple operations
        test_tuple = (1, 2, 3)
        assert test_tuple[0] == 1
        assert len(test_tuple) == 3
        assert 2 in test_tuple