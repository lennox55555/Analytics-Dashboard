"""
Integration tests for full application workflows
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TestFullWorkflow:
    
    @patch('src.app.get_db_connection')
    def test_user_registration_workflow(self, mock_get_db):
        """Test complete user registration workflow"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock no existing user
        mock_cursor.fetchone.return_value = None
        # Mock successful insertion
        mock_cursor.execute.return_value = None
        mock_conn.commit.return_value = None
        
        # Register new user
        registration_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "securepassword123"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"
    
    @patch('src.app.get_db_connection')
    def test_user_login_workflow(self, mock_get_db):
        """Test complete user login workflow"""
        from src.app import app
        from src.auth_utils import AuthManager
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Create test user with hashed password
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            hashed_password = auth_manager.hash_password("testpassword")
        
        # Mock user exists with correct password
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'email': 'test@example.com',
            'username': 'testuser',
            'password_hash': hashed_password,
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Login user
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"
    
    @patch('src.app.get_db_connection')
    def test_dashboard_customization_workflow(self, mock_get_db):
        """Test dashboard customization workflow"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock user authentication
        with patch('src.app.get_current_user') as mock_get_user:
            mock_get_user.return_value = {"id": 1, "email": "test@example.com"}
            
            # Mock dashboard settings
            mock_cursor.fetchall.return_value = [
                {
                    'panel_id': 'chart1',
                    'panel_name': 'Price Chart',
                    'is_visible': True,
                    'panel_order': 1
                }
            ]
            
            # Get dashboard settings
            response = client.get("/api/dashboard/settings")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            
            # Update dashboard settings
            settings_update = [
                {
                    'panel_id': 'chart1',
                    'is_visible': False,
                    'panel_order': 1
                }
            ]
            
            response = client.post("/api/dashboard/settings", json=settings_update)
            
            assert response.status_code == 200
    
    @patch('src.app.get_db_connection')
    def test_api_key_management_workflow(self, mock_get_db):
        """Test API key management workflow"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock user authentication
        with patch('src.app.get_current_user') as mock_get_user:
            mock_get_user.return_value = {"id": 1, "email": "test@example.com"}
            
            # Mock no existing API keys
            mock_cursor.fetchall.return_value = []
            
            # Create new API key
            api_key_data = {
                "key_name": "Test API Key",
                "permissions": ["read"],
                "rate_limit_per_hour": 1000
            }
            
            # Mock successful API key creation
            mock_cursor.fetchone.return_value = {'id': 1}
            
            response = client.post("/api/keys", json=api_key_data)
            
            assert response.status_code == 201
            data = response.json()
            assert "api_key" in data
            assert "api_secret" in data
    
    @patch('src.app.get_db_connection')
    def test_data_retrieval_workflow(self, mock_get_db):
        """Test data retrieval workflow"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock price data
        mock_cursor.fetchall.return_value = [
            {
                'timestamp': '2024-01-01T00:00:00Z',
                'hb_busavg': 25.50,
                'hb_houston': 26.00,
                'hb_north': 24.50
            },
            {
                'timestamp': '2024-01-01T00:15:00Z',
                'hb_busavg': 25.75,
                'hb_houston': 26.25,
                'hb_north': 24.75
            }
        ]
        
        # Get settlement prices
        response = client.get("/api/data?table=ercot_settlement_prices&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['hb_busavg'] == 25.50
    
    @patch('src.app.get_db_connection')
    def test_error_handling_workflow(self, mock_get_db):
        """Test error handling throughout application"""
        from src.app import app
        client = TestClient(app)
        
        # Test database connection error
        mock_get_db.side_effect = Exception("Database connection failed")
        
        # Health check should show unhealthy
        response = client.get("/health")
        assert response.status_code == 503
        
        # Data endpoint should return error
        response = client.get("/api/data?table=ercot_settlement_prices")
        assert response.status_code == 500
    
    def test_application_security_headers(self):
        """Test security headers are properly set"""
        from src.app import app
        client = TestClient(app)
        
        response = client.get("/health")
        
        # Check security headers
        assert response.headers.get("x-frame-options") == "ALLOWALL"
        assert "frame-ancestors *" in response.headers.get("content-security-policy", "")
        assert response.headers.get("x-content-type-options") == "nosniff"
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        from src.app import app
        client = TestClient(app)
        
        # Test preflight request
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should allow CORS
        assert "access-control-allow-origin" in response.headers
    
    def test_input_validation(self):
        """Test input validation across endpoints"""
        from src.app import app
        client = TestClient(app)
        
        # Test invalid registration data
        invalid_registration = {
            "email": "invalid-email",  # Invalid email format
            "username": "",  # Empty username
            "password": "123"  # Too short password
        }
        
        response = client.post("/api/auth/register", json=invalid_registration)
        assert response.status_code == 422  # Validation error
    
    @patch('src.app.get_db_connection')
    def test_pagination_workflow(self, mock_get_db):
        """Test data pagination workflow"""
        from src.app import app
        client = TestClient(app)
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Mock large dataset
        mock_data = []
        for i in range(50):
            mock_data.append({
                'timestamp': f'2024-01-01T{i:02d}:00:00Z',
                'hb_busavg': 25.0 + i * 0.1
            })
        
        mock_cursor.fetchall.return_value = mock_data
        
        # Test with limit parameter
        response = client.get("/api/data?table=ercot_settlement_prices&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        # Should respect limit in SQL query
        mock_cursor.execute.assert_called()
        sql_call = mock_cursor.execute.call_args[0][0]
        assert "LIMIT 10" in sql_call