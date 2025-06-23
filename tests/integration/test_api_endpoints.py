"""
Integration tests for API endpoints
"""
import pytest
from unittest.mock import patch
import json

class TestAPIEndpoints:
    
    def test_health_endpoint(self, app_client):
        """Test health check endpoint"""
        response = app_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, app_client):
        """Test root endpoint returns HTML"""
        response = app_client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_docs_endpoint(self, app_client):
        """Test API documentation endpoint"""
        response = app_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_auth_me_without_token(self, app_client):
        """Test /api/auth/me without authentication"""
        response = app_client.get("/api/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
    
    def test_login_invalid_credentials(self, app_client):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = app_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_register_missing_fields(self, app_client):
        """Test registration with missing required fields"""
        register_data = {
            "email": "test@example.com"
            # Missing username and password
        }
        
        response = app_client.post("/api/auth/register", json=register_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_ai_visualization_without_auth(self, app_client):
        """Test AI visualization endpoint without authentication"""
        ai_request = {
            "request_text": "Show me settlement prices"
        }
        
        response = app_client.post("/api/ai/visualizations/langgraph", json=ai_request)
        
        assert response.status_code == 401  # Unauthorized
    
    def test_dashboard_settings_without_auth(self, app_client):
        """Test dashboard settings endpoint without authentication"""
        response = app_client.get("/api/dashboard/settings")
        
        assert response.status_code == 401  # Unauthorized
    
    @patch('src.app.get_current_user')
    def test_dashboard_settings_with_auth(self, mock_get_user, app_client, mock_db_connection):
        """Test dashboard settings endpoint with authentication"""
        # Mock authenticated user
        mock_get_user.return_value = {"id": 1, "email": "test@example.com"}
        
        # Mock database response
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = []
        
        response = app_client.get("/api/dashboard/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_api_data_endpoint(self, app_client, mock_db_connection):
        """Test API data endpoint"""
        # Mock database response
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = [
            {"timestamp": "2024-01-01T00:00:00", "hb_busavg": 25.50}
        ]
        
        response = app_client.get("/api/data?table=ercot_settlement_prices&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_api_data_invalid_table(self, app_client):
        """Test API data endpoint with invalid table"""
        response = app_client.get("/api/data?table=invalid_table")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data