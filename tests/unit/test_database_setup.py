"""
Unit tests for database setup utilities
"""
import pytest
from unittest.mock import Mock, patch
import psycopg2

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'database'))

class TestDatabaseSetup:
    
    @patch('setup_database.get_db_connection')
    def test_create_tables_success(self, mock_get_db):
        """Test successful table creation"""
        from setup_database import create_tables
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        result = create_tables()
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('setup_database.get_db_connection')
    def test_create_tables_error(self, mock_get_db):
        """Test table creation with error"""
        from setup_database import create_tables
        
        # Mock database error
        mock_get_db.side_effect = Exception("Database connection failed")
        
        result = create_tables()
        
        assert result is False
    
    @patch('setup_database.get_db_connection')
    def test_create_indexes_success(self, mock_get_db):
        """Test successful index creation"""
        from setup_database import create_indexes
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        result = create_indexes()
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('setup_database.get_db_connection')
    def test_create_triggers_success(self, mock_get_db):
        """Test successful trigger creation"""
        from setup_database import create_triggers
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        result = create_triggers()
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('setup_database.get_db_connection')
    def test_verify_tables_exist(self, mock_get_db):
        """Test table verification"""
        from setup_database import verify_tables
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock table exists
        mock_cursor.fetchall.return_value = [
            {'table_name': 'ercot_settlement_prices'},
            {'table_name': 'users'},
            {'table_name': 'user_sessions'}
        ]
        
        result = verify_tables()
        
        assert result is True
        mock_cursor.execute.assert_called()
    
    @patch('setup_database.get_db_connection')
    def test_verify_tables_missing(self, mock_get_db):
        """Test table verification with missing tables"""
        from setup_database import verify_tables
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock missing tables
        mock_cursor.fetchall.return_value = []
        
        result = verify_tables()
        
        assert result is False
    
    @patch('setup_database.get_db_connection')
    def test_get_database_statistics(self, mock_get_db):
        """Test database statistics collection"""
        from setup_database import get_database_statistics
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock statistics data
        mock_cursor.fetchall.return_value = [
            {
                'schemaname': 'public',
                'tablename': 'ercot_settlement_prices',
                'n_live_tup': 1000,
                'n_dead_tup': 10
            }
        ]
        
        stats = get_database_statistics()
        
        assert isinstance(stats, list)
        assert len(stats) > 0
        mock_cursor.execute.assert_called()
    
    def test_validate_database_config(self):
        """Test database configuration validation"""
        from setup_database import validate_database_config
        
        # Test valid config
        valid_config = {
            'host': 'localhost',
            'database': 'analytics',
            'user': 'dbuser',
            'password': 'password',
            'port': 5432
        }
        
        assert validate_database_config(valid_config) is True
        
        # Test invalid config (missing required fields)
        invalid_config = {
            'host': 'localhost'
            # Missing other required fields
        }
        
        assert validate_database_config(invalid_config) is False
    
    def test_generate_sql_scripts(self):
        """Test SQL script generation"""
        from setup_database import generate_create_table_sql
        
        # Test table creation SQL
        sql = generate_create_table_sql('test_table')
        
        assert isinstance(sql, str)
        assert 'CREATE TABLE' in sql.upper()
        assert 'test_table' in sql
    
    @patch('setup_database.get_db_connection')
    def test_database_cleanup(self, mock_get_db):
        """Test database cleanup operations"""
        from setup_database import cleanup_database
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        result = cleanup_database()
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('setup_database.get_db_connection')
    def test_backup_database(self, mock_get_db):
        """Test database backup functionality"""
        from setup_database import backup_database_schema
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock schema data
        mock_cursor.fetchall.return_value = [
            {'ddl': 'CREATE TABLE test_table (id SERIAL PRIMARY KEY);'}
        ]
        
        result = backup_database_schema()
        
        assert isinstance(result, list)
        mock_cursor.execute.assert_called()