from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Create test client
client = TestClient(app)

def test_health_check():
    """Test that health endpoint works"""
    response = client.get("/api/health")
    assert response.status_code == 200
    # Check if response has status field
    data = response.json()
    assert "status" in data

def test_docs_available():
    """Test that API docs are accessible"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_api_root():
    """Test API root endpoint"""
    response = client.get("/")
    # Root might redirect or return something
    assert response.status_code in [200, 307, 404]