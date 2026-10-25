import pytest
from fastapi.testclient import TestClient
from main import app

# Create a test client
client = TestClient(app)

# ==========================================
# Test 1: Health Check (Happy Path)
# ==========================================
def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# ==========================================
# Test 2: Security - Missing User ID (Validation)
# ==========================================
def test_create_report_without_user_id():
    payload = {
        "segment_id": 1,
        "report_type": "Theft",
        "description": "Test without header"
    }
    # We intentionally DO NOT send the X-User-Id header
    response = client.post("/api/v1/reports", json=payload)
    
    # Should be 422 Unprocessable Entity (Missing required Header)
    assert response.status_code == 422

# ==========================================
# Test 3: Validation - Invalid Coordinates
# ==========================================
def test_route_invalid_coordinates():
    payload = {
        "origin_lat": 999, # INVALID (must be between -90 and 90)
        "origin_lng": 78.4867,
        "dest_lat": 17.3980,
        "dest_lng": 78.4980,
        "preference": "car",
        "priority": "safety"
    }
    response = client.post("/api/v1/route", json=payload)
    
    # Should be 422 because Pydantic blocks the bad latitude
    assert response.status_code == 422

# ==========================================
# Test 4: Access Control - Wrong User Delete
# ==========================================
def test_delete_wrong_user_report():
    # User 999 tries to delete report 1
    headers = {"X-User-Id": "999"}
    response = client.delete("/api/v1/reports/1", headers=headers)
    
    # Should be 403 Forbidden (User 999 does not own report 1)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]