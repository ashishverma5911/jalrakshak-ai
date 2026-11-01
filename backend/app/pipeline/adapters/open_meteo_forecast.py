"""
Open-Meteo Operational Forecast & Near-Real-Time Weather Model Adapter (Phase 3A)
Retrieves hourly numerical weather prediction (NWP) model outputs from the official
Open-Meteo Weather Forecast API (https://api.open-meteo.com/v1/forecast).

Scientific Transparency Notice:
- Dataset Type: FORECAST & MODELLED_ESTIMATE (ECMWF IFS / GFS Blended NWP)
- Represents numerical weather prediction model simulations at district centroid coordinates.
- Strictly NOT direct in-situ ground gauge or automatic weather station (AWS) measurements.
- Strictly representative-point estimates; not polygon-averaged over district boundaries.
- Distinguishes near-current model outputs from future forecast projections.
- Missing values remain strictly None / null; never converted into zero.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, date, timedelta
import httpx

from .base import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterResponse,
    ObservationRecord,
    SourceConnectionStatus,
    DatasetType,
    QualityStatus,
    AdapterPayloadError,
    DistrictIsolationError,
    AdapterConnectionError,
)
from ...core.config import (
    OPEN_METEO_FORECAST_URL,
    OPEN_METEO_API_KEY,
    LIVE_REQUEST_TIMEOUT_SECONDS,
    LIVE_MAX_RETRIES,
)

logger = logging.getLogger("jalrakshak.pipeline.adapter.open_meteo_forecast")

# Authoritative district centroid coordinates (WGS84 EPSG:4326)
DISTRICT_COORDINATES: Dict[str, Dict[str, Any]] = {
    "district-gorakhpur": {"name": "Gorakhpur", "lat": 26.7606, "lng": 83.3732, "state": "UP"},
    "district-mahoba": {"name": "Mahoba", "lat": 25.2953, "lng": 79.8630, "state": "UP"},
    "district-lucknow": {"name": "Lucknow", "lat": 26.8467, "lng": 80.9462, "state": "UP"},
    "district-prayagraj": {"name": "Prayagraj", "lat": 25.4358, "lng": 81.8463, "state": "UP"},
    "district-varanasi": {"name": "Varanasi", "lat": 25.3176, "lng": 82.9739, "state": "UP"},
    "district-jhansi": {"name": "Jhansi", "lat": 25.4484, "lng": 78.5685, "state": "UP"},
    "district-banda": {"name": "Banda", "lat": 25.4754, "lng": 80.3346, "state": "UP"},
    "district-kushinagar": {"name": "Kushinagar", "lat": 26.7410, "lng": 83.8887, "state": "UP"},
    "district-deoria": {"name": "Deoria", "lat": 26.5024, "lng": 83.7791, "state": "UP"},
    "district-patna": {"name": "Patna", "lat": 25.5941, "lng": 85.1376, "state": "Bihar"},
    "district-gaya": {"name": "Gaya", "lat": 24.7955, "lng": 85.0002, "state": "Bihar"},
}


class OpenMeteoForecastAdapter(ScientificSourceAdapter):
    """
    Adapter for Open-Meteo operational weather forecast API (NWP model data).
    Integrates hourly precipitation, 2m temperature, relative humidity,
    10m wind speed, and reference FAO-56 evapotranspiration (ET0).
    """

    METADATA = AdapterMetadata(
        source_id="open_meteo_forecast",
        name="Open-Meteo Operational Forecast & Weather Model",
        provider="Open-Meteo GmbH / ECMWF / DWD / NOAA",
        product_version="v1 Forecast API (ECMWF IFS / GFS Blended NWP)",
        dataset_type=DatasetType.FORECAST,
        spatial_resolution="0.1° (~11 km grid representative point estimate)",
        temporal_resolution="Hourly and Daily aggregated series",
        default_units="mm",
        is_rate_based=False,
        historical_coverage="Past 7 days model estimates + 7 days operational forecast",
        latency="Near-real-time model cycle updates (~1 hour)",
        auth_required=False,
        access_method="Public REST API HTTPS (https://api.open-meteo.com/v1/forecast)",
        citations=[
            "Open-Meteo Weather API Documentation (https://open-meteo.com/en/docs)",
            "Zippenfenig, P. (2023). Open-Meteo: Open-source weather API.",
        ],
        limitations=(
            "Model-derived numerical weather prediction estimates. Does NOT represent direct in-situ "
            "rain-gauge or weather station observations. District centroid values are representative-point "
            "estimates, NOT district-wide spatial polygon averages. Does not simulate river hydrodynamics."
        ),
    )

    @classmethod
    def get_metadata(cls) -> AdapterMetadata:
        return cls.METADATA

    @classmethod
    def resolve_district_coordinates(cls, district_id: str) -> Dict[str, Any]:
        """
        Resolves geographical coordinates for a district identifier.
        Enforces strict district isolation: never substitutes adjacent district coordinates.
        """
        clean_id = cls.normalize_region_id(district_id)
        if clean_id in DISTRICT_COORDINATES:
            return DISTRICT_COORDINATES[clean_id]

        # Dynamic lookup from metadata fixtures
        try:
            from ..ingestion import DataIngestionService
            ingestion = DataIngestionService()
            slug = clean_id.replace("district-", "").strip()
            info = ingestion.get_district_info(slug)
            return {
                "name": info.get("name", slug.capitalize()),
                "lat": float(info["lat"]),
                "lng": float(info["lng"]),
                "state": info.get("state", "UP"),
            }
        except Exception:
            pass

        raise DistrictIsolationError(
            f"Coordinates for district '{clean_id}' could not be resolved from authoritative registry. "
            "District isolation strictly forbids substituting adjacent district coordinates."
        )

    @classmethod
    async def check_connection(cls, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Verifies Open-Meteo Forecast endpoint reachability with a lightweight ping.
        """
        now = datetime.now(timezone.utc)
        result: Dict[str, Any] = {
            "source_id": cls.METADATA.source_id,
            "provider": cls.METADATA.provider,
            "endpoint": OPEN_METEO_FORECAST_URL,
            "checked_at": now.isoformat(),
            "status": SourceConnectionStatus.UNREACHABLE,
            "latency_ms": None,
        }

        # Query lightweight coordinate test
        test_url = f"{OPEN_METEO_FORECAST_URL}?latitude=26.76&longitude=83.37&hourly=precipitation&forecast_days=1&timezone=UTC"
        headers = {}
        if OPEN_METEO_API_KEY:
            headers["apikey"] = OPEN_METEO_API_KEY

        try:
            start_t = datetime.now(timezone.utc)
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.get(test_url, headers=headers)
                latency = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000.0
                result["latency_ms"] = round(latency, 1)

                if resp.status_code == 200:
                    result["status"] = SourceConnectionStatus.CONNECTED
                    result["message"] = "Open-Meteo Forecast API reachable."
                elif resp.status_code == 429:
                    result["status"] = SourceConnectionStatus.RATE_LIMITED
                    result["error"] = "Open-Meteo API rate limit exceeded."
                else:
                    result["status"] = SourceConnectionStatus.ERROR
                    result["status_code"] = resp.status_code
        except httpx.TimeoutException:
            result["status"] = SourceConnectionStatus.TIMEOUT
            result["error"] = f"Connection timed out after {timeout_seconds}s."
        except Exception as exc:
            result["status"] = SourceConnectionStatus.ERROR
            result["error"] = str(exc)

        return result

    @classmethod
    async def fetch_forecast_raw(
        cls,
        lat: float,
        lng: float,
        past_days: int = 7,
        forecast_days: int = 7,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes bounded, resilient HTTP GET to Open-Meteo Forecast API.
        Applies exponential backoff with strict max-retry caps.
        """
        timeout = timeout_seconds or LIVE_REQUEST_TIMEOUT_SECONDS
        retries = max_retries if max_retries is not None else LIVE_MAX_RETRIES

        params = {
            "latitude": round(lat, 4),
            "longitude": round(lng, 4),
            "hourly": "precipitation,temperature_2m,relative_humidity_2m,wind_speed_10m,et0_fao_evapotranspiration",
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "UTC",
        }

        headers = {}
        if OPEN_METEO_API_KEY:
            headers["apikey"] = OPEN_METEO_API_KEY

        last_error = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(OPEN_METEO_FORECAST_URL, params=params, headers=headers)

                    if resp.status_code == 200:
                        try:
                            return resp.json()
                        except Exception as e:
                            raise AdapterPayloadError(f"Failed to decode Open-Meteo JSON payload: {e}")

                    if resp.status_code == 429:
                        raise AdapterConnectionError("Open-Meteo rate limit exceeded (HTTP 429).")

                    if 500 <= resp.status_code < 600:
                        last_error = AdapterConnectionError(f"Open-Meteo server error (HTTP {resp.status_code}).")
                    else:
                        raise AdapterPayloadError(f"Open-Meteo returned client error (HTTP {resp.status_code}).")

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = AdapterConnectionError(f"Open-Meteo network request failed: {type(exc).__name__}")

            if attempt < retries:
                backoff = 0.5 * (2 ** attempt)
                await asyncio.sleep(backoff)

        raise last_error or AdapterConnectionError("Failed to fetch Open-Meteo data after retries.")

    @classmethod
    def validate_and_parse_hourly(
        cls,
        payload: Dict[str, Any],
        district_id: str,
        coords: Dict[str, Any],
        retrieval_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Strictly parses and validates Open-Meteo hourly response.
        Enforces physical bounds, separates forecasts from observations,
        and ensures missing values remain None.
        """
        if not isinstance(payload, dict):
            raise AdapterPayloadError("Expected JSON dictionary from Open-Meteo.")

        hourly = payload.get("hourly")
        if not hourly or not isinstance(hourly, dict):
            raise AdapterPayloadError("Missing or invalid 'hourly' object in Open-Meteo payload.")

        required_keys = ["time", "precipitation", "temperature_2m", "relative_humidity_2m", "wind_speed_10m"]
        for k in required_keys:
            if k not in hourly:
                raise AdapterPayloadError(f"Open-Meteo hourly payload missing mandatory variable: '{k}'.")

        times = hourly["time"]
        precips = hourly["precipitation"]
        temps = hourly["temperature_2m"]
        humidities = hourly["relative_humidity_2m"]
        winds = hourly["wind_speed_10m"]
        et0s = hourly.get("et0_fao_evapotranspiration", [None] * len(times))

        num_records = len(times)
        if not (len(precips) == len(temps) == len(humidities) == len(winds) == num_records):
            raise AdapterPayloadError("Mismatch in lengths of Open-Meteo hourly variable arrays.")

        now_utc = retrieval_time or datetime.now(timezone.utc)
        parsed_records: List[Dict[str, Any]] = []

        valid_precip_count = 0
        missing_precip_count = 0
        forecast_count = 0

        for idx in range(num_records):
            t_raw = times[idx]
            try:
                # Open-Meteo returns '2026-10-28T00:00' when timezone=UTC
                dt = datetime.fromisoformat(t_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception as e:
                raise AdapterPayloadError(f"Invalid timestamp '{t_raw}' at index {idx}: {e}")

            # Forecast classification: future timestamps relative to retrieval are forecasts
            is_forecast = dt > now_utc
            if is_forecast:
                forecast_count += 1

            # 1. Precipitation bounds & missingness check
            p_val = precips[idx]
            clean_p: Optional[float] = None
            q_status = "observed_estimate" if not is_forecast else "forecast"

            if p_val is None:
                clean_p = None
                q_status = "missing"
                missing_precip_count += 1
            else:
                try:
                    f_val = float(p_val)
                    if f_val < 0.0:
                        raise AdapterPayloadError(f"Negative precipitation ({f_val} mm) rejected at {t_raw}.")
                    if f_val > 500.0:
                        clean_p = 500.0
                        q_status = "provisional_extreme"
                    else:
                        clean_p = round(f_val, 2)
                        valid_precip_count += 1
                except (ValueError, TypeError):
                    clean_p = None
                    q_status = "missing"
                    missing_precip_count += 1

            # 2. Temperature physical bounds (-50°C to +60°C)
            t_val = temps[idx]
            clean_t: Optional[float] = None
            if t_val is not None:
                f_t = float(t_val)
                if -50.0 <= f_t <= 60.0:
                    clean_t = round(f_t, 1)

            # 3. Relative humidity bounds (0 to 100%)
            h_val = humidities[idx]
            clean_h: Optional[float] = None
            if h_val is not None:
                f_h = float(h_val)
                clean_h = max(0.0, min(100.0, round(f_h, 1)))

            # 4. Wind speed bounds (0 to 300 km/h)
            w_val = winds[idx]
            clean_w: Optional[float] = None
            if w_val is not None:
                f_w = float(w_val)
                if 0.0 <= f_w <= 300.0:
                    clean_w = round(f_w, 1)

            # 5. Evapotranspiration bounds (0 to 50 mm/hr)
            e_val = et0s[idx] if idx < len(et0s) else None
            clean_e: Optional[float] = None
            if e_val is not None:
                f_e = float(e_val)
                if 0.0 <= f_e <= 50.0:
                    clean_e = round(f_e, 3)

            parsed_records.append({
                "timestamp": dt.isoformat(),
                "dt": dt,
                "precipitation_mm": clean_p,
                "temperature_2m_c": clean_t,
                "relative_humidity_pct": clean_h,
                "wind_speed_10m_kmh": clean_w,
                "et0_evapotranspiration_mm": clean_e,
                "is_forecast": is_forecast,
                "quality_status": q_status,
            })

        return {
            "district_id": district_id,
            "coordinates": coords,
            "retrieval_timestamp": now_utc.isoformat(),
            "records": parsed_records,
            "total_records": num_records,
            "valid_precip_count": valid_precip_count,
            "missing_precip_count": missing_precip_count,
            "forecast_count": forecast_count,
        }

    @classmethod
    def aggregate_hourly_to_daily(
        cls,
        hourly_records: List[Dict[str, Any]],
        min_hours_coverage: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates validated hourly records into calendar-day precipitation totals (UTC).
        Requires minimum hourly coverage (default: 20/24 hours).
        If coverage is inadequate, daily precipitation remains None (missing).
        Separates forecast days from observed/reanalysis days.
        """
        days_map: Dict[date, List[Dict[str, Any]]] = {}
        for r in hourly_records:
            d = r["dt"].date()
            if d not in days_map:
                days_map[d] = []
            days_map[d].append(r)

        daily_summaries: List[Dict[str, Any]] = []
        for d in sorted(days_map.keys()):
            pts = days_map[d]
            total_hours = len(pts)
            valid_p_pts = [p["precipitation_mm"] for p in pts if p["precipitation_mm"] is not None]
            missing_hours = total_hours - len(valid_p_pts)

            # Check if this entire day is in the forecast period (majority of hours forecast)
            forecast_hours = sum(1 for p in pts if p.get("is_forecast", False))
            is_forecast_day = forecast_hours > (total_hours / 2)

            if len(valid_p_pts) >= min_hours_coverage:
                daily_sum = round(sum(valid_p_pts), 2)
                q_status = "forecast" if is_forecast_day else "observed_estimate"
            else:
                daily_sum = None
                q_status = "missing"

            daily_summaries.append({
                "date": d.isoformat(),
                "rainfall_mm": daily_sum,
                "is_forecast": is_forecast_day,
                "hours_recorded": len(valid_p_pts),
                "hours_missing": missing_hours,
                "quality_status": q_status,
            })

        return daily_summaries
