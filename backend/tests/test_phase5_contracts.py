import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_map_layers_geometry_transparency():
    response = client.get("/api/v1/map/layers?layer=flood")
    assert response.status_code == 200
    data = response.json()

    # Must explicitly declare geometry status
    assert data["geometry_available"] is False
    assert data["geometry_status"] == "centroid_coordinates_only"
    assert "geometry_disclaimer" in data
    assert "District centroid coordinates provided under WGS84" in data["geometry_disclaimer"]
    assert data["is_demo_data"] is True

    # District features must contain centroid coords and observation metadata
    districts = data["districts"]
    assert len(districts) >= 2
    gorakhpur = next((d for d in districts if d["district_id"] == "gorakhpur"), None)
    mahoba = next((d for d in districts if d["district_id"] == "mahoba"), None)

    assert gorakhpur is not None
    assert gorakhpur["is_pilot"] is True
    assert gorakhpur["geometry_type"] == "centroid_point"
    assert gorakhpur["geometry_available"] is False

    assert mahoba is not None
    assert mahoba["is_pilot"] is True
    assert mahoba["geometry_type"] == "centroid_point"

def test_rainfall_trends_missing_vs_zero_distinction():
    response = client.get("/api/v1/trends/rainfall?location=gorakhpur&range=30&aggregation=daily")
    assert response.status_code == 200
    data = response.json()

    assert "series" in data
    assert len(data["series"]) > 0
    assert data["data_coverage_pct"] == 100.0
    assert "disclaimer" in data
    assert "Does not represent or imply a predictive weather forecast" in data["disclaimer"]

    # Verify points distinguish zero measured rain
    for pt in data["series"]:
        assert "data_quality" in pt
        if pt["observed_rainfall_mm"] == 0.0:
            assert pt["is_zero_measured"] is True
            assert pt["data_quality"] == "zero_precipitation"
        elif pt["observed_rainfall_mm"] is not None and pt["observed_rainfall_mm"] > 0.0:
            assert pt["is_zero_measured"] is False
            assert pt["data_quality"] == "observed"

def test_health_distinct_diagnostics_reporting():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["api_status"] == "online"

    # Distinct data freshness object
    assert "data_freshness" in data
    assert data["data_freshness"]["source_type"] == "local_cached_baseline"
    assert data["data_freshness"]["is_stale"] is False

    # Distinct model runtime object (never falsely claims live neural execution)
    assert "model_runtime" in data
    assert data["model_runtime"]["fallback_engine"] == "deterministic_grounded_rules"
    assert "Neural runtime availability is verified dynamically per query" in data["model_runtime"]["runtime_disclaimer"]

def test_sources_metadata_fidelity():
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    sources = response.json()

    assert len(sources) >= 4
    source_ids = [s.get("id") or s.get("source_id") for s in sources]
    assert "nasa_gpm_imerg" in source_ids
    assert "chirps_daily" in source_ids
    assert "srtm_dem" in source_ids
    assert "upsdma_imd" in source_ids
