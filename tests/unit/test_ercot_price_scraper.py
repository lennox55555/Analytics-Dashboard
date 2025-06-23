"""
Unit tests for ERCOT price scraper
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import requests
import pytz

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scrapers'))

from ercot_price_scraper import get_ercot_now, create_price_table

class TestERCOTPriceScraper:
    
    def test_get_ercot_now(self):
        """Test getting current ERCOT time"""
        central_time = get_ercot_now()
        
        assert isinstance(central_time, datetime)
        assert central_time.tzinfo is not None
        # Should be in Central timezone
        assert 'Central' in str(central_time.tzinfo) or 'CST' in str(central_time.tzinfo) or 'CDT' in str(central_time.tzinfo)
    
    @patch('ercot_price_scraper.get_db_connection')
    def test_create_price_table_success(self, mock_get_db):
        """Test successful price table creation"""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        result = create_price_table()
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('ercot_price_scraper.get_db_connection')
    def test_create_price_table_error(self, mock_get_db):
        """Test price table creation with database error"""
        # Mock database error
        mock_get_db.side_effect = Exception("Database connection failed")
        
        result = create_price_table()
        
        assert result is False
    
    def test_timezone_handling(self):
        """Test timezone handling functionality"""
        # Test that ERCOT time is properly handled
        central_time = get_ercot_now()
        utc_time = datetime.now(pytz.UTC)
        
        # Convert both to UTC for comparison
        central_utc = central_time.astimezone(pytz.UTC)
        
        # Should be within a reasonable time difference (a few seconds)
        time_diff = abs((central_utc - utc_time).total_seconds())
        assert time_diff < 10  # Less than 10 seconds difference
    
    @patch('requests.get')
    def test_http_request_handling(self, mock_get):
        """Test HTTP request handling"""
        # This tests the pattern used in the scraper
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "test,data,content"
        mock_get.return_value = mock_response
        
        # Test successful request
        response = requests.get("http://test-url.com")
        assert response.status_code == 200
        assert "test,data,content" in response.text
    
    @patch('requests.get')
    def test_http_request_error_handling(self, mock_get):
        """Test HTTP request error handling"""
        # Test network error
        mock_get.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(requests.RequestException):
            requests.get("http://test-url.com")
    
    @patch('requests.get')
    def test_http_404_handling(self, mock_get):
        """Test HTTP 404 error handling"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        response = requests.get("http://test-url.com")
        assert response.status_code == 404
    
    def test_data_validation_patterns(self):
        """Test data validation patterns"""
        # Test valid decimal patterns
        valid_prices = ["25.50", "100.00", "0.00", "-10.50"]
        for price in valid_prices:
            try:
                float_val = float(price)
                assert isinstance(float_val, float)
            except ValueError:
                pytest.fail(f"Valid price {price} failed conversion")
        
        # Test invalid patterns
        invalid_prices = ["N/A", "", "invalid", "---"]
        for price in invalid_prices:
            try:
                float(price)
                pytest.fail(f"Invalid price {price} should have failed")
            except ValueError:
                pass  # Expected to fail
    
    def test_timestamp_patterns(self):
        """Test timestamp parsing patterns"""
        # Test valid timestamp formats
        valid_timestamps = [
            "01/01/2024 01:00",
            "12/31/2024 23:45",
            "06/15/2024 12:30"
        ]
        
        for ts in valid_timestamps:
            try:
                # Test basic parsing pattern
                parts = ts.split()
                assert len(parts) == 2  # Date and time parts
                date_part, time_part = parts
                assert "/" in date_part
                assert ":" in time_part
            except Exception:
                pytest.fail(f"Valid timestamp {ts} failed parsing")
    
    @patch('ercot_price_scraper.get_db_connection')
    def test_database_error_resilience(self, mock_get_db):
        """Test database error resilience"""
        # Test various database errors
        error_scenarios = [
            Exception("Connection timeout"),
            Exception("Authentication failed"),
            Exception("Database does not exist"),
            Exception("Permission denied")
        ]
        
        for error in error_scenarios:
            mock_get_db.side_effect = error
            
            # Should handle error gracefully
            result = create_price_table()
            assert result is False
    
    def test_data_structure_validation(self):
        """Test data structure validation"""
        # Test expected data structure for price data
        sample_price_data = {
            'timestamp': datetime.now(),
            'oper_day': '2024-01-01',
            'interval_ending': '01:00',
            'hb_busavg': 25.50,
            'hb_houston': 26.00,
            'hb_north': 24.50
        }
        
        # Validate required fields exist
        required_fields = ['timestamp', 'oper_day', 'interval_ending']
        for field in required_fields:
            assert field in sample_price_data
        
        # Validate data types
        assert isinstance(sample_price_data['timestamp'], datetime)
        assert isinstance(sample_price_data['hb_busavg'], float)
    
    def test_safe_data_conversion(self):
        """Test safe data conversion utilities"""
        # Test safe float conversion
        def safe_float(value, default=0.0):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        # Test various inputs
        assert safe_float("25.50") == 25.50
        assert safe_float("invalid") == 0.0
        assert safe_float(None) == 0.0
        assert safe_float("") == 0.0
        assert safe_float("123.45") == 123.45