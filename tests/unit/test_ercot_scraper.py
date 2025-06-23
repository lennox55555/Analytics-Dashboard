"""
Unit tests for ERCOT scraper
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import requests

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scrapers'))

from ercot_scraper import scrape_ercot

class TestERCOTScraper:
    
    @patch('requests.get')
    @patch('ercot_scraper.get_db_connection')
    def test_scrape_ercot_success(self, mock_get_db, mock_get):
        """Test successful ERCOT scraping"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <table>
                    <tr><td>Some capacity data</td></tr>
                </table>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        # Mock database
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock successful execution
        mock_cursor.execute.return_value = None
        mock_conn.commit.return_value = None
        
        result = scrape_ercot()
        
        # Should complete without error
        mock_get.assert_called_once()
        mock_cursor.execute.assert_called()
    
    @patch('requests.get')
    def test_scrape_ercot_http_error(self, mock_get):
        """Test ERCOT scraping with HTTP error"""
        # Mock HTTP error
        mock_get.side_effect = requests.RequestException("Network error")
        
        # Should handle error gracefully
        scrape_ercot()  # Should not raise exception
    
    @patch('requests.get')
    def test_scrape_ercot_404(self, mock_get):
        """Test ERCOT scraping with 404 response"""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Should handle 404 gracefully
        scrape_ercot()  # Should not raise exception
    
    @patch('requests.get')
    @patch('ercot_scraper.get_db_connection')
    def test_scrape_ercot_db_error(self, mock_get_db, mock_get):
        """Test ERCOT scraping with database error"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><table><tr><td>data</td></tr></table></body></html>'
        mock_get.return_value = mock_response
        
        # Mock database error
        mock_get_db.side_effect = Exception("Database connection failed")
        
        # Should handle database error gracefully
        scrape_ercot()  # Should not raise exception
    
    def test_scrape_ercot_import_available(self):
        """Test that scrape_ercot function is importable"""
        # This test ensures the function exists and is importable
        from ercot_scraper import scrape_ercot
        assert callable(scrape_ercot)