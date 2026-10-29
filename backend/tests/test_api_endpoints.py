import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "JalRakshak"
    assert data["is_demo_data"] is True

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_status"] == "online"
    assert data["project"] == "JalRakshak"
    assert data["is_demo_data"] is True

def test_sources_endpoint():
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    source_ids = [s["id"] for s in data]
    assert "nasa_gpm_imerg" in source_ids
    assert "chirps_daily" in source_ids
    assert "srtm_dem" in source_ids
    assert "upsdma_imd" in source_ids

def test_flood_risk_endpoint_valid():
    response = client.get("/api/v1/risk/flood?location=gorakhpur")
    assert response.status_code == 200
    data = response.json()
    assert data["hazard"] == "flood"
    assert data["location"]["location_id"] == "gorakhpur"
    assert "indicators" in data
    assert len(data["indicators"]) >= 4
    assert data["is_demo_data"] is True

def test_flood_risk_endpoint_invalid_location():
    response = client.get("/api/v1/risk/flood?location=unknown_district_xyz")
    assert response.status_code == 400

def test_drought_risk_endpoint_valid():
    response = client.get("/api/v1/risk/drought?location=mahoba")
    assert response.status_code == 200
    data = response.json()
    assert data["hazard"] == "drought"
    assert data["location"]["location_id"] == "mahoba"
    assert "indicators" in data
    assert len(data["indicators"]) >= 4

def test_dashboard_endpoint():
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "metric_cards" in data
    assert len(data["metric_cards"]) == 4
    assert "recent_alerts" in data
    assert "pilot_locations" in data
    assert data["is_demo_data"] is True

def test_trends_rainfall_endpoint():
    # Test 30 days daily
    res_daily = client.get("/api/v1/trends/rainfall?location=gorakhpur&range=30&aggregation=daily")
    assert res_daily.status_code == 200
    data_daily = res_daily.json()
    assert data_daily["location_id"] == "gorakhpur"
    assert len(data_daily["series"]) > 0

    # Test 365 days monthly
    res_monthly = client.get("/api/v1/trends/rainfall?location=mahoba&range=365&aggregation=monthly")
    assert res_monthly.status_code == 200
    data_monthly = res_monthly.json()
    assert data_monthly["location_id"] == "mahoba"
    assert len(data_monthly["series"]) > 0

def test_map_layers_endpoint():
    response = client.get("/api/v1/map/layers?layer=flood")
    assert response.status_code == 200
    data = response.json()
    assert data["layer_type"] == "flood"
    assert "districts" in data
    assert len(data["districts"]) >= 9
    assert data["is_demo_data"] is True
