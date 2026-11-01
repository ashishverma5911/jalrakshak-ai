"""
Comprehensive Test Suite for Scientific Source Adapters (Stage 2)
Verifies:
1. ScientificSourceAdapter base primitives (rate-to-accumulation, bounds validation, zero vs missing).
2. CHIRPSAdapter (verification, metadata, district isolation, payload checks).
3. GPMIMERGAdapter (run types, authentication-required status, rate conversion, isolation).
4. OpenMeteoAdapter (reanalysis classification, payload validation, error/timeout resilience).
5. SRTMAdapter (static reference invariant, elevation profiles, candidate district rejection).
6. ScientificSourceRegistry (discovery, lookup, parallel health auditing).
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pandas as pd
import httpx

from app.pipeline.adapters import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterResponse,
    ObservationRecord,
    SourceConnectionStatus,
    DatasetType,
    QualityStatus,
    PrecipitationUnit,
    AdapterError,
    AdapterPayloadError,
    AdapterUnitError,
    DistrictIsolationError,
    CHIRPSAdapter,
    GPMIMERGAdapter,
    OpenMeteoAdapter,
    SRTMAdapter,
    ScientificSourceRegistry,
)


# =============================================================================
# 1. Base Adapter Primitives & Scientific Temporal Rules Tests
# =============================================================================

def test_base_adapter_rate_to_accumulation_conversion():
    """Verify rate (mm/hr) to accumulation (mm) calculation and physical constraints."""
    # 2.0 mm/hr over 30 minutes (0.5 hr) -> exactly 1.0 mm
    assert ScientificSourceAdapter.convert_half_hourly_rate_to_accumulation(2.0) == 1.0
    assert ScientificSourceAdapter.convert_rate_to_accumulation(2.0, duration_hours=0.5) == 1.0

    # 2.0 mm/hr over 24 hours -> exactly 48.0 mm (only when representing full 24h)
    assert ScientificSourceAdapter.convert_daily_mean_rate_to_accumulation(2.0) == 48.0
    assert ScientificSourceAdapter.convert_rate_to_accumulation(2.0, duration_hours=24.0) == 48.0

    # 0.0 mm/hr -> 0.0 mm
    assert ScientificSourceAdapter.convert_rate_to_accumulation(0.0, 24.0) == 0.0
    assert ScientificSourceAdapter.convert_half_hourly_rate_to_accumulation(0.0) == 0.0

    # Negative rate must raise AdapterUnitError
    with pytest.raises(AdapterUnitError, match="negative precipitation rate"):
        ScientificSourceAdapter.convert_rate_to_accumulation(-1.0, 24.0)

    # Non-positive duration must raise AdapterUnitError
    with pytest.raises(AdapterUnitError, match="duration must be strictly positive"):
        ScientificSourceAdapter.convert_rate_to_accumulation(5.0, 0.0)

    with pytest.raises(AdapterUnitError, match="duration must be strictly positive"):
        ScientificSourceAdapter.convert_rate_to_accumulation(5.0, -1.0)

    # Missing duration must raise AdapterUnitError
    with pytest.raises(AdapterUnitError, match="duration_hours is required"):
        ScientificSourceAdapter.convert_rate_to_accumulation(5.0, None)  # type: ignore


def test_numerical_already_accumulated_depth_remains_unchanged():
    """Verify that an already accumulated value of 5 mm remains 5 mm (no duration multiplication)."""
    val, status, flag = ScientificSourceAdapter.validate_rainfall_value(5.0)
    assert val == 5.0
    assert status == QualityStatus.OBSERVED
    assert flag is None


def test_numerical_missing_values_remain_missing():
    """Verify missing values remain strictly None with MISSING status (never coerced to 0.0)."""
    for missing_input in [None, float("nan")]:
        val, status, flag = ScientificSourceAdapter.validate_rainfall_value(missing_input)
        assert val is None
        assert status == QualityStatus.MISSING
        assert flag is None


def test_numerical_legitimate_zero_remains_zero():
    """Verify legitimate 0 mm rainfall is preserved as 0.0 with ZERO_PRECIPITATION status."""
    val, status, flag = ScientificSourceAdapter.validate_rainfall_value(0.0)
    assert val == 0.0
    assert status == QualityStatus.ZERO_PRECIPITATION
    assert flag is None


def test_numerical_half_hourly_series_accumulation_no_double_counting():
    """
    Verify integration of 48 half-hourly granules (each 2.0 mm/hr) over a 24-hour day.
    Each half-hour: 2.0 mm/hr * 0.5 hr = 1.0 mm.
    Sum of 48 half-hours = exactly 48.0 mm.
    Guarantees no double accumulation (e.g. multiplying by 24 twice -> 1152 mm).
    """
    half_hourly_rates = [2.0] * 48  # 48 intervals of 30 minutes in a full day
    total_day_mm = ScientificSourceAdapter.accumulate_half_hourly_series(half_hourly_rates)
    assert total_day_mm == 48.0


def test_base_adapter_validate_rainfall_values():
    """Verify physical bounds validation: negative rejection, legitimate zero, and extreme flag."""
    # Legitimate zero
    val, status, flag = ScientificSourceAdapter.validate_rainfall_value(0.0)
    assert val == 0.0
    assert status == QualityStatus.ZERO_PRECIPITATION
    assert flag is None

    # Normal observed rainfall
    val, status, flag = ScientificSourceAdapter.validate_rainfall_value(25.4)
    assert val == 25.4
    assert status == QualityStatus.OBSERVED
    assert flag is None

    # Provisional extreme (> 500 mm/day)
    val, status, flag = ScientificSourceAdapter.validate_rainfall_value(540.2)
    assert val == 540.2
    assert status == QualityStatus.PROVISIONAL_EXTREME
    assert "exceeds 500 mm" in flag

    # Negative rainfall must be rejected
    with pytest.raises(AdapterPayloadError, match="Negative rainfall"):
        ScientificSourceAdapter.validate_rainfall_value(-0.5)

    # Non-numeric string must be rejected
    with pytest.raises(AdapterPayloadError, match="Invalid non-numeric"):
        ScientificSourceAdapter.validate_rainfall_value("corrupted_text")


# =============================================================================
# 2. CHIRPSAdapter Tests
# =============================================================================

def test_chirps_adapter_metadata():
    """Verify CHIRPS metadata specifications."""
    meta = CHIRPSAdapter.get_metadata()
    assert meta.source_id == "chirps_daily"
    assert meta.dataset_type == DatasetType.SATELLITE_DERIVED
    assert meta.default_units == "mm"
    assert meta.is_rate_based is False
    assert meta.auth_required is False
    assert "0.05°" in meta.spatial_resolution


@pytest.mark.anyio
async def test_chirps_adapter_check_connection():
    """Verify CHIRPS reachability and local archive inspection."""
    res = await CHIRPSAdapter.check_connection(timeout_seconds=2.0)
    assert res["source_id"] == "chirps_daily"
    assert "local_archive_ready" in res
    assert "districts_cached" in res
    assert "district-gorakhpur" in res["districts_cached"]
    assert "district-mahoba" in res["districts_cached"]


@pytest.mark.anyio
async def test_chirps_adapter_fetch_series_gorakhpur():
    """Verify fetching genuine verified CHIRPS series for Gorakhpur."""
    resp = await CHIRPSAdapter.fetch_series(
        region_id="district-gorakhpur",
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 15)
    )
    assert resp.status == SourceConnectionStatus.CONNECTED
    assert resp.region_id == "district-gorakhpur"
    assert resp.units == "mm"
    assert resp.records_count == 15
    assert resp.valid_count == 15
    assert len(resp.observations) == 15

    # Check first record structure
    first = resp.observations[0]
    assert isinstance(first.date, date)
    assert first.rainfall_mm is not None
    assert first.quality_status in [QualityStatus.OBSERVED, QualityStatus.ZERO_PRECIPITATION]


@pytest.mark.anyio
async def test_chirps_adapter_district_isolation_rejection():
    """Verify candidate districts cannot inherit or access uncalibrated CHIRPS series."""
    with pytest.raises(DistrictIsolationError, match="zero data bleed"):
        await CHIRPSAdapter.fetch_series(region_id="district-lucknow")


def test_chirps_adapter_payload_validation():
    """Verify CHIRPS DataFrame validation logic."""
    valid_df = pd.DataFrame({
        "date": ["2024-08-01", "2024-08-02"],
        "rainfall_mm": [12.0, 0.0]
    })
    report = CHIRPSAdapter.validate_payload(valid_df)
    assert report["total_rows"] == 2
    assert report["mean_rainfall_mm"] == 6.0

    # Negative values rejected
    invalid_df = pd.DataFrame({
        "date": ["2024-08-01"],
        "rainfall_mm": [-5.0]
    })
    with pytest.raises(AdapterPayloadError, match="negative precipitation"):
        CHIRPSAdapter.validate_payload(invalid_df)

    # Missing column rejected
    missing_df = pd.DataFrame({"date": ["2024-08-01"]})
    with pytest.raises(AdapterPayloadError, match="missing required column"):
        CHIRPSAdapter.validate_payload(missing_df)


# =============================================================================
# 3. GPMIMERGAdapter Tests
# =============================================================================

def test_gpm_adapter_metadata_and_runs():
    """Verify GPM metadata and distinction between Early, Late, and Final runs."""
    meta = GPMIMERGAdapter.get_metadata()
    assert meta.source_id == "nasa_gpm_imerg"
    assert meta.auth_required is True
    assert "0.1°" in meta.spatial_resolution

    early = GPMIMERGAdapter.get_run_metadata("Early")
    late = GPMIMERGAdapter.get_run_metadata("Late")
    final = GPMIMERGAdapter.get_run_metadata("Final")

    assert early["product_id"] == "3B-DAY-E"
    assert early["latency_hours"] == 4

    assert late["product_id"] == "3B-DAY-L"
    assert late["latency_hours"] == 14

    assert final["product_id"] == "3B-DAY-F"
    assert final["latency_months"] == 3.5


@pytest.mark.anyio
async def test_gpm_adapter_authentication_required_when_unconfigured():
    """Verify GPM reports AUTHENTICATION_REQUIRED honestly when credentials are not in environment."""
    with patch("app.pipeline.adapters.gpm_imerg.EARTHDATA_USERNAME", ""), \
         patch("app.pipeline.adapters.gpm_imerg.EARTHDATA_PASSWORD", ""), \
         patch("app.pipeline.adapters.gpm_imerg.EARTHDATA_BEARER_TOKEN", ""):
        res = await GPMIMERGAdapter.check_connection()
        assert res["status"] == SourceConnectionStatus.AUTHENTICATION_REQUIRED
        assert res["auth_configured"] is False
        assert "NASA Earthdata URS credentials" in res["message"]


@pytest.mark.anyio
async def test_gpm_adapter_fetch_series_half_hourly_rate_handling():
    """Verify that a half-hourly GPM rate (2.0 mm/hr over 30 min) converts to exactly 1.0 mm."""
    clean_id = "district-gorakhpur"
    mock_df = pd.DataFrame({
        "date": ["2024-08-01"],
        "rainfall_mm": [2.0],
        "unit": ["mm/hr"],
        "interval_minutes": [30],
    })
    with patch("pandas.read_csv", return_value=mock_df), \
         patch("pathlib.Path.exists", return_value=True):
        resp = await GPMIMERGAdapter.fetch_series(clean_id, run_type="Late")
        assert resp.status == SourceConnectionStatus.CONNECTED
        assert len(resp.observations) == 1
        # 2.0 mm/hr * 0.5 hr = 1.0 mm
        assert resp.observations[0].rainfall_mm == 1.0
        assert resp.observations[0].raw_value == 2.0
        assert resp.observations[0].raw_units == "mm/hr"
        assert resp.observations[0].interval_hours == 0.5
        assert "converted_rate_0.5h" in resp.observations[0].temporal_semantics


@pytest.mark.anyio
async def test_gpm_adapter_fetch_series_daily_mean_rate_handling():
    """Verify that a genuine 24-hour daily mean rate (2.0 mm/hr over 24 hours) converts to 48.0 mm."""
    clean_id = "district-gorakhpur"
    mock_df = pd.DataFrame({
        "date": ["2024-08-01"],
        "rainfall_mm": [2.0],
        "unit": ["mm/hr"],
        "duration_hours": [24.0],
    })
    with patch("pandas.read_csv", return_value=mock_df), \
         patch("pathlib.Path.exists", return_value=True):
        resp = await GPMIMERGAdapter.fetch_series(clean_id, run_type="Late")
        assert resp.status == SourceConnectionStatus.CONNECTED
        assert len(resp.observations) == 1
        # 2.0 mm/hr * 24 hr = 48.0 mm
        assert resp.observations[0].rainfall_mm == 48.0
        assert resp.observations[0].raw_value == 2.0
        assert resp.observations[0].raw_units == "mm/hr"
        assert resp.observations[0].interval_hours == 24.0


@pytest.mark.anyio
async def test_gpm_adapter_fetch_series_already_accumulated():
    """Verify that already accumulated daily values (unit: mm) remain unchanged (5 mm remains 5 mm)."""
    clean_id = "district-gorakhpur"
    mock_df = pd.DataFrame({
        "date": ["2024-08-01"],
        "rainfall_mm": [5.0],
        "unit": ["mm"],
    })
    with patch("pandas.read_csv", return_value=mock_df), \
         patch("pathlib.Path.exists", return_value=True):
        resp = await GPMIMERGAdapter.fetch_series(clean_id, run_type="Late")
        assert resp.status == SourceConnectionStatus.CONNECTED
        assert len(resp.observations) == 1
        # Already accumulated: 5.0 mm remains 5.0 mm, no multiplication!
        assert resp.observations[0].rainfall_mm == 5.0
        assert resp.observations[0].raw_value == 5.0
        assert resp.observations[0].raw_units == "mm"
        assert resp.observations[0].temporal_semantics == "daily_accumulation"


@pytest.mark.anyio
async def test_gpm_adapter_fetch_series_ambiguous_interval_rejected():
    """Verify that a rate (mm/hr) without an explicit duration is rejected rather than guessing 24h."""
    clean_id = "district-gorakhpur"
    mock_df = pd.DataFrame({
        "date": ["2024-08-01"],
        "rainfall_mm": [2.0],
        "unit": ["mm/hr"],  # No duration_hours or interval_minutes provided!
    })
    with patch("pandas.read_csv", return_value=mock_df), \
         patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(AdapterPayloadError, match="Ambiguous temporal interval"):
            await GPMIMERGAdapter.fetch_series(clean_id, run_type="Late")


@pytest.mark.anyio
async def test_chirps_adapter_provenance_cached_status():
    """Verify that CHIRPS observations from local archive are explicitly labeled with is_cached_archive."""
    resp = await CHIRPSAdapter.fetch_series(
        region_id="district-gorakhpur",
        start_date=date(2024, 8, 1),
        end_date=date(2024, 8, 5)
    )
    assert resp.metadata.get("is_cached_archive") is True
    assert "gorakhpur_chirps_daily_verified.csv" in resp.metadata.get("provenance_archive", "")
    assert resp.temporal_semantics == "daily_accumulated_depth"


@pytest.mark.anyio
async def test_gpm_adapter_district_isolation_boundary_failure():
    """Verify GPM fetch fails with DistrictIsolationError if district has no boundary polygon."""
    with pytest.raises(DistrictIsolationError, match="lacks validated boundary"):
        await GPMIMERGAdapter.fetch_series("district-nonexistent-bound")


# =============================================================================
# 4. OpenMeteoAdapter Tests
# =============================================================================

def test_open_meteo_metadata_reanalysis_classification():
    """Verify Open-Meteo is strictly classified as MODELLED_REANALYSIS, not ground observation."""
    meta = OpenMeteoAdapter.get_metadata()
    assert meta.source_id == "open_meteo_archive"
    assert meta.dataset_type == DatasetType.MODELLED_REANALYSIS
    assert meta.auth_required is False
    assert "Modelled numerical weather prediction reanalysis" in meta.limitations


@pytest.mark.anyio
async def test_open_meteo_check_connection_timeout_handling():
    """Verify timeout resilience when connecting to Open-Meteo."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Mock timeout")):
        res = await OpenMeteoAdapter.check_connection(timeout_seconds=0.1)
        assert res["status"] == SourceConnectionStatus.TIMEOUT
        assert "timed out" in res["error"]


@pytest.mark.anyio
async def test_open_meteo_fetch_series_rate_limit_handling():
    """Verify HTTP 429 response is mapped cleanly to RATE_LIMITED status."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        resp = await OpenMeteoAdapter.fetch_series("district-gorakhpur")
        assert resp.status == SourceConnectionStatus.RATE_LIMITED
        assert resp.records_count == 0
        assert "rate limit" in resp.error_message.lower()


@pytest.mark.anyio
async def test_open_meteo_fetch_series_valid_mock_payload():
    """Verify parsing and validation of Open-Meteo daily JSON response."""
    mock_json = {
        "latitude": 26.76,
        "longitude": 83.37,
        "daily": {
            "time": ["2024-08-01", "2024-08-02", "2024-08-03"],
            "precipitation_sum": [15.2, 0.0, None]
        },
        "daily_units": {"precipitation_sum": "mm"}
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_json

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        resp = await OpenMeteoAdapter.fetch_series("district-gorakhpur")
        assert resp.status == SourceConnectionStatus.CONNECTED
        assert resp.records_count == 3
        assert resp.valid_count == 2
        assert resp.missing_count == 1
        assert resp.observations[0].rainfall_mm == 15.2
        assert resp.observations[1].rainfall_mm == 0.0
        assert resp.observations[1].quality_status == QualityStatus.ZERO_PRECIPITATION
        assert resp.observations[2].rainfall_mm is None
        assert resp.observations[2].quality_status == QualityStatus.MISSING


def test_open_meteo_payload_validation():
    """Verify validation of Open-Meteo payload structure."""
    valid_payload = {
        "daily": {
            "time": ["2024-01-01"],
            "precipitation_sum": [5.0]
        }
    }
    res = OpenMeteoAdapter.validate_payload(valid_payload)
    assert res["total_days"] == 1

    # Length mismatch
    mismatch_payload = {
        "daily": {
            "time": ["2024-01-01", "2024-01-02"],
            "precipitation_sum": [5.0]
        }
    }
    with pytest.raises(AdapterPayloadError, match="Mismatch between 'time' and 'precipitation_sum'"):
        OpenMeteoAdapter.validate_payload(mismatch_payload)


# =============================================================================
# 5. SRTMAdapter Tests
# =============================================================================

def test_srtm_adapter_metadata_and_static_reference():
    """Verify SRTM is configured strictly as a STATIC_REFERENCE dataset."""
    meta = SRTMAdapter.get_metadata()
    assert meta.source_id == "nasa_srtm_30m"
    assert meta.dataset_type == DatasetType.STATIC_REFERENCE
    assert meta.default_units == "meters"
    assert meta.is_rate_based is False
    assert meta.latency == "Static Reference (Zero latency)"


@pytest.mark.anyio
async def test_srtm_adapter_check_connection():
    """Verify SRTM reports STATIC_REFERENCE status and lists calibrated benchmarks."""
    res = await SRTMAdapter.check_connection()
    assert res["status"] == SourceConnectionStatus.STATIC_REFERENCE
    assert res["is_static"] is True
    assert "district-gorakhpur" in res["calibrated_districts"]
    assert "district-mahoba" in res["calibrated_districts"]


@pytest.mark.anyio
async def test_srtm_adapter_fetch_series_rejected():
    """Verify calling fetch_series() on static SRTM dataset raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="static topographic dataset"):
        await SRTMAdapter.fetch_series("district-gorakhpur")


def test_srtm_adapter_elevation_profile_and_isolation():
    """Verify elevation profile retrieval for pilots and clean rejection of candidate districts."""
    # Gorakhpur (lowland terai plain)
    g_prof = SRTMAdapter.get_elevation_profile("district-gorakhpur")
    assert g_prof["mean_elevation_m"] == 77.7
    assert g_prof["terrain_vulnerability_index"] == 0.88
    assert "Terai Lowland" in g_prof["terrain_type"]

    # Mahoba (Bundelkhand plateau)
    m_prof = SRTMAdapter.get_elevation_profile("district-mahoba")
    assert m_prof["mean_elevation_m"] == 197.1
    assert m_prof["terrain_vulnerability_index"] == 0.15
    assert "Bundelkhand" in g_prof.get("terrain_type", "") or "Bundelkhand" in m_prof["terrain_type"]

    # Candidate district without calibrated SRTM benchmark must raise DistrictIsolationError
    with pytest.raises(DistrictIsolationError):
        SRTMAdapter.get_elevation_profile("district-lucknow")


def test_srtm_payload_validation():
    """Verify terrestrial elevation bounds checking."""
    valid_terrain = {
        "mean_elevation_m": 80.0,
        "min_elevation_m": 75.0,
        "max_elevation_m": 85.0,
        "elevation_std_m": 2.5
    }
    res = SRTMAdapter.validate_payload(valid_terrain)
    assert res["relief_range_m"] == 10.0

    # Negative standard deviation
    with pytest.raises(AdapterPayloadError, match="Standard deviation cannot be negative"):
        SRTMAdapter.validate_payload({**valid_terrain, "elevation_std_m": -1.0})

    # Out of bounds elevation (> 9000 m)
    with pytest.raises(AdapterPayloadError, match="Physical bounds violation"):
        SRTMAdapter.validate_payload({**valid_terrain, "max_elevation_m": 12000.0})


# =============================================================================
# 6. ScientificSourceRegistry Tests
# =============================================================================

def test_registry_lookup_and_listing():
    """Verify discovery and querying of registered adapters."""
    adapters = ScientificSourceRegistry.list_adapters()
    assert len(adapters) == 4
    ids = [a.source_id for a in adapters]
    assert "chirps_daily" in ids
    assert "nasa_gpm_imerg" in ids
    assert "open_meteo_archive" in ids
    assert "nasa_srtm_30m" in ids

    # Exact retrieval
    assert ScientificSourceRegistry.get_adapter("chirps_daily") is CHIRPSAdapter
    assert ScientificSourceRegistry.get_adapter("nasa_gpm_imerg") is GPMIMERGAdapter
    assert ScientificSourceRegistry.get_adapter("open_meteo_archive") is OpenMeteoAdapter
    assert ScientificSourceRegistry.get_adapter("nasa_srtm_30m") is SRTMAdapter

    # Unknown key raises KeyError
    with pytest.raises(KeyError, match="Unknown scientific source adapter"):
        ScientificSourceRegistry.get_adapter("unknown_provider")


@pytest.mark.anyio
async def test_registry_check_all_connections():
    """Verify aggregated parallel health auditing across all registered adapters."""
    report = await ScientificSourceRegistry.check_all_connections()
    assert report["total_adapters"] == 4
    assert "chirps_daily" in report["sources"]
    assert "nasa_gpm_imerg" in report["sources"]
    assert "open_meteo_archive" in report["sources"]
    assert "nasa_srtm_30m" in report["sources"]
