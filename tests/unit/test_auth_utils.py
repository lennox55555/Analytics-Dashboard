"""
Unit tests for authentication utilities
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import jwt

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from auth_utils import AuthManager

class TestAuthManager:
    
    def test_hash_password(self):
        """Test password hashing"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            password = "test-password"
            hashed = auth_manager.hash_password(password)
            
            assert hashed != password
            assert auth_manager.verify_password(password, hashed)
    
    def test_verify_password_invalid(self):
        """Test password verification with invalid password"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            password = "test-password"
            hashed = auth_manager.hash_password(password)
            
            assert not auth_manager.verify_password("wrong-password", hashed)
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            user_data = {"user_id": 1, "email": "test@example.com"}
            
            token = auth_manager.create_access_token(user_data)
            
            assert isinstance(token, str)
            assert len(token) > 0
    
    def test_verify_token_valid(self):
        """Test valid token verification"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            user_data = {"user_id": 1, "email": "test@example.com"}
            
            token = auth_manager.create_access_token(user_data)
            decoded = auth_manager.verify_token(token)
            
            assert decoded["user_id"] == 1
            assert decoded["email"] == "test@example.com"
    
    def test_verify_token_expired(self):
        """Test expired token verification"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            user_data = {"user_id": 1, "email": "test@example.com"}
            
            # Create token with immediate expiration
            token = auth_manager.create_access_token(user_data, timedelta(seconds=-1))
            
            with pytest.raises(jwt.ExpiredSignatureError):
                auth_manager.verify_token(token)
    
    def test_verify_token_invalid(self):
        """Test invalid token verification"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            
            with pytest.raises(jwt.InvalidTokenError):
                auth_manager.verify_token("invalid-token")
    
    @patch('auth_utils.get_db_connection')
    def test_get_user_by_email(self, mock_get_db):
        """Test user retrieval by email"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            # Setup mock
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_conn
            
            mock_cursor.fetchone.return_value = {
                'id': 1,
                'email': 'test@example.com',
                'username': 'testuser',
                'password_hash': 'hashed-password'
            }
            
            auth_manager = AuthManager()
            user = auth_manager.get_user_by_email("test@example.com")
            
            assert user['id'] == 1
            assert user['email'] == 'test@example.com'
            mock_cursor.execute.assert_called_once()
    
    @patch('auth_utils.get_db_connection')
    def test_get_user_by_email_not_found(self, mock_get_db):
        """Test user retrieval when email not found"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            # Setup mock
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_conn
            
            mock_cursor.fetchone.return_value = None
            
            auth_manager = AuthManager()
            user = auth_manager.get_user_by_email("nonexistent@example.com")
            
            assert user is None
    
    def test_auth_manager_initialization(self):
        """Test AuthManager initialization"""
        with patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key-for-testing-purposes-only'}):
            auth_manager = AuthManager()
            assert auth_manager is not None
            assert hasattr(auth_manager, 'secret_key')