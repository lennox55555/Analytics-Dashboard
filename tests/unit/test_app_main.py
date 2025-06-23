"""
Unit tests for main FastAPI application
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TestAppMain:
    
    @patch('src.app.get_db_connection')
    def test_health_endpoint_healthy(self, mock_get_db):
        """Test health endpoint when system is healthy"""
        from src.app import app
        client = TestClient(app)
        
        # Mock successful database connection
        mock_conn = Mock()
        mock_get_db.return_value = mock_conn
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @patch('src.app.get_db_connection')
    def test_health_endpoint_db_error(self, mock_get_db):
        """Test health endpoint when database is unavailable"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database connection failure
        mock_get_db.side_effect = Exception("Database connection failed")
        
        response = client.get("/health")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Database connection failed" in data["detail"]
    
    def test_root_endpoint(self):
        """Test root endpoint returns HTML"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_docs_endpoint(self):
        """Test API documentation endpoint"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_endpoint(self):
        """Test OpenAPI schema endpoint"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
    
    @patch('src.app.get_db_connection')
    def test_api_data_endpoint_valid_table(self, mock_get_db):
        """Test API data endpoint with valid table"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"timestamp": "2024-01-01T00:00:00", "hb_busavg": 25.50}
        ]
        mock_get_db.return_value = mock_conn
        
        response = client.get("/api/data?table=ercot_settlement_prices&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 0
    
    def test_api_data_endpoint_invalid_table(self):
        """Test API data endpoint with invalid table"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/api/data?table=invalid_table")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_api_data_endpoint_missing_table(self):
        """Test API data endpoint without table parameter"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/api/data")
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.app.get_db_connection')
    def test_api_ercot_data_endpoint(self, mock_get_db):
        """Test ERCOT data endpoint"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"timestamp": "2024-01-01T00:00:00", "hb_busavg": 25.50}
        ]
        mock_get_db.return_value = mock_conn
        
        response = client.get("/api/ercot-data")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_cors_headers(self):
        """Test CORS headers are set"""
        from src.app import app
        client = TestClient(app)
        
        response = client.options("/")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
    
    def test_iframe_headers(self):
        """Test iframe headers are set"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/health")
        
        # Should have iframe headers
        assert response.headers.get("x-frame-options") == "ALLOWALL"
        assert "frame-ancestors *" in response.headers.get("content-security-policy", "")
    
    @patch('src.app.AI_SYSTEM_AVAILABLE', True)
    @patch('src.app.get_current_user')
    def test_ai_visualization_endpoint_auth_required(self, mock_get_user):
        """Test AI visualization endpoint requires authentication"""
        from src.app import app
        client = TestClient(app)
        
        # No authentication provided
        response = client.post("/api/ai/visualizations", json={"request_text": "test"})
        
        assert response.status_code in [401, 403]  # Unauthorized or Forbidden
    
    def test_auth_me_endpoint_no_token(self):
        """Test auth/me endpoint without token"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/api/auth/me")
        
        # Should return not authenticated
        data = response.json()
        assert data["authenticated"] is False