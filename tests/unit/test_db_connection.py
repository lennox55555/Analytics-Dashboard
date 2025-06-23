"""
Unit tests for database connection utilities
"""
import pytest
from unittest.mock import Mock, patch
import psycopg2

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'database'))

from db_connection import DatabaseConnection, get_db_connection

class TestDatabaseConnection:
    
    def test_db_connection_initialization(self):
        """Test database connection initialization"""
        with patch.dict('os.environ', {
            'DB_HOST': 'test-host',
            'DB_NAME': 'test-db',
            'DB_USER': 'test-user',
            'DB_PASSWORD': 'test-pass',
            'DB_PORT': '5432'
        }):
            db_conn = DatabaseConnection()
            assert db_conn.config['host'] == 'test-host'
            assert db_conn.config['database'] == 'test-db'
            assert db_conn.config['user'] == 'test-user'
            assert db_conn.config['port'] == 5432
    
    def test_db_connection_default_values(self):
        """Test database connection with default values"""
        with patch.dict('os.environ', {}, clear=True):
            db_conn = DatabaseConnection()
            assert db_conn.config['host'] == 'localhost'
            assert db_conn.config['database'] == 'analytics'
            assert db_conn.config['user'] == 'dbuser'
            assert db_conn.config['port'] == 5432
    
    @patch('psycopg2.connect')
    def test_get_connection_success(self, mock_connect):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        db_conn = DatabaseConnection()
        conn = db_conn.get_connection()
        
        assert conn == mock_conn
        mock_connect.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_get_connection_failure(self, mock_connect):
        """Test database connection failure"""
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
        
        db_conn = DatabaseConnection()
        
        with pytest.raises(ConnectionError):
            db_conn.get_connection()
    
    @patch('psycopg2.connect')
    def test_get_db_connection_function(self, mock_connect):
        """Test get_db_connection function"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = get_db_connection()
        
        assert conn == mock_conn
        mock_connect.assert_called_once()
    
    def test_invalid_port_handling(self):
        """Test handling of invalid port configuration"""
        with patch.dict('os.environ', {'DB_PORT': 'invalid-port'}):
            db_conn = DatabaseConnection()
            # Should fallback to default port
            assert db_conn.config['port'] == 5432
    
    @patch('psycopg2.connect')
    def test_connection_authentication_error(self, mock_connect):
        """Test authentication error handling"""
        mock_connect.side_effect = psycopg2.OperationalError("authentication failed for user")
        
        db_conn = DatabaseConnection()
        
        with pytest.raises(ConnectionError, match="Database authentication failed"):
            db_conn.get_connection()
    
    @patch('psycopg2.connect') 
    def test_database_not_exists_error(self, mock_connect):
        """Test database does not exist error"""
        mock_connect.side_effect = psycopg2.OperationalError('database "nonexistent" does not exist')
        
        with patch.dict('os.environ', {'DB_NAME': 'nonexistent'}):
            db_conn = DatabaseConnection()
            
            with pytest.raises(ConnectionError, match="Database 'nonexistent' not found"):
                db_conn.get_connection()