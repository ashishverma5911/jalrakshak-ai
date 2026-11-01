"""
Regression test suite for Milestone 7.2 Missing-Data Semantics.
Verifies scientific invariants:
1. Missing rainfall remains null (None in Python, null in JSON).
2. Genuine zero rainfall remains 0.0.
3. DATA_PENDING cannot produce a fabricated risk score.
4. Missing values cannot contaminate climatological averages.
5. Existing pilot-district results remain unchanged.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.engine.indicators import (
    calculate_cumulative_rainfall,
    calculate_rainfall_anomaly,
    count_wet_days,
    calculate_max_consecutive_dry_days,
    calculate_historical_percentile,
)
from app.engine.flood_engine import FloodRiskEngine
from app.engine.drought_engine import DroughtRiskEngine
from app.pipeline.precipitation_pipeline import PrecipitationIngestionService
from app.pipeline.spatial_aggregation import SpatialAggregator

client = TestClient(app)


# ==============================================================================
# INVARIANT 1: Missing rainfall remains null
# ==============================================================================
def test_missing_rainfall_remains_null_in_indicators():
    """All-NaN / missing observation slices return None, never 0.0."""
    df_missing = pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=7),
        "rainfall_mm": [None, np.nan, None, np.nan, None, np.nan, None],
    })
    result = calculate_cumulative_rainfall(df_missing, window_days=7)
    assert result is None, f"Expected None for missing observations, got {result}"

    wet_days = count_wet_days(df_missing, window_days=7)
    assert wet_days is None, f"Expected None for wet days on missing series, got {wet_days}"

    dry_days = calculate_max_consecutive_dry_days(df_missing, window_days=7)
    assert dry_days is None, f"Expected None for dry days on missing series, got {dry_days}"


def test_missing_rainfall_remains_null_in_dashboard_api():
    """Candidate districts with unlinked telemetry return null for metric values and is_data_available=False."""
    resp = client.get("/api/v1/dashboard?location=lucknow")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "DATA_PENDING"
    assert data["is_data_available"] is False

    for card in data["metric_cards"]:
        assert card["value"] is None, f"Card '{card['title']}' value must be null for candidate district, got {card['value']}"
        assert card["delta_percentage"] is None
        assert card["is_positive_delta"] is None
        assert card["is_data_available"] is False
        assert card["hazard_type"] == "pending"


def test_missing_rainfall_ingestion_service_preserves_missing():
    """PrecipitationIngestionService validates None/NaN as (None, 'missing')."""
    val, status = PrecipitationIngestionService.validate_observation(None)
    assert val is None
    assert status == "missing"

    val_nan, status_nan = PrecipitationIngestionService.validate_observation(float("nan"))
    assert val_nan is None
    assert status_nan == "missing"


# ==============================================================================
# INVARIANT 2: Genuine zero rainfall remains 0.0
# ==============================================================================
def test_genuine_zero_rainfall_remains_zero_in_indicators():
    """Genuine observed zero rainfall (0.0) is preserved as 0.0 and distinct from missing."""
    df_zero = pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=7),
        "rainfall_mm": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    })
    result = calculate_cumulative_rainfall(df_zero, window_days=7)
    assert result == 0.0
    assert isinstance(result, float)
    assert result is not None

    # Anomaly for 0.0 against baseline 50.0 should be -100.0% departure
    anomaly = calculate_rainfall_anomaly(0.0, baseline_mean_mm=50.0)
    assert anomaly == -100.0

    wet = count_wet_days(df_zero, window_days=7)
    assert wet == 0

    dry = calculate_max_consecutive_dry_days(df_zero, window_days=7)
    assert dry == 7


def test_genuine_zero_rainfall_ingestion_service():
    """PrecipitationIngestionService validates 0.0 as (0.0, 'zero_precipitation')."""
    val, status = PrecipitationIngestionService.validate_observation(0.0)
    assert val == 0.0
    assert isinstance(val, float)
    assert status == "zero_precipitation"


# ==============================================================================
# INVARIANT 3: DATA_PENDING cannot produce a fabricated risk score
# ==============================================================================
def test_data_pending_cannot_produce_fabricated_flood_risk():
    """Evaluating flood risk on unlinked candidate district returns risk_level='pending', not 'low'."""
    cand_info = {
        "id": "lucknow",
        "name": "Lucknow",
        "hindi_name": "लखनऊ",
        "lat": 26.8467,
        "lng": 80.9462,
        "elevation_m": 123.0,
        "river_basin": "Gomti River Basin",
        "region": "Central Plain",
        "is_pilot": False,
    }
    empty_df = pd.DataFrame(columns=["date", "rainfall_mm"])

    eval_result = FloodRiskEngine.evaluate(cand_info, empty_df)
    assert eval_result.risk_level == "pending", f"Must NOT fabricate risk score, got {eval_result.risk_level}"
    assert eval_result.data_mode == "DATA_PENDING"
    assert eval_result.is_data_available is False

    for ind in eval_result.indicators:
        assert ind.value is None, f"Indicator {ind.indicator_id} value must be null, got {ind.value}"
        assert ind.is_data_available is False
        assert ind.quality_status == "missing"


def test_data_pending_cannot_produce_fabricated_drought_risk():
    """Evaluating drought risk on unlinked candidate district returns risk_level='pending', not 'low'."""
    cand_info = {
        "id": "patna",
        "name": "Patna",
        "hindi_name": "पटना",
        "lat": 25.5941,
        "lng": 85.1376,
        "elevation_m": 53.0,
        "river_basin": "Middle Ganga Basin",
        "region": "South Bihar Plain",
        "is_pilot": False,
    }
    empty_df = pd.DataFrame(columns=["date", "rainfall_mm"])

    eval_result = DroughtRiskEngine.evaluate(cand_info, empty_df)
    assert eval_result.risk_level == "pending", f"Must NOT fabricate risk score, got {eval_result.risk_level}"
    assert eval_result.data_mode == "DATA_PENDING"
    assert eval_result.is_data_available is False

    for ind in eval_result.indicators:
        assert ind.value is None, f"Indicator {ind.indicator_id} value must be null, got {ind.value}"
        assert ind.is_data_available is False
        assert ind.quality_status == "missing"


def test_verified_map_layers_marks_candidates_as_pending():
    """In verified mode, candidate districts report pending risk and null anomalies."""
    resp = client.get("/api/v1/map/layers?layer=flood&mode=verified")
    assert resp.status_code == 200
    data = resp.json()

    candidates = [d for d in data["districts"] if not d["is_pilot"]]
    assert len(candidates) > 0

    for cand in candidates:
        assert cand["flood_risk"] == "pending"
        assert cand["drought_risk"] == "pending"
        assert cand["rainfall_anomaly_pct"] is None
        assert cand["spi3"] is None
        assert cand["is_data_available"] is False
        assert cand["data_quality"] == "data_pending"


# ==============================================================================
# INVARIANT 4: Missing values cannot contaminate climatological averages
# ==============================================================================
def test_missing_values_excluded_from_cumulative_and_anomalies():
    """Intermittent missing values are excluded, not coerced to 0 that would drag down totals."""
    df_partial = pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=5),
        "rainfall_mm": [10.0, None, 20.0, np.nan, 30.0],
    })
    # Valid sum should be 10 + 20 + 30 = 60.0
    total = calculate_cumulative_rainfall(df_partial, window_days=5)
    assert total == 60.0

    # Wet days count should evaluate only non-null values
    wet = count_wet_days(df_partial, threshold_mm=2.5, window_days=5)
    assert wet == 3


def test_spatial_aggregation_skips_missing_grid_cells():
    """Grid observations with None/NaN rainfall are skipped and do not pull down area-weighted mean."""
    grid_obs = [
        {"lat": 26.76, "lng": 83.37, "rainfall_mm": 50.0},
        {"lat": 26.75, "lng": 83.36, "rainfall_mm": None},  # Missing cell
        {"lat": 26.77, "lng": 83.38, "rainfall_mm": 50.0},
    ]
    res = SpatialAggregator.aggregate_gridded_precipitation("district-gorakhpur", grid_obs)
    assert res["area_weighted_rainfall_mm"] == 50.0
    assert res["cells_intersected"] == 2


# ==============================================================================
# INVARIANT 5: Existing pilot-district results remain unchanged
# ==============================================================================
def test_pilot_district_gorakhpur_flood_risk_unimpaired():
    """Verified and Demo Gorakhpur flood evaluations retain exact scientific outputs."""
    # Demo mode: Prototype fixtures simulate active monsoon surge
    resp_demo = client.get("/api/v1/risk/flood?location=gorakhpur&mode=demo")
    assert resp_demo.status_code == 200
    data_demo = resp_demo.json()
    assert data_demo["data_mode"] == "DEMONSTRATION"
    assert data_demo["is_data_available"] is True
    assert data_demo["risk_level"] == "high"
    r7d_demo = next(i for i in data_demo["indicators"] if i["indicator_id"] == "flood_precip_7d_accum")
    assert r7d_demo["value"] is not None
    assert r7d_demo["value"] >= 180.0
    assert r7d_demo["is_data_available"] is True

    # Verified mode: Evaluates genuine CHIRPS observations
    resp_ver = client.get("/api/v1/risk/flood?location=gorakhpur&mode=verified")
    assert resp_ver.status_code == 200
    data_ver = resp_ver.json()
    assert data_ver["data_mode"] == "CACHED_VERIFIED"
    assert data_ver["is_data_available"] is True
    assert data_ver["location"]["name"] == "Gorakhpur"
    assert data_ver["location"]["is_pilot"] is True
    r7d_ver = next(i for i in data_ver["indicators"] if i["indicator_id"] == "flood_precip_7d_accum")
    assert r7d_ver["value"] is not None
    assert r7d_ver["is_data_available"] is True


def test_pilot_district_mahoba_drought_risk_unimpaired():
    """Verified and Demo Mahoba drought evaluations retain exact scientific outputs."""
    # Demo mode: Prototype fixture
    resp_demo = client.get("/api/v1/risk/drought?location=mahoba&mode=demo")
    assert resp_demo.status_code == 200
    data_demo = resp_demo.json()
    assert data_demo["data_mode"] == "DEMONSTRATION"
    assert data_demo["is_data_available"] is True
    assert data_demo["risk_level"] in ["moderate", "high"]
    r90d_demo = next(i for i in data_demo["indicators"] if i["indicator_id"] == "drought_precip_90d_accum")
    assert r90d_demo["value"] is not None
    assert r90d_demo["is_data_available"] is True

    # Verified mode: Evaluates genuine CHIRPS observations
    resp_ver = client.get("/api/v1/risk/drought?location=mahoba&mode=verified")
    assert resp_ver.status_code == 200
    data_ver = resp_ver.json()
    assert data_ver["data_mode"] == "CACHED_VERIFIED"
    assert data_ver["is_data_available"] is True
    assert data_ver["risk_level"] in ["moderate", "high"]
    assert data_ver["location"]["name"] == "Mahoba"
    assert data_ver["location"]["is_pilot"] is True
    r90d_ver = next(i for i in data_ver["indicators"] if i["indicator_id"] == "drought_precip_90d_accum")
    assert r90d_ver["value"] is not None
    assert r90d_ver["is_data_available"] is True


def test_dashboard_overview_pilot_defaults():
    """Dashboard default overview returns is_data_available=True and valid metrics for pilots."""
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_data_available"] is True
    assert len(data["metric_cards"]) == 4

    for card in data["metric_cards"]:
        assert card["value"] is not None
        assert card["is_data_available"] is True
