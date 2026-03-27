import sys
import os

# Add the parent directory to path so Python can find the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    def test_health_check():
        """Test health endpoint"""
        # Try different possible health endpoint paths
        response = client.get("/api/health")
        assert response.status_code == 200
        
    def test_app_exists():
        """Test that app exists"""
        assert app is not None
        
except ImportError as e:
    # If import fails, create a dummy test that passes but shows the error
    import pytest
    print(f"Import error: {e}")
    
    def test_import_error():
        """Test that shows import error"""
        assert False, f"Failed to import app: {e}"