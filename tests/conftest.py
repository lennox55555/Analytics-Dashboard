"""
Pytest configuration and fixtures for ERCOT Analytics Dashboard tests
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scrapers'))

@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing"""
    with patch('psycopg2.connect') as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn, mock_cursor

@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client for testing"""
    with patch('boto3.client') as mock_client:
        mock_bedrock = Mock()
        mock_client.return_value = mock_bedrock
        yield mock_bedrock

@pytest.fixture
def test_env_vars():
    """Set test environment variables"""
    test_vars = {
        'DB_HOST': 'test-host',
        'DB_NAME': 'test-analytics',
        'DB_USER': 'test-user',
        'DB_PASSWORD': 'test-password',
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'AWS_ACCESS_KEY_ID': 'test-access-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        'GRAFANA_URL': 'http://test-grafana:3000'
    }
    
    # Store original values
    original_values = {}
    for key, value in test_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture
def app_client(test_env_vars, mock_db_connection):
    """Create FastAPI test client"""
    from src.app import app
    client = TestClient(app)
    yield client