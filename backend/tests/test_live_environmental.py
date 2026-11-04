"""
JalRakshak AI — Phase 3A Live Environmental Data Test Suite
Tests:
1. OpenMeteoForecastAdapter (metadata, coordinate resolution, hourly validation, bounds, aggregation).
2. EnvironmentalCacheService (caching, TTL expiration, stale fallback, concurrency deduplication).
3. API Endpoints (GET /environmental/live, GET /status, POST /refresh, feature flag toggling).
4. Engine Integration (FloodRiskEngine, DroughtRiskEngine, Trends in mode='live').
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pandas as pd

from app.main import app
from app.core import config
from app.pipeline.adapters.open_meteo_forecast import (
    OpenMeteoForecastAdapter,
    DISTRICT_COORDINATES,
)
from app.pipeline.adapters.base import (
    SourceConnectionStatus,
    AdapterConnectionError,
    AdapterPayloadError,
)
from app.services.environmental_cache import (
    EnvironmentalCacheService,
    _memory_cache,
    _last_refresh_timestamps,
)
from app.pipeline.ingestion import DataIngestionService
from app.engine.flood_engine import FloodRiskEngine
from app.engine.drought_engine import DroughtRiskEngine
from app.schemas.environmental import (
    EnvironmentalLiveResponse,
    EnvironmentalSystemStatusResponse,
    EnvironmentalRefreshResponse,
)

client = TestClient(app)


# Sample valid Open-Meteo forecast JSON payload
def generate_sample_open_meteo_payload(lat=26.7606, lng=83.3732, base_dt=None):
    if base_dt is None:
        base_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    # Generate 48 hours (24 past, 24 future)
    start_dt = base_dt - timedelta(hours=24)
    times = []
    precip = []
    temp = []
    humidity = []
    wind = []
    et0 = []

    for h in range(48):
        cur = start_dt + timedelta(hours=h)
        times.append(cur.strftime("%Y-%m-%dT%H:00"))
        # h == 10 has 0.0 mm (genuine zero), h == 11 has 5.2 mm, h == 12 has None
        if h == 10:
            precip.append(0.0)
        elif h == 11:
            precip.append(5.2)
        elif h == 12:
            precip.append(None)
        else:
            precip.append(1.0)
        temp.append(28.5)
        humidity.append(65.0)
        wind.append(12.0)
        et0.append(0.3)

    return {
        "latitude": lat,
        "longitude": lng,
        "generationtime_ms": 0.42,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": 84.0,
        "hourly_units": {
            "time": "iso8601",
            "precipitation": "mm",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
            "et0_fao_evapotranspiration": "mm",
        },
        "hourly": {
            "time": times,
            "precipitation": precip,
            "temperature_2m": temp,
            "relative_humidity_2m": humidity,
            "wind_speed_10m": wind,
            "et0_fao_evapotranspiration": et0,
        },
    }


# =============================================================================
# 1. OpenMeteoForecastAdapter Unit Tests
# =============================================================================

def test_adapter_metadata():
    """Verify source metadata and scientific invariants."""
    meta = OpenMeteoForecastAdapter.get_metadata()
    assert meta.source_id == "open_meteo_forecast"
    assert "Open-Meteo" in meta.name
    assert meta.dataset_type.value == "forecast"
    assert "representative point estimate" in meta.spatial_resolution
    assert "representative-point estimate" in meta.limitations


def test_district_centroid_resolution():
    """Verify centroid coordinate resolution for pilot and candidate districts."""
    # Pilot: Gorakhpur
    g_coords = OpenMeteoForecastAdapter.resolve_district_coordinates("district-gorakhpur")
    assert round(g_coords["lat"], 2) == 26.76
    assert round(g_coords["lng"], 2) == 83.37
    assert g_coords["name"] == "Gorakhpur"

    # Pilot: Mahoba
    m_coords = OpenMeteoForecastAdapter.resolve_district_coordinates("mahoba")
    assert round(m_coords["lat"], 2) == 25.30
    assert round(m_coords["lng"], 2) == 79.86

    # Candidate: Patna
    p_coords = OpenMeteoForecastAdapter.resolve_district_coordinates("patna")
    assert p_coords["lat"] > 25.0
    assert p_coords["lng"] > 85.0


def test_hourly_validation_and_zero_vs_missing():
    """Verify zero vs null semantics and forecast vs observation distinction."""
    ref_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    payload = generate_sample_open_meteo_payload(base_dt=ref_time)
    coords = {"lat": 26.76, "lng": 83.37, "name": "Gorakhpur"}

    parsed = OpenMeteoForecastAdapter.validate_and_parse_hourly(
        payload=payload,
        district_id="district-gorakhpur",
        coords=coords,
        retrieval_time=ref_time,
    )

    records = parsed["records"]
    assert len(records) == 48

    # Check genuine zero is preserved as 0.0
    r_zero = records[10]
    assert r_zero["precipitation_mm"] == 0.0
    assert r_zero["precipitation_mm"] is not None
    assert r_zero["quality_status"] == "historical_model_estimate"

    # Check missing is preserved as None (never coerced to 0)
    r_missing = records[12]
    assert r_missing["precipitation_mm"] is None
    assert r_missing["quality_status"] == "missing"

    # Check temporal classification relative to UTC hour
    # Record at h=0 is 24 hours in past -> is_forecast == False, historical_model_estimate
    assert records[0]["is_forecast"] is False
    assert records[0]["quality_status"] == "historical_model_estimate"
    # Record at h=24 is the current hour -> is_forecast == False, live_model_estimate
    assert records[24]["is_forecast"] is False
    assert records[24]["quality_status"] == "live_model_estimate"
    # Record at h=30 is in future -> is_forecast == True, forecast
    assert records[30]["is_forecast"] is True
    assert records[30]["quality_status"] == "forecast"

    # Verify no record carries the legacy/misleading observed_estimate
    for r in records:
        assert r["quality_status"] != "observed_estimate"


def test_hourly_bounds_validation():
    """Verify out-of-bounds meteorological values are marked None or raise validation error."""
    ref_time = datetime.now(timezone.utc)
    coords = {"lat": 26.76, "lng": 83.37}

    # Negative precipitation must raise AdapterPayloadError
    payload_neg = {
        "latitude": 26.76,
        "longitude": 83.37,
        "hourly": {
            "time": ["2026-10-28T12:00"],
            "precipitation": [-5.0],
            "temperature_2m": [25.0],
            "relative_humidity_2m": [60.0],
            "wind_speed_10m": [10.0],
            "et0_fao_evapotranspiration": [0.5],
        }
    }
    with pytest.raises(AdapterPayloadError, match="Negative precipitation"):
        OpenMeteoForecastAdapter.validate_and_parse_hourly(payload_neg, "gorakhpur", coords, ref_time)

    # Extreme bounds filtering
    payload_bounds = {
        "latitude": 26.76,
        "longitude": 83.37,
        "hourly": {
            "time": ["2026-10-28T12:00"],
            "precipitation": [550.0],       # Clamped to 500
            "temperature_2m": [85.0],       # > 60°C -> None
            "relative_humidity_2m": [120.0], # > 100% -> clamped to 100
            "wind_speed_10m": [-10.0],      # < 0 -> None
            "et0_fao_evapotranspiration": [99.0], # > 50 mm/hr -> None
        }
    }
    parsed = OpenMeteoForecastAdapter.validate_and_parse_hourly(payload_bounds, "gorakhpur", coords, ref_time)
    rec = parsed["records"][0]
    assert rec["precipitation_mm"] == 500.0
    assert rec["temperature_2m_c"] is None
    assert rec["relative_humidity_pct"] == 100.0
    assert rec["wind_speed_10m_kmh"] is None
    assert rec["et0_evapotranspiration_mm"] is None


def test_hourly_to_daily_aggregation():
    """Verify daily aggregation and coverage threshold."""
    records = []
    # Day 1: 24 valid hours, 1.0 mm each -> 24.0 mm
    for h in range(24):
        records.append({
            "timestamp": f"2026-10-28T{h:02d}:00",
            "dt": datetime(2026, 10, 28, h, 0, tzinfo=timezone.utc),
            "precipitation_mm": 1.0,
            "is_forecast": False,
        })
    # Day 2: 15 missing hours (< 20 threshold) -> daily sum must be None
    for h in range(24):
        records.append({
            "timestamp": f"2026-10-29T{h:02d}:00",
            "dt": datetime(2026, 10, 29, h, 0, tzinfo=timezone.utc),
            "precipitation_mm": 1.0 if h < 9 else None,
            "is_forecast": True,
        })

    daily = OpenMeteoForecastAdapter.aggregate_hourly_to_daily(records)
    assert len(daily) == 2

    # Day 1: Pure historical day
    assert daily[0]["date"] == "2026-10-28"
    assert daily[0]["rainfall_mm"] == 24.0
    assert daily[0]["hours_recorded"] == 24
    assert daily[0]["is_forecast"] is False
    assert daily[0]["quality_status"] == "historical_model_estimate"

    # Day 2: Missing data threshold enforced
    assert daily[1]["date"] == "2026-10-29"
    assert daily[1]["rainfall_mm"] is None
    assert daily[1]["hours_missing"] == 15
    assert daily[1]["is_forecast"] is True
    assert daily[1]["quality_status"] == "missing"


@pytest.mark.anyio
async def test_adapter_fetch_forecast_mock():
    """Verify bounded HTTP fetch with mocked response."""
    mock_payload = generate_sample_open_meteo_payload()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        data = await OpenMeteoForecastAdapter.fetch_forecast_raw(26.76, 83.37)
        assert data["latitude"] == 26.7606
        assert "hourly" in data


# =============================================================================
# 2. EnvironmentalCacheService Unit & Resilience Tests
# =============================================================================

@pytest.fixture(autouse=True)
def clean_cache():
    """Cleans in-memory and disk cache between tests."""
    EnvironmentalCacheService.clear_cache()
    _last_refresh_timestamps.clear()
    yield
    EnvironmentalCacheService.clear_cache()
    _last_refresh_timestamps.clear()


@pytest.mark.anyio
async def test_cache_hit_and_freshness():
    """Verify cache returns fresh hit within 3-hour TTL without re-fetching."""
    mock_payload = generate_sample_open_meteo_payload()
    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_payload

        # First retrieval: Miss, calls provider
        res1 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res1.data_mode == "LIVE_MODEL"
        assert res1.freshness.is_cached is False
        assert mock_fetch.call_count == 1

        # Second retrieval: Hit, does not call provider
        res2 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res2.data_mode == "LIVE_MODEL"
        assert res2.freshness.is_cached is True
        assert mock_fetch.call_count == 1


@pytest.mark.anyio
async def test_stale_cache_fallback_on_provider_error():
    """Verify stale cache (between 3h and 24h) is returned with DATA_STALE on provider outage."""
    now_utc = datetime.now(timezone.utc)
    four_hours_ago = (now_utc - timedelta(hours=4)).isoformat()

    # Pre-seed cache with 4-hour-old data
    cached_entry = {
        "district_id": "district-gorakhpur",
        "retrieval_timestamp": four_hours_ago,
        "expires_at": (now_utc - timedelta(hours=1)).isoformat(),
        "coordinates": {"lat": 26.7606, "lng": 83.3732},
        "hourly_records": [
            {
                "timestamp": four_hours_ago,
                "precipitation_mm": 2.5,
                "temperature_2m_c": 30.0,
                "relative_humidity_pct": 70.0,
                "wind_speed_10m_kmh": 10.0,
                "et0_evapotranspiration_mm": 0.2,
                "is_forecast": False,
                "quality_status": "observed_estimate",
            }
        ],
        "daily_records": [
            {
                "date": four_hours_ago[:10],
                "rainfall_mm": 2.5,
                "is_forecast": False,
                "hours_recorded": 24,
                "hours_missing": 0,
                "quality_status": "observed_estimate",
            }
        ],
    }
    _memory_cache["district-gorakhpur"] = cached_entry

    # Force refresh with provider failure
    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", side_effect=Exception("503 Service Unavailable")):
        res = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur", force_refresh=True)
        assert res.data_mode == "DATA_STALE"
        assert res.freshness.is_stale is True
        assert res.current_conditions is not None
        assert res.current_conditions.precipitation_rate_mm_hr == 2.5


@pytest.mark.anyio
async def test_data_pending_when_no_cache_and_provider_down():
    """Verify DATA_PENDING is returned honestly when no cache exists and provider is unreachable."""
    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", side_effect=Exception("Connection Timeout")):
        res = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res.data_mode == "DATA_PENDING"
        assert res.freshness.is_stale is True
        assert res.current_conditions is None
        assert len(res.hourly_series) == 0


@pytest.mark.anyio
async def test_concurrency_deduplication():
    """Verify concurrent requests for the same district make exactly one HTTP call."""
    mock_payload = generate_sample_open_meteo_payload()
    call_count = 0

    async def delayed_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return mock_payload

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", side_effect=delayed_fetch):
        # Fire 5 concurrent requests
        results = await asyncio.gather(*[
            EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
            for _ in range(5)
        ])
        assert call_count == 1
        for r in results:
            assert r.data_mode == "LIVE_MODEL"


# =============================================================================
# 3. API Endpoints Integration Tests
# =============================================================================

def test_get_environmental_status():
    """Verify GET /api/v1/environmental/status contract."""
    response = client.get("/api/v1/environmental/status")
    assert response.status_code == 200
    data = response.json()
    assert "feature_flag_enabled" in data
    assert data["provider"] == "Open-Meteo Weather Forecast (NWP)"
    assert data["cache_ttl_hours"] == 3.0
    assert data["stale_threshold_hours"] == 24.0


def test_get_environmental_live_when_feature_flag_disabled():
    """Verify GET /api/v1/environmental/live returns honest status when flag is disabled."""
    with patch("app.core.config.LIVE_DATA_ENABLED", False):
        with patch("app.api.environmental.LIVE_DATA_ENABLED", False):
            response = client.get("/api/v1/environmental/live?location=gorakhpur")
            assert response.status_code == 200
            data = response.json()
            assert data["district_id"] == "district-gorakhpur"
            assert data["data_mode"] == "DATA_PENDING"
            assert "disabled" in data["provider_status"]["error"].lower()


def test_post_environmental_refresh_when_disabled():
    """Verify POST /api/v1/environmental/refresh reports disabled status."""
    with patch("app.core.config.LIVE_DATA_ENABLED", False):
        with patch("app.api.environmental.LIVE_DATA_ENABLED", False):
            response = client.post("/api/v1/environmental/refresh?location=gorakhpur")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["status"] == "disabled"


def test_get_environmental_live_when_enabled():
    """Verify GET /api/v1/environmental/live retrieves live model when flag is enabled."""
    mock_payload = generate_sample_open_meteo_payload()
    with patch("app.core.config.LIVE_DATA_ENABLED", True):
        with patch("app.api.environmental.LIVE_DATA_ENABLED", True):
            with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = mock_payload
                response = client.get("/api/v1/environmental/live?location=gorakhpur")
                assert response.status_code == 200
                data = response.json()
                assert data["district_id"] == "district-gorakhpur"
                assert data["data_mode"] == "LIVE_MODEL"
                assert data["spatial_representation"] == "representative_point_estimate"
                assert len(data["hourly_series"]) == 48


# =============================================================================
# 4. Engine & Ingestion Pipeline Integration Tests
# =============================================================================

def test_ingestion_service_mode_live():
    """Verify DataIngestionService loads daily precipitation from live cache when mode='live'."""
    ingestion = DataIngestionService()

    # When no cache exists
    df_empty = ingestion.load_daily_rainfall("gorakhpur", mode="live")
    assert isinstance(df_empty, pd.DataFrame)
    assert df_empty.empty

    # When cache exists
    _memory_cache["district-gorakhpur"] = {
        "district_id": "district-gorakhpur",
        "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        "daily_records": [
            {"date": "2026-10-27", "rainfall_mm": 12.4},
            {"date": "2026-10-28", "rainfall_mm": 5.0},
        ]
    }
    df_live = ingestion.load_daily_rainfall("gorakhpur", mode="live")
    assert len(df_live) == 2
    assert float(df_live.iloc[0]["rainfall_mm"]) == 12.4


def test_flood_engine_mode_live():
    """Verify FloodRiskEngine produces LIVE_MODEL assessment with Open-Meteo attribution and model_derived category."""
    ingestion = DataIngestionService()
    g_info = ingestion.get_district_info("gorakhpur")

    daily_df = pd.DataFrame([
        {"date": pd.to_datetime("2026-10-27"), "rainfall_mm": 20.0},
        {"date": pd.to_datetime("2026-10-28"), "rainfall_mm": 30.0},
    ])

    eval_result = FloodRiskEngine.evaluate(g_info, daily_df, reference_date="2026-10-28", mode="live")
    assert eval_result.data_mode == "LIVE_MODEL"
    assert eval_result.is_demo_data is False
    source_ids = [s.source_id for s in eval_result.sources]
    assert "open_meteo_forecast" in source_ids
    assert "nasa_gpm_imerg" not in source_ids
    assert any("Open-Meteo" in note for note in eval_result.scientific_notes)

    # Check indicator provenance category & quality status
    ind_map = {ind.indicator_id: ind for ind in eval_result.indicators}
    assert ind_map["flood_precip_7d_accum"].category == "model_derived"
    assert ind_map["flood_precip_7d_accum"].quality_status == "provisional"
    assert "Open-Meteo" in ind_map["flood_precip_7d_accum"].dataset_version
    assert ind_map["flood_precip_30d_accum"].category == "model_derived"
    assert ind_map["flood_precip_30d_accum"].quality_status == "provisional"


def test_drought_engine_mode_live():
    """Verify DroughtRiskEngine produces LIVE_MODEL assessment with Open-Meteo attribution and model_derived category."""
    ingestion = DataIngestionService()
    m_info = ingestion.get_district_info("mahoba")

    daily_df = pd.DataFrame([
        {"date": pd.to_datetime("2026-10-27"), "rainfall_mm": 0.0},
        {"date": pd.to_datetime("2026-10-28"), "rainfall_mm": 0.0},
    ])

    eval_result = DroughtRiskEngine.evaluate(m_info, daily_df, reference_date="2026-10-28", mode="live")
    assert eval_result.data_mode == "LIVE_MODEL"
    assert eval_result.is_demo_data is False
    source_ids = [s.source_id for s in eval_result.sources]
    assert "open_meteo_forecast" in source_ids
    assert "nasa_gpm_imerg" not in source_ids

    # Check indicator provenance category & quality status
    ind_map = {ind.indicator_id: ind for ind in eval_result.indicators}
    assert ind_map["drought_precip_90d_accum"].category == "model_derived"
    assert ind_map["drought_precip_90d_accum"].quality_status == "missing"
    assert ind_map["drought_precip_90d_accum"].value is None
    assert ind_map["drought_precip_90d_anomaly"].value is None
    assert ind_map["drought_precip_90d_anomaly"].quality_status == "missing"
    assert "Open-Meteo" in ind_map["drought_precip_90d_accum"].dataset_version

    # If full 90-day series is available in live mode, quality_status is provisional
    dates_90d = pd.date_range(end="2026-10-28", periods=90, freq="D")
    df_90d = pd.DataFrame({"date": dates_90d, "rainfall_mm": [1.0] * 90})
    eval_90d = DroughtRiskEngine.evaluate(m_info, df_90d, reference_date="2026-10-28", mode="live")
    ind_map_90d = {ind.indicator_id: ind for ind in eval_90d.indicators}
    assert ind_map_90d["drought_precip_90d_accum"].category == "model_derived"
    assert ind_map_90d["drought_precip_90d_accum"].quality_status == "provisional"
    assert ind_map_90d["drought_precip_90d_accum"].value == 90.0
