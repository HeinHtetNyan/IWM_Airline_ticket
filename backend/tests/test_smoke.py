"""
Smoke tests — these are the ONLY tests that run in CI.

Purpose: verify the app starts, connects to DB and Redis,
and core endpoints respond correctly.

Business logic is tested manually on staging after CD deploys.
These tests must stay fast (under 30 seconds total) 
"""

from fastapi.testclient import TestClient
from backend.app.main import app

# Single shared client — no fixtures, no conftest needed
client = TestClient(app)


# ── App startup 

def test_health_check():
    """App is running and healthy."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_root_endpoint():
    """Root endpoint responds."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


# ── API surface

def test_api_docs_load():
    """Swagger UI loads — proves all routes registered without import errors."""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_openapi_schema_valid():
    """OpenAPI schema generates — proves all route definitions are valid."""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
    assert "info" in data


# ── Error handling 

def test_unknown_route_returns_404_not_500():
    """Unknown routes return 404, not a server crash."""
    response = client.get("/api/this-does-not-exist-99999")
    assert response.status_code == 404


# ── Auth

def test_protected_endpoint_requires_auth():
    """Protected endpoints reject unauthenticated requests with 401."""
    response = client.get("/api/bookings/me")
    assert response.status_code == 401


def test_admin_endpoint_requires_auth():
    """Admin endpoints reject unauthenticated requests with 401 or 403."""
    response = client.get("/api/admin/dashboard")
    assert response.status_code in (401, 403)