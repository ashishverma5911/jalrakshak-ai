"""
Milestone 6 Integration & Verification Test Suite for JalRakshak AI
Validates:
1. Real-world CHIRPS v2.0 daily observations & 1991–2020 climatological normal calculations.
2. Scientific precipitation quality validation: negative rainfall rejection & provisional extreme flagging.
3. NASA SRTM 30m Digital Elevation Model terrain analysis & flood/drought vulnerability scoring.
4. Area-weighted spatial aggregation & strict exclusion of out-of-boundary grid cells.
5. SPI-3 calculation with historical series and explicit refusal on insufficient series.
6. Official government alerts (IMD & UPSDMA) retrieval and transparent API limitation handling.
7. Two-district strict pilot scope: Gorakhpur (Flood) and Mahoba (Drought).
8. Candidate district isolation: Lucknow, Patna, Gaya, Varanasi must remain DATA_PENDING with zero data bleed.
9. Multi-mode API responses: DEMONSTRATION vs CACHED_VERIFIED / LIVE_VERIFIED vs DATA_PENDING.
10. Gemma 4 Grounded Assistant deterministic fallback referencing verified observations and safety disclosures.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.chirps_pipeline import CHIRPSPipeline
from app.pipeline.gpm_pipeline import GPMIMERGPipeline
from app.pipeline.srtm_pipeline import SRTMElevationPipeline, SRTM_DISTRICT_BENCHMARKS
from app.pipeline.spatial_aggregation import SpatialAggregator, SpatialAggregationError
from app.pipeline.official_alerts import OfficialAlertsPipeline
from app.pipeline.validation import DataValidator, PrecipitationValidationError
from app.pipeline.ingestion import DataIngestionService
from app.engine.flood_engine import FloodRiskEngine
from app.engine.drought_engine import DroughtRiskEngine
from app.engine.spi import SPIEngine
from app.engine.assistant_engine import GroundedAssistantEngine
from app.schemas.common import DataMode

client = TestClient(app)
ingestion = DataIngestionService()


# ---------------------------------------------------------------------------
# 1. Genuine CHIRPS Observations & Climatological Normals
# ---------------------------------------------------------------------------
def test_chirps_verified_observations_loading():
    """Verify loading of genuine verified CHIRPS daily series for Gorakhpur and Mahoba."""
    # Gorakhpur verified observations
    df_gkp = CHIRPSPipeline.load_verified_daily_series("gorakhpur")
    assert not df_gkp.empty
    assert len(df_gkp) >= 4000, f"Expected >= 4000 daily records, got {len(df_gkp)}"
    assert (df_gkp["rainfall_mm"] >= 0.0).all(), "Detected negative rainfall values"
    assert df_gkp["rainfall_mm"].isna().sum() == 0, "Null values found in continuous observation record"
    assert "date" in df_gkp.columns
    assert "rainfall_mm" in df_gkp.columns

    # Mahoba verified observations
    df_mhb = CHIRPSPipeline.load_verified_daily_series("mahoba")
    assert not df_mhb.empty
    assert len(df_mhb) >= 4000, f"Expected >= 4000 daily records, got {len(df_mhb)}"
    assert (df_mhb["rainfall_mm"] >= 0.0).all(), "Detected negative rainfall values"
    assert df_mhb["rainfall_mm"].isna().sum() == 0, "Null values found in continuous observation record"


def test_chirps_climatological_normals_1991_2020():
    """Verify 30-year (1991–2020) climatological normals and monthly lookups."""
    normals = CHIRPSPipeline.load_climatological_normals()
    assert "district-gorakhpur" in normals
    assert "district-mahoba" in normals

    # Gorakhpur normals
    gkp_norm = normals["district-gorakhpur"]
    assert gkp_norm["annual_normal_mm"] == pytest.approx(1151.4, abs=5.0)
    assert gkp_norm["monsoon_normal_mm"] == pytest.approx(996.7, abs=5.0)
    gkp_oct = CHIRPSPipeline.get_district_monthly_normal("district-gorakhpur", 10)
    assert gkp_oct == pytest.approx(40.2, abs=2.0)

    # Mahoba normals
    mhb_norm = normals["district-mahoba"]
    assert mhb_norm["annual_normal_mm"] == pytest.approx(943.6, abs=5.0)
    assert mhb_norm["monsoon_normal_mm"] == pytest.approx(845.4, abs=5.0)
    mhb_oct = CHIRPSPipeline.get_district_monthly_normal("district-mahoba", 10)
    assert mhb_oct == pytest.approx(27.1, abs=2.0)

    # Candidate district raises SpatialAggregationError (uncalibrated)
    with pytest.raises(SpatialAggregationError):
        CHIRPSPipeline.get_district_monthly_normal("district-lucknow", 10)


# ---------------------------------------------------------------------------
# 2. Precipitation Quality Validation
# ---------------------------------------------------------------------------
def test_precipitation_negative_rejection():
    """Physically impossible negative rainfall must be rejected."""
    with pytest.raises(PrecipitationValidationError):
        GPMIMERGPipeline.validate_gpm_record({"rainfall_mm": -4.2, "date": "2026-10-01"})


def test_precipitation_provisional_extreme_flagging():
    """Values > 500 mm must be flagged as provisional_extreme, not discarded."""
    extreme_record = {
        "date": "2026-10-01",
        "rainfall_mm": 542.0,
        "lat": 26.76,
        "lng": 83.37
    }
    validated = GPMIMERGPipeline.validate_gpm_record(extreme_record)
    assert validated["quality_status"] == "provisional_extreme"
    assert validated["rainfall_mm"] == 542.0
    assert "review_flag" in validated


# ---------------------------------------------------------------------------
# 3. NASA SRTM 30m Elevation Benchmarks
# ---------------------------------------------------------------------------
def test_srtm_30m_elevation_benchmarks():
    """Verify SRTM 30m elevation terrain metrics for alluvial Terai vs Bundelkhand plateau."""
    gkp_elev = SRTMElevationPipeline.get_elevation_profile("district-gorakhpur")
    assert gkp_elev["mean_elevation_m"] == pytest.approx(77.7, abs=1.0)
    assert gkp_elev["elevation_std_m"] == pytest.approx(2.7, abs=0.5)
    assert gkp_elev["terrain_vulnerability_index"] > 0.80  # Low-lying alluvial floodplain

    mhb_elev = SRTMElevationPipeline.get_elevation_profile("district-mahoba")
    assert mhb_elev["mean_elevation_m"] == pytest.approx(197.1, abs=2.0)
    assert mhb_elev["elevation_std_m"] == pytest.approx(29.9, abs=2.0)
    assert mhb_elev["terrain_vulnerability_index"] < 0.25  # High rocky plateau

    # Candidate district lacking verified polygon boundary must raise SpatialAggregationError
    with pytest.raises(SpatialAggregationError):
        SRTMElevationPipeline.get_elevation_profile("district-lucknow")


# ---------------------------------------------------------------------------
# 4. Area-Weighted Spatial Aggregation & Boundary Enforcement
# ---------------------------------------------------------------------------
def test_spatial_aggregation_with_boundary_intersection():
    """Area-weighted spatial aggregation over Gorakhpur verified polygon boundary."""
    # Synthetic grid points inside Gorakhpur bounding box
    grid_obs = [
        {"lat": 26.76, "lng": 83.37, "rainfall_mm": 20.0},
        {"lat": 26.80, "lng": 83.45, "rainfall_mm": 30.0},
        {"lat": 25.00, "lng": 80.00, "rainfall_mm": 100.0},  # Completely outside Gorakhpur
    ]
    res = SpatialAggregator.aggregate_gridded_precipitation(
        "district-gorakhpur",
        grid_obs,
        resolution_deg=0.05
    )
    assert res["cells_intersected"] >= 1
    # Point outside (lat 25, lng 80) must be discarded; mean must be between 20 and 30 mm
    assert 20.0 <= res["area_weighted_rainfall_mm"] <= 30.0
    assert res["aggregation_method"] == "area_weighted_polygon_intersection"


def test_spatial_aggregation_refusal_for_unverified_boundary():
    """Spatial aggregation must explicitly refuse to run without a validated polygon boundary."""
    grid_obs = [{"lat": 26.84, "lng": 80.94, "rainfall_mm": 15.0}]
    with pytest.raises(SpatialAggregationError):
        SpatialAggregator.aggregate_gridded_precipitation("district-lucknow", grid_obs)


# ---------------------------------------------------------------------------
# 5. SPI-3 Calculation & Insufficient Data Handling
# ---------------------------------------------------------------------------
def test_spi_3_calculation_with_historical_series():
    """Standardized Precipitation Index (SPI-3) computation with continuous monthly totals."""
    # Generate 36 months of realistic rainfall series
    np.random.seed(42)
    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
    # Monsoon peak in Jul-Sep
    rains = [15.0 if d.month not in [6, 7, 8, 9] else 250.0 + np.random.uniform(-50, 50) for d in dates]
    series = pd.Series(rains, index=dates)

    spi_val, category, metadata = SPIEngine.calculate_spi_3(series)
    assert isinstance(spi_val, float)
    assert category in [c[1] for c in SPIEngine.CATEGORIES]
    assert "gamma_shape_alpha" in metadata
    assert "gamma_scale_beta" in metadata


def test_spi_3_insufficient_data_refusal():
    """SPI-3 calculation must refuse to calculate when series is too short (< 3 months)."""
    short_dates = pd.date_range(start="2026-08-01", periods=2, freq="MS")
    short_series = pd.Series([10.0, 15.0], index=short_dates)
    spi_val, category, metadata = SPIEngine.calculate_spi_3(short_series)
    assert category == "Insufficient Data"
    assert "error" in metadata


# ---------------------------------------------------------------------------
# 6. Official Government Alerts
# ---------------------------------------------------------------------------
def test_official_alerts_pipeline():
    """Verify retrieval of authoritative alerts and handling of unauthenticated portal limits."""
    # Gorakhpur alert
    gkp_alert = OfficialAlertsPipeline.get_district_official_alert("district-gorakhpur")
    assert gkp_alert["region_id"] == "district-gorakhpur"
    assert gkp_alert["alert_level"] == "Yellow"
    assert "IMD" in gkp_alert["authority"]
    assert gkp_alert["status"] == "manually_verified"
    assert "limitations" in gkp_alert

    # Mahoba alert
    mhb_alert = OfficialAlertsPipeline.get_district_official_alert("district-mahoba")
    assert mhb_alert["region_id"] == "district-mahoba"
    assert mhb_alert["alert_level"] == "Orange"
    assert "UPSDMA" in mhb_alert["authority"]
    assert mhb_alert["status"] == "manually_verified"

    # Candidate district returns data_pending
    lkn_alert = OfficialAlertsPipeline.get_district_official_alert("district-lucknow")
    assert lkn_alert["status"] == "data_pending"
    assert lkn_alert["alert_level"] == "None"


# ---------------------------------------------------------------------------
# 7. Candidate District Isolation & Zero Data Bleed
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cand_id", ["lucknow", "patna", "gaya", "varanasi"])
def test_candidate_districts_dashboard_isolation(cand_id):
    """Candidate districts must display DATA_PENDING status with zero pilot data bleed."""
    resp = client.get(f"/api/v1/dashboard?location={cand_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "DATA_PENDING"
    assert data["data_freshness_status"] == "pending_onboarding"
    assert "pending onboarding" in data["disclaimer"].lower()

    # All metrics must be null (DATA_PENDING)
    for card in data["metric_cards"]:
        assert card["value"] is None
        assert card["is_data_available"] is False
        assert card["hazard_type"] == "pending"


def test_candidate_district_direct_risk_endpoint_rejection():
    """Requesting verified risk assessment for unconfigured candidate district halts with 400/404."""
    resp = client.get("/api/v1/risk/flood?location=lucknow&mode=verified")
    assert resp.status_code in [400, 404]

    resp = client.get("/api/v1/risk/drought?location=patna&mode=verified")
    assert resp.status_code in [400, 404]


# ---------------------------------------------------------------------------
# 8. Multi-Mode API Endpoints Verification
# ---------------------------------------------------------------------------
def test_dashboard_api_verified_mode():
    """Dashboard endpoint responds with CACHED_VERIFIED when mode='verified'."""
    resp = client.get("/api/v1/dashboard?location=gorakhpur&mode=verified")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "CACHED_VERIFIED"
    assert data["is_demo_data"] is False


def test_flood_risk_endpoint_verified_mode():
    """Flood risk endpoint evaluates verified Gorakhpur CHIRPS observations."""
    resp = client.get("/api/v1/risk/flood?location=gorakhpur&mode=verified")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "CACHED_VERIFIED"
    assert data["is_demo_data"] is False
    assert data["location"]["name"] == "Gorakhpur"
    # Verify indicators present
    indicator_ids = [ind["indicator_id"] for ind in data["indicators"]]
    assert "flood_precip_7d_accum" in indicator_ids
    assert "flood_precip_30d_accum" in indicator_ids
    assert "flood_terrain_vulnerability" in indicator_ids


def test_drought_risk_endpoint_verified_mode():
    """Drought risk endpoint evaluates verified Mahoba CHIRPS observations."""
    resp = client.get("/api/v1/risk/drought?location=mahoba&mode=verified")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "CACHED_VERIFIED"
    assert data["is_demo_data"] is False
    assert data["location"]["name"] == "Mahoba"
    indicator_ids = [ind["indicator_id"] for ind in data["indicators"]]
    assert "drought_precip_90d_accum" in indicator_ids
    assert "drought_precip_90d_anomaly" in indicator_ids
    assert "drought_seasonal_deficit" in indicator_ids
    assert "drought_spi_3" in indicator_ids


def test_rainfall_trends_endpoint_verified_mode():
    """Rainfall trends endpoint loads verified series."""
    resp = client.get("/api/v1/trends/rainfall?location=gorakhpur&range=30&mode=verified")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_mode"] == "CACHED_VERIFIED"
    assert data["is_demo_data"] is False
    assert len(data["series"]) == 30


# ---------------------------------------------------------------------------
# 9. Gemma 4 Grounded Assistant Engine
# ---------------------------------------------------------------------------
def test_grounded_assistant_verified_citations():
    """Assistant generates grounded explanations citing verified data and disclaimers."""
    payload = {
        "query": "What is the current flood risk in Gorakhpur and how does rainfall relate to river stage?",
        "location": "gorakhpur"
    }
    resp = client.post("/api/v1/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["citations"]) >= 2
    assert "Gorakhpur" in data["answer"] or "Rapti" in data["answer"]
    # Key scientific caveat: rainfall != Rapti gauge depth
    all_text = (data["answer"] + " " + " ".join(data["limitations"])).lower()
    assert "rapti" in all_text or "river" in all_text
