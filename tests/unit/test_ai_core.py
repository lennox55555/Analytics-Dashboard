"""
Unit tests for AI visualization core
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TestAIVisualizationCore:
    
    @patch('src.ai_visualization_core.boto3.client')
    def test_bedrock_client_initialization(self, mock_boto3):
        """Test Bedrock client initialization"""
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        from src.ai_visualization_core import BedrockAIClient
        
        with patch.dict('os.environ', {'AWS_REGION': 'us-east-1'}):
            client = BedrockAIClient()
            assert client.bedrock_client == mock_client
    
    @patch('src.ai_visualization_core.boto3.client')
    def test_bedrock_client_no_region(self, mock_boto3):
        """Test Bedrock client with no region set"""
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        from src.ai_visualization_core import BedrockAIClient
        
        with patch.dict('os.environ', {}, clear=True):
            client = BedrockAIClient()
            # Should use default region
            mock_boto3.assert_called_with('bedrock-runtime', region_name='us-east-1')
    
    @patch('src.ai_visualization_core.get_db_connection')
    def test_database_analyzer_initialization(self, mock_get_db):
        """Test database analyzer initialization"""
        from src.ai_visualization_core import DatabaseAnalyzer
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock table information query
        mock_cursor.fetchall.return_value = [
            {
                'table_name': 'ercot_settlement_prices',
                'column_name': 'timestamp',
                'data_type': 'timestamp without time zone'
            }
        ]
        
        analyzer = DatabaseAnalyzer()
        assert analyzer is not None
    
    @patch('src.ai_visualization_core.get_db_connection')
    def test_database_analyzer_get_available_tables(self, mock_get_db):
        """Test getting available tables"""
        from src.ai_visualization_core import DatabaseAnalyzer
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock table information
        mock_cursor.fetchall.return_value = [
            {
                'table_name': 'ercot_settlement_prices',
                'column_name': 'timestamp',
                'data_type': 'timestamp without time zone'
            },
            {
                'table_name': 'ercot_settlement_prices',
                'column_name': 'hb_busavg',
                'data_type': 'numeric'
            }
        ]
        
        analyzer = DatabaseAnalyzer()
        tables = analyzer.get_available_tables()
        
        assert isinstance(tables, list)
        assert len(tables) > 0
    
    @patch('src.ai_visualization_core.requests.post')
    def test_grafana_api_client_create_dashboard(self, mock_post):
        """Test Grafana API dashboard creation"""
        from src.ai_visualization_core import GrafanaAPIClient
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'uid': 'test-uid',
            'url': '/d/test-uid/test-dashboard'
        }
        mock_post.return_value = mock_response
        
        grafana_client = GrafanaAPIClient(
            grafana_url="http://test:3000",
            api_key="test-key"
        )
        
        dashboard_config = {
            'dashboard': {
                'title': 'Test Dashboard',
                'panels': []
            }
        }
        
        result = grafana_client.create_dashboard(dashboard_config)
        
        assert result['id'] == 123
        assert result['uid'] == 'test-uid'
    
    @patch('src.ai_visualization_core.requests.post')
    def test_grafana_api_client_create_dashboard_error(self, mock_post):
        """Test Grafana API dashboard creation error"""
        from src.ai_visualization_core import GrafanaAPIClient
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Bad request'}
        mock_post.return_value = mock_response
        
        grafana_client = GrafanaAPIClient(
            grafana_url="http://test:3000",
            api_key="test-key"
        )
        
        dashboard_config = {
            'dashboard': {
                'title': 'Test Dashboard',
                'panels': []
            }
        }
        
        result = grafana_client.create_dashboard(dashboard_config)
        
        assert result is None
    
    def test_sql_query_generator_validation(self):
        """Test SQL query generator validation"""
        from src.ai_visualization_core import SQLQueryGenerator
        
        generator = SQLQueryGenerator()
        
        # Test valid query
        valid_query = "SELECT timestamp, hb_busavg FROM ercot_settlement_prices LIMIT 100"
        assert generator.validate_query(valid_query) is True
        
        # Test invalid query (DROP statement)
        invalid_query = "DROP TABLE ercot_settlement_prices"
        assert generator.validate_query(invalid_query) is False
        
        # Test invalid query (DELETE statement)
        invalid_query = "DELETE FROM ercot_settlement_prices"
        assert generator.validate_query(invalid_query) is False
    
    def test_sql_query_generator_clean_query(self):
        """Test SQL query cleaning"""
        from src.ai_visualization_core import SQLQueryGenerator
        
        generator = SQLQueryGenerator()
        
        # Test query with markdown formatting
        query_with_markdown = "```sql\nSELECT * FROM ercot_settlement_prices;\n```"
        cleaned = generator.clean_query(query_with_markdown)
        
        assert "```" not in cleaned
        assert "SELECT * FROM ercot_settlement_prices" in cleaned
    
    @patch('src.ai_visualization_core.get_db_connection')
    def test_sql_query_generator_test_query(self, mock_get_db):
        """Test SQL query testing"""
        from src.ai_visualization_core import SQLQueryGenerator
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{'count': 1}]
        mock_get_db.return_value = mock_conn
        
        generator = SQLQueryGenerator()
        
        query = "SELECT COUNT(*) as count FROM ercot_settlement_prices"
        result = generator.test_query(query)
        
        assert result is True
        mock_cursor.execute.assert_called_once()
    
    @patch('src.ai_visualization_core.get_db_connection')
    def test_sql_query_generator_test_query_error(self, mock_get_db):
        """Test SQL query testing with error"""
        from src.ai_visualization_core import SQLQueryGenerator
        
        # Mock database connection with error
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        generator = SQLQueryGenerator()
        
        query = "INVALID SQL QUERY"
        result = generator.test_query(query)
        
        assert result is False
    
    @patch('src.ai_visualization_core.initialize_ai_system')
    def test_get_ai_processor(self, mock_initialize):
        """Test getting AI processor"""
        from src.ai_visualization_core import get_ai_processor
        
        # Mock initialized processor
        mock_processor = Mock()
        mock_initialize.return_value = mock_processor
        
        processor = get_ai_processor()
        
        assert processor == mock_processor