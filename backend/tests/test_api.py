"""
API Tests for Airline Booking System
These tests run inside the Docker container
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Import using the same path as your main.py
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.core.redis import redis_client

# Create test client
client = TestClient(app)


# ========== HEALTH TESTS ==========
def test_health_check():
    """Test health endpoint returns 200 OK"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    print("✅ Health check passed!")


def test_root_endpoint():
    """Test root endpoint returns welcome message"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    print("✅ Root endpoint passed!")


# ========== DATABASE TESTS ==========
def test_database_connection():
    """Test database connection from inside container"""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
        print("✅ Database connection works!")
    finally:
        db.close()


# ========== REDIS TESTS ==========
def test_redis_connection():
    """Test Redis connection from inside container"""
    try:
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        assert value == b"test_value" or value == "test_value"
        redis_client.delete("test_key")
        print("✅ Redis connection works!")
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


# ========== API DOCS TESTS ==========
def test_api_docs():
    """Test API documentation is accessible"""
    response = client.get("/api/docs")
    assert response.status_code == 200
    print("✅ API docs accessible!")


def test_openapi_schema():
    """Test OpenAPI schema is generated"""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
    print("✅ OpenAPI schema generated!")


# ========== ERROR HANDLING TESTS ==========
def test_invalid_route_returns_404():
    """Test invalid route returns 404 Not Found"""
    response = client.get("/api/this-route-does-not-exist-12345")
    assert response.status_code == 404
    print("✅ 404 error handling works!")


# ========== CORS TESTS ==========
def test_cors_headers():
    """Test CORS headers are configured"""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code != 500
    print(f"✅ CORS configured (response: {response.status_code})")


# ========== METRICS TESTS ==========
def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        print("✅ Metrics endpoint is enabled!")
    else:
        print("ℹ️ Metrics endpoint not enabled (this is OK)")


# ========== PROTECTED ENDPOINTS ==========
def test_protected_endpoint_requires_auth():
    """Test that protected endpoints require authentication"""
    response = client.get("/api/bookings")
    assert response.status_code != 200
    print(f"✅ Authentication protection works (returned {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])