"""
JalRakshak AI — Phase 3B Open-Meteo HTTP 429 Rate Limit Protection & Resilience Test Suite

Verifies:
1. HTTP 429 parsing: parses integer seconds and RFC 1123/2822 HTTP dates.
2. Conservative bounded fallback: missing or invalid Retry-After clamps between 30s and 300s (default 60s).
3. Global provider cooldown: suppresses all outbound calls across Gorakhpur, Mahoba, and other districts during cooldown.
4. Cache preservation: serves stale cache (<24h) as DATA_STALE or CACHED during cooldown without outbound attempts.
5. Honest empty fallback: serves honest DATA_PENDING with zero fabricated values when no cache exists.
6. Negative caching: suppresses immediate repeat attempts on transient failures.
7. Cross-district synchronization: deduplicates simultaneous cold-start requests.
8. Cooldown expiration and recovery: cleanly resumes live fetching after cooldown elapses.
9. System status API: GET /api/v1/environmental/status exposes cooldown state, remaining time, and reason.
10. Refresh endpoint: POST /api/v1/environmental/refresh returns live payload in data field.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.core import config
from app.pipeline.adapters.open_meteo_forecast import (
    OpenMeteoForecastAdapter,
    DISTRICT_COORDINATES,
)
from app.pipeline.adapters.base import (
    SourceConnectionStatus,
    AdapterConnectionError,
    AdapterRateLimitError,
)
from app.services.environmental_cache import (
    EnvironmentalCacheService,
    _memory_cache,
    _last_refresh_timestamps,
    _negative_cache,
)
from app.schemas.environmental import (
    EnvironmentalLiveResponse,
    EnvironmentalSystemStatusResponse,
    EnvironmentalRefreshResponse,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_cache_and_cooldown():
    """Ensures clean cache, locks, and cooldown state for each test."""
    EnvironmentalCacheService.clear_cache()
    _last_refresh_timestamps.clear()
    _negative_cache.clear()
    yield
    EnvironmentalCacheService.clear_cache()
    _last_refresh_timestamps.clear()
    _negative_cache.clear()


def sample_open_meteo_response(lat=26.7606, lng=83.3732):
    base_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
        precip.append(2.5 if h % 4 == 0 else 0.0)
        temp.append(29.0)
        humidity.append(60.0)
        wind.append(10.0)
        et0.append(0.25)

    return {
        "latitude": lat,
        "longitude": lng,
        "generationtime_ms": 0.35,
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


# =====================================================================
# 1. Adapter Retry-After Parsing & Error Raising
# =====================================================================

def test_parse_retry_after_integer_seconds():
    """Verify parsing integer delta-seconds from Retry-After header."""
    assert OpenMeteoForecastAdapter._parse_retry_after("60") == 60
    assert OpenMeteoForecastAdapter._parse_retry_after(" 120 ") == 120
    assert OpenMeteoForecastAdapter._parse_retry_after("0") == 1
    assert OpenMeteoForecastAdapter._parse_retry_after("-5") == 1


def test_parse_retry_after_http_date():
    """Verify parsing RFC 1123/2822 HTTP date from Retry-After header."""
    future_time = datetime.now(timezone.utc) + timedelta(seconds=90)
    http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    parsed_sec = OpenMeteoForecastAdapter._parse_retry_after(http_date)
    assert parsed_sec is not None
    assert 80 <= parsed_sec <= 95


def test_parse_retry_after_invalid_returns_none():
    """Verify invalid or empty Retry-After header returns None."""
    assert OpenMeteoForecastAdapter._parse_retry_after(None) is None
    assert OpenMeteoForecastAdapter._parse_retry_after("") is None
    assert OpenMeteoForecastAdapter._parse_retry_after("invalid-date-format") is None


@pytest.mark.anyio
async def test_fetch_forecast_raw_429_raises_rate_limit_error_without_retrying():
    """
    Verify HTTP 429 immediately raises AdapterRateLimitError with parsed headers
    and does NOT retry 2 times.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "45", "X-RateLimit-Reset": "45"}
    mock_resp.json.return_value = {"reason": "Daily request limit exceeded"}

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        with pytest.raises(AdapterRateLimitError) as exc_info:
            await OpenMeteoForecastAdapter.fetch_forecast_raw(26.76, 83.37, max_retries=2)

        # Confirm exactly 1 call was made (no retries)
        assert call_count == 1
        assert exc_info.value.retry_after_seconds == 45
        assert exc_info.value.reason == "Daily request limit exceeded"


# =====================================================================
# 2. Cooldown Clamping & Fallbacks
# =====================================================================

def test_set_provider_cooldown_clamping():
    """Verify cooldown is clamped between 30 and 300 seconds (default 60s)."""
    sec = EnvironmentalCacheService.set_provider_cooldown(None)
    assert sec == 60.0
    assert EnvironmentalCacheService.is_provider_in_cooldown() is True
    assert 55.0 <= EnvironmentalCacheService.get_cooldown_remaining_seconds() <= 60.0

    sec_low = EnvironmentalCacheService.set_provider_cooldown(5)
    assert sec_low == 30.0

    sec_high = EnvironmentalCacheService.set_provider_cooldown(9999)
    assert sec_high == 300.0


# =====================================================================
# 3. Global Cooldown Cross-District Call Suppression
# =====================================================================

@pytest.mark.anyio
async def test_global_cooldown_suppresses_outbound_calls_across_all_districts():
    """
    When Open-Meteo returns HTTP 429 for Gorakhpur, global cooldown activates.
    Subsequent requests for Gorakhpur, Mahoba, Gaya, etc. must make ZERO outbound calls.
    """
    outbound_mock = AsyncMock(
        side_effect=AdapterRateLimitError(
            message="Rate limit exceeded",
            retry_after_seconds=60,
            reason="Hour quota reached",
        )
    )

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", outbound_mock):
        # 1. First request for Gorakhpur hits 429
        res_gork = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res_gork.data_mode == "DATA_PENDING"
        assert res_gork.provider_status["cooldown_active"] is True
        assert outbound_mock.call_count == 1

        # 2. Subsequent request for Gorakhpur during cooldown: 0 additional outbound calls
        res_gork_2 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res_gork_2.data_mode == "DATA_PENDING"
        assert outbound_mock.call_count == 1

        # 3. Request for Mahoba during cooldown: 0 outbound calls
        res_mah = await EnvironmentalCacheService.get_district_environmental_data("mahoba")
        assert res_mah.data_mode == "DATA_PENDING"
        assert res_mah.provider_status["cooldown_active"] is True
        assert outbound_mock.call_count == 1

        # 4. Request for candidate district Gaya during cooldown: 0 outbound calls
        res_gaya = await EnvironmentalCacheService.get_district_environmental_data("gaya")
        assert res_gaya.data_mode == "DATA_PENDING"
        assert outbound_mock.call_count == 1


# =====================================================================
# 4. Stale Cache Preservation During Cooldown
# =====================================================================

@pytest.mark.anyio
async def test_stale_cache_returned_during_429_cooldown():
    """
    If a district has cached data (<24h old) and a 429 cooldown is triggered,
    the cache is preserved and served as DATA_STALE with cooldown details.
    """
    now_utc = datetime.now(timezone.utc)
    cached_timestamp = (now_utc - timedelta(hours=4)).isoformat()
    coords = DISTRICT_COORDINATES["district-gorakhpur"]

    _memory_cache["district-gorakhpur"] = {
        "district_id": "district-gorakhpur",
        "retrieval_timestamp": cached_timestamp,
        "expires_at": (now_utc - timedelta(hours=1)).isoformat(),
        "coordinates": coords,
        "hourly_records": [
            {
                "timestamp": cached_timestamp,
                "precipitation_mm": 1.5,
                "temperature_2m_c": 31.0,
                "relative_humidity_pct": 70.0,
                "wind_speed_10m_kmh": 14.0,
                "et0_evapotranspiration_mm": 0.3,
                "is_forecast": False,
                "quality_status": "observed_estimate",
            }
        ],
        "daily_records": [],
        "raw_metadata": {},
    }

    # Activate global cooldown
    EnvironmentalCacheService.set_provider_cooldown(60, "Rate limit reached")

    outbound_mock = AsyncMock()
    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", outbound_mock):
        res = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")

        # Zero outbound calls made
        assert outbound_mock.call_count == 0

        # Served from stale cache
        assert res.data_mode == "DATA_STALE"
        assert res.freshness.is_cached is True
        assert res.freshness.is_stale is True
        assert res.current_conditions is not None
        assert res.current_conditions.temperature_2m_c == 31.0
        assert res.provider_status["status"] == "provider_cooldown_active"
        assert res.provider_status["cooldown_remaining_seconds"] > 0


# =====================================================================
# 5. Cold-Start Honest Fallback (DATA_PENDING, Zero Fabrications)
# =====================================================================

@pytest.mark.anyio
async def test_cold_start_empty_cache_returns_honest_pending_during_429():
    """
    On cold start with no local disk/memory cache, an HTTP 429 must return
    DATA_PENDING with honest error message and strictly zero fabricated metrics.
    """
    outbound_mock = AsyncMock(
        side_effect=AdapterRateLimitError(
            message="Open-Meteo rate limit exceeded (HTTP 429)",
            retry_after_seconds=60,
        )
    )

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", outbound_mock):
        res = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")

        assert res.data_mode == "DATA_PENDING"
        assert res.current_conditions is None
        assert len(res.hourly_series) == 0
        assert len(res.daily_precipitation) == 0
        assert "Open-Meteo" in res.provider_status["error"]
        assert res.provider_status["cooldown_active"] is True


# =====================================================================
# 6. Negative Caching for Transient Failures
# =====================================================================

@pytest.mark.anyio
async def test_negative_caching_suppresses_repeat_failures():
    """
    On non-429 provider error (e.g. 500 server error or timeout),
    a 30-second negative cache prevents immediate repeat outbound requests.
    """
    outbound_mock = AsyncMock(
        side_effect=AdapterConnectionError("Open-Meteo 500 Internal Server Error")
    )

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", outbound_mock):
        # First call fails and activates negative cache
        res1 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res1.data_mode == "DATA_PENDING"
        assert outbound_mock.call_count == 1

        # Second call within 30s is suppressed by negative cache
        res2 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
        assert res2.data_mode == "DATA_PENDING"
        assert outbound_mock.call_count == 1


# =====================================================================
# 7. Recovery After Cooldown Elapses
# =====================================================================

@pytest.mark.anyio
async def test_cooldown_expiration_allows_fresh_fetch():
    """
    Once the cooldown timestamp has passed, the system resumes normal
    outbound fetching and successfully caches HTTP 200 data.
    """
    past_utc = datetime.now(timezone.utc) - timedelta(seconds=1)
    EnvironmentalCacheService.set_provider_cooldown(30)
    from app.services import environmental_cache
    environmental_cache._provider_cooldown_until = past_utc

    assert EnvironmentalCacheService.is_provider_in_cooldown() is False

    valid_payload = sample_open_meteo_response()
    outbound_mock = AsyncMock(return_value=valid_payload)

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", outbound_mock):
        res = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")

        assert res.data_mode == "LIVE_MODEL"
        assert outbound_mock.call_count == 1
        assert res.current_conditions is not None
        assert res.current_conditions.temperature_2m_c == 29.0


# =====================================================================
# 8. GET /api/v1/environmental/status Exposes Cooldown Telemetry
# =====================================================================

def test_environmental_status_endpoint_exposes_cooldown_state():
    """Verify GET /api/v1/environmental/status reports cooldown active and remaining seconds."""
    with patch("app.core.config.LIVE_DATA_ENABLED", True):
        with patch("app.api.environmental.LIVE_DATA_ENABLED", True):
            # 1. When not in cooldown
            EnvironmentalCacheService.reset_cooldown()
            r1 = client.get("/api/v1/environmental/status")
            assert r1.status_code == 200
            d1 = r1.json()
            assert d1["provider_connection_status"] == "online"
            assert d1["provider_cooldown_active"] is False
            assert d1["cooldown_remaining_seconds"] == 0.0

            # 2. When cooldown is active
            EnvironmentalCacheService.set_provider_cooldown(60, "Open-Meteo HTTP 429 Rate Limit")
            r2 = client.get("/api/v1/environmental/status")
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["provider_connection_status"] == "rate_limited_cooldown"
            assert d2["provider_cooldown_active"] is True
            assert 55.0 <= d2["cooldown_remaining_seconds"] <= 60.0
            assert "HTTP 429" in d2["provider_cooldown_reason"]


# =====================================================================
# 9. POST /api/v1/environmental/refresh Returns Live Payload
# =====================================================================

def test_environmental_refresh_endpoint_returns_data_payload():
    """
    Verify POST /api/v1/environmental/refresh returns updated EnvironmentalLiveResponse
    in the 'data' field, preventing redundant GET requests from the frontend.
    """
    valid_payload = sample_open_meteo_response()

    with patch("app.core.config.LIVE_DATA_ENABLED", True):
        with patch("app.api.environmental.LIVE_DATA_ENABLED", True):
            with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", AsyncMock(return_value=valid_payload)):
                resp = client.post("/api/v1/environmental/refresh?location=gorakhpur")
                assert resp.status_code == 200
                data = resp.json()

                assert data["success"] is True
                assert data["district_id"] == "district-gorakhpur"
                assert data["status"] == "refreshed"
                assert data["data_mode"] == "LIVE_MODEL"

                # Verify embedded data payload is present
                assert data["data"] is not None
                assert data["data"]["district_id"] == "district-gorakhpur"
                assert data["data"]["current_conditions"]["temperature_2m_c"] == 29.0
                assert len(data["data"]["hourly_series"]) > 0


# =====================================================================
# 10. Concurrency & Cross-Loop Resilience Tests
# =====================================================================

@pytest.mark.anyio
async def test_simultaneous_cross_district_requests_cooldown_recheck():
    """
    Verify that simultaneous requests for Gorakhpur and Mahoba (cold cache)
    result in EXACTLY ONE outbound provider call when the first request returns HTTP 429.
    The second request waiting on the provider lock must detect cooldown upon acquiring
    the lock and return DATA_PENDING without making a second outbound request.
    """
    outbound_calls = []

    async def mock_fetch(lat, lng, **kwargs):
        outbound_calls.append((lat, lng))
        # Small sleep to simulate realistic network delay and ensure both tasks queue up
        await asyncio.sleep(0.05)
        raise AdapterRateLimitError(
            message="Open-Meteo rate limit exceeded (HTTP 429)",
            retry_after_seconds=60,
            reason="Daily quota exceeded",
        )

    with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", side_effect=mock_fetch):
        # Fire simultaneous cold requests for Gorakhpur and Mahoba
        res_gork, res_mah = await asyncio.gather(
            EnvironmentalCacheService.get_district_environmental_data("gorakhpur"),
            EnvironmentalCacheService.get_district_environmental_data("mahoba"),
        )

        # Both must receive safe DATA_PENDING fallback
        assert res_gork.data_mode == "DATA_PENDING"
        assert res_mah.data_mode == "DATA_PENDING"

        # Exactly 1 outbound call was made across the entire system
        assert len(outbound_calls) == 1
        assert res_gork.provider_status["cooldown_active"] is True
        assert res_mah.provider_status["cooldown_active"] is True


def test_separate_event_loop_lifecycles_no_runtime_error():
    """
    Verify that executing requests across distinct, independent event loops
    (e.g., sequential asyncio.run calls) does not raise
    'RuntimeError: Task got Future attached to a different loop'.
    """
    # Loop 1 lifecycle
    async def run_in_loop_1():
        valid_payload = sample_open_meteo_response()
        with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", AsyncMock(return_value=valid_payload)):
            res1 = await EnvironmentalCacheService.get_district_environmental_data("gorakhpur")
            assert res1.data_mode == "LIVE_MODEL"

    asyncio.run(run_in_loop_1())

    # Clear cache and run in Loop 2 lifecycle (completely different event loop instance)
    EnvironmentalCacheService.clear_cache()

    async def run_in_loop_2():
        valid_payload = sample_open_meteo_response()
        with patch.object(OpenMeteoForecastAdapter, "fetch_forecast_raw", AsyncMock(return_value=valid_payload)):
            res2 = await EnvironmentalCacheService.get_district_environmental_data("mahoba")
            assert res2.data_mode == "LIVE_MODEL"

    # Must execute cleanly with zero cross-loop Future/Lock errors
    asyncio.run(run_in_loop_2())
