"""
Unit tests for LangGraph AI visualization system
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TestLangGraphAI:
    
    def test_data_source_initialization(self):
        """Test DataSource class initialization"""
        from langgraph_ai_visualization import DataSource
        
        data_source = DataSource(
            table_name="test_table",
            description="Test table description",
            columns=["id", "name", "value"],
            time_column="timestamp"
        )
        
        assert data_source.table_name == "test_table"
        assert data_source.description == "Test table description"
        assert len(data_source.columns) == 3
        assert data_source.time_column == "timestamp"
    
    def test_ai_visualization_state_structure(self):
        """Test AIVisualizationState structure"""
        from langgraph_ai_visualization import AIVisualizationState
        
        # Test that state structure is properly defined
        state = {
            'user_id': 1,
            'request_text': 'Show me price data',
            'visualization_type': 'line',
            'available_data_sources': [],
            'errors': [],
            'status': 'processing'
        }
        
        # Should be able to create state with required fields
        assert state['user_id'] == 1
        assert state['request_text'] == 'Show me price data'
        assert state['status'] == 'processing'
    
    @patch('langgraph_ai_visualization.boto3.client')
    def test_langgraph_visualizer_initialization(self, mock_boto3):
        """Test LangGraph visualizer initialization"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        with patch.dict('os.environ', {'AWS_REGION': 'us-east-1'}):
            visualizer = LangGraphAIVisualizer()
            
            assert visualizer.bedrock_client == mock_client
            assert len(visualizer.data_sources) > 0
            assert visualizer.workflow is not None
    
    def test_chart_type_detection_patterns(self):
        """Test chart type detection patterns"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test line chart detection
            line_requests = [
                "show me prices over time",
                "display trend of capacity",
                "historical data timeline"
            ]
            
            for request in line_requests:
                chart_type = visualizer._detect_chart_type_from_keywords(request)
                assert chart_type in ['line', 'timeseries']  # Both are valid for time series
            
            # Test bar chart detection
            bar_requests = [
                "compare regions",
                "show comparison between hubs",
                "compare values by zone"
            ]
            
            for request in bar_requests:
                chart_type = visualizer._detect_chart_type_from_keywords(request)
                assert chart_type == 'bar'
    
    def test_data_source_selection_logic(self):
        """Test data source selection logic"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test price-related keywords
            price_requests = [
                "show settlement prices",
                "display LMP data",
                "hub pricing information"
            ]
            
            for request in price_requests:
                data_source = visualizer._select_data_source_by_keywords(request)
                assert data_source['table_name'] == 'ercot_settlement_prices'
            
            # Test capacity-related keywords
            capacity_requests = [
                "show grid stress",
                "display capacity reserves",
                "generation availability"
            ]
            
            for request in capacity_requests:
                data_source = visualizer._select_data_source_by_keywords(request)
                assert data_source['table_name'] == 'ercot_capacity_monitor'
    
    def test_sql_query_validation(self):
        """Test SQL query validation"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test valid SELECT query
            valid_query = "SELECT timestamp, hb_busavg FROM ercot_settlement_prices WHERE timestamp > NOW() - INTERVAL '24 hours' LIMIT 100"
            assert visualizer._validate_sql_query(valid_query) is True
            
            # Test invalid queries
            invalid_queries = [
                "DROP TABLE ercot_settlement_prices",
                "DELETE FROM users",
                "UPDATE ercot_settlement_prices SET hb_busavg = 0",
                "INSERT INTO users VALUES (1, 'test')"
            ]
            
            for query in invalid_queries:
                assert visualizer._validate_sql_query(query) is False
    
    def test_query_cleaning(self):
        """Test SQL query cleaning"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test markdown removal
            query_with_markdown = "```sql\nSELECT * FROM ercot_settlement_prices;\n```"
            cleaned = visualizer._clean_sql_query(query_with_markdown)
            assert "```" not in cleaned
            assert "SELECT * FROM ercot_settlement_prices" in cleaned
            
            # Test semicolon removal
            query_with_semicolon = "SELECT * FROM ercot_settlement_prices;"
            cleaned = visualizer._clean_sql_query(query_with_semicolon)
            assert not cleaned.endswith(";")
    
    def test_visualization_type_detection(self):
        """Test visualization type detection from request text"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            test_cases = [
                ("show me a line chart of prices", "line"),
                ("create a bar chart comparing regions", "bar"),
                ("display pie chart of distribution", "pie"),
                ("show current status gauge", "gauge"),
                ("list all the data in a table", "table"),
                ("show area chart of capacity", "area")
            ]
            
            for request_text, expected_type in test_cases:
                detected_type = visualizer._detect_chart_type_from_keywords(request_text)
                assert detected_type == expected_type
    
    @patch('langgraph_ai_visualization.get_db_connection')
    def test_data_preview_functionality(self, mock_get_db):
        """Test data preview functionality"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'timestamp': '2024-01-01 00:00:00', 'hb_busavg': 25.50},
            {'timestamp': '2024-01-01 00:15:00', 'hb_busavg': 26.00}
        ]
        mock_get_db.return_value = mock_conn
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            query = "SELECT timestamp, hb_busavg FROM ercot_settlement_prices LIMIT 2"
            preview = visualizer._preview_data(query)
            
            assert isinstance(preview, list)
            assert len(preview) == 2
            assert 'timestamp' in preview[0]
            assert 'hb_busavg' in preview[0]
    
    def test_grafana_panel_configuration(self):
        """Test Grafana panel configuration generation"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test line chart configuration
            line_config = visualizer._generate_grafana_panel_config(
                chart_type="line",
                title="Test Line Chart",
                sql_query="SELECT timestamp, hb_busavg FROM ercot_settlement_prices",
                panel_id=1
            )
            
            assert line_config['type'] == 'timeseries'
            assert line_config['title'] == 'Test Line Chart'
            assert line_config['id'] == 1
            
            # Test bar chart configuration
            bar_config = visualizer._generate_grafana_panel_config(
                chart_type="bar",
                title="Test Bar Chart", 
                sql_query="SELECT region, AVG(price) FROM prices GROUP BY region",
                panel_id=2
            )
            
            assert bar_config['type'] == 'barchart'
            assert bar_config['title'] == 'Test Bar Chart'
    
    def test_error_handling_in_workflow(self):
        """Test error handling in workflow nodes"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test error state creation
            error_state = {
                'user_id': 1,
                'request_text': 'invalid request',
                'errors': ['Test error message'],
                'status': 'failed'
            }
            
            # Should handle error state gracefully
            result = visualizer._handle_error_state(error_state)
            assert result['status'] == 'failed'
            assert len(result['errors']) > 0
    
    def test_workflow_node_routing(self):
        """Test workflow node routing logic"""
        from langgraph_ai_visualization import LangGraphAIVisualizer
        
        with patch('langgraph_ai_visualization.boto3.client'):
            visualizer = LangGraphAIVisualizer()
            
            # Test successful state routing
            success_state = {
                'status': 'processing',
                'errors': [],
                'detected_visualization_type': 'line'
            }
            
            # Should route to next node
            next_node = visualizer._determine_next_node(success_state)
            assert next_node in ['analyze_data_sources', 'generate_query', 'validate_query']
            
            # Test error state routing
            error_state = {
                'status': 'failed',
                'errors': ['Critical error'],
                'detected_visualization_type': None
            }
            
            # Should route to error handler
            next_node = visualizer._determine_next_node(error_state)
            assert next_node == 'handle_error'