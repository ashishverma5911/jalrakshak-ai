"""
Open-Meteo Numerical Weather Prediction & Reanalysis Adapter for JalRakshak AI
Manages ECMWF ERA5 reanalysis and operational forecast precipitation feeds.

Scientific Transparency Notice:
- Dataset Type: MODELLED_REANALYSIS (Historical) & FORECAST (Operational)
- Reanalysis and numerical weather prediction (NWP) outputs represent model simulations,
  NOT direct in-situ meteorological station gauge observations.
- Resolution: ~0.1° to 0.25° (~11–27 km grid).
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta, timezone
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
)
from ...core.config import OPEN_METEO_API_KEY, OPEN_METEO_ARCHIVE_URL

logger = logging.getLogger("jalrakshak.pipeline.adapter.open_meteo")

# District Centroid Coordinates (WGS84 EPSG:4326)
DISTRICT_COORDINATES: Dict[str, Dict[str, Any]] = {
    "district-gorakhpur": {"name": "Gorakhpur", "lat": 26.7606, "lng": 83.3732, "state": "UP"},
    "district-mahoba": {"name": "Mahoba", "lat": 25.2917, "lng": 79.8722, "state": "UP"},
    "district-lucknow": {"name": "Lucknow", "lat": 26.8467, "lng": 80.9462, "state": "UP"},
    "district-patna": {"name": "Patna", "lat": 25.5941, "lng": 85.1376, "state": "Bihar"},
    "district-varanasi": {"name": "Varanasi", "lat": 25.3176, "lng": 82.9739, "state": "UP"},
    "district-gaya": {"name": "Gaya", "lat": 24.7955, "lng": 85.0002, "state": "Bihar"},
}


class OpenMeteoAdapter(ScientificSourceAdapter):
    """
    Adapter for Open-Meteo numerical weather prediction and ERA5 reanalysis feeds.
    """

    METADATA = AdapterMetadata(
        source_id="open_meteo_archive",
        name="Open-Meteo ERA5 Reanalysis & Forecast Weather",
        provider="Open-Meteo GmbH / ECMWF / DWD / NOAA",
        product_version="v1 API (ECMWF ERA5 / GFS Blended)",
        dataset_type=DatasetType.MODELLED_REANALYSIS,
        spatial_resolution="0.1° to 0.25° (~11–27 km resolution)",
        temporal_resolution="Hourly and Daily accumulation (precipitation_sum)",
        default_units="mm",
        is_rate_based=False,
        historical_coverage="1940 – Present (ERA5 Reanalysis) + 7-14 Day Forecast",
        latency="Approximately 2 to 5 days for ERA5T / Instant for Forecast",
        auth_required=False,
        access_method="Public REST API HTTPS (https://archive-api.open-meteo.com/v1/archive)",
        citations=[
            "Hersbach, H., et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049.",
            "Open-Meteo Weather API Documentation (https://open-meteo.com/en/docs)",
        ],
        limitations=(
            "Modelled numerical weather prediction reanalysis. Does NOT represent direct in-situ ground gauge observations. "
            "May underestimate localized micro-orographic cloudbursts and convective precipitation spikes."
        ),
    )

    @classmethod
    def get_metadata(cls) -> AdapterMetadata:
        return cls.METADATA

    @classmethod
    async def check_connection(cls, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Verifies Open-Meteo API endpoint connectivity with a lightweight ping.
        """
        now = datetime.now(timezone.utc)
        result: Dict[str, Any] = {
            "source_id": cls.METADATA.source_id,
            "provider": cls.METADATA.provider,
            "checked_at": now.isoformat(),
            "status": SourceConnectionStatus.UNREACHABLE,
            "latency_ms": None,
            "auth_configured": bool(OPEN_METEO_API_KEY),
        }

        # Query a 1-day sample coordinate (Gorakhpur)
        test_url = f"{OPEN_METEO_ARCHIVE_URL}?latitude=26.76&longitude=83.37&start_date=2024-01-01&end_date=2024-01-01&daily=precipitation_sum&timezone=auto"
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
                    result["message"] = "Open-Meteo ERA5 API reachable."
                elif resp.status_code == 429:
                    result["status"] = SourceConnectionStatus.RATE_LIMITED
                    result["error"] = "Open-Meteo API rate limit exceeded."
                else:
                    result["status"] = SourceConnectionStatus.ERROR
                    result["status_code"] = resp.status_code
        except httpx.TimeoutException:
            result["status"] = SourceConnectionStatus.TIMEOUT
            result["error"] = f"Open-Meteo request timed out after {timeout_seconds}s."
        except httpx.RequestError as exc:
            result["status"] = SourceConnectionStatus.UNREACHABLE
            result["error"] = f"Open-Meteo unreachable: {type(exc).__name__}."
        except Exception as exc:
            result["status"] = SourceConnectionStatus.ERROR
            result["error"] = str(exc)

        return result

    @classmethod
    async def fetch_series(
        cls,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeout_seconds: float = 6.0,
    ) -> AdapterResponse:
        """
        Fetches daily ERA5 precipitation series for a district from Open-Meteo.
        Strictly labels results as MODELLED_REANALYSIS.
        """
        clean_id = cls.normalize_region_id(region_id)

        if clean_id not in DISTRICT_COORDINATES:
            raise DistrictIsolationError(
                f"District '{clean_id}' coordinates not registered in Open-Meteo adapter. "
                "District isolation prevents substituting adjacent district coordinates."
            )

        coords = DISTRICT_COORDINATES[clean_id]
        
        # Default to previous 30 days if unspecified
        end_d = end_date or (datetime.now(timezone.utc).date() - timedelta(days=5))
        start_d = start_date or (end_d - timedelta(days=29))

        if start_d > end_d:
            raise AdapterPayloadError(f"Start date {start_d} cannot be after end date {end_d}.")

        url = (
            f"{OPEN_METEO_ARCHIVE_URL}?latitude={coords['lat']}&longitude={coords['lng']}"
            f"&start_date={start_d.isoformat()}&end_date={end_d.isoformat()}"
            f"&daily=precipitation_sum&timezone=auto"
        )
        headers = {}
        if OPEN_METEO_API_KEY:
            headers["apikey"] = OPEN_METEO_API_KEY

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 429:
                    return AdapterResponse(
                        source_id=cls.METADATA.source_id,
                        region_id=clean_id,
                        status=SourceConnectionStatus.RATE_LIMITED,
                        dataset_type=cls.METADATA.dataset_type,
                        product_version=cls.METADATA.product_version,
                        units=cls.METADATA.default_units,
                        observations=[],
                        error_message="Open-Meteo API rate limit exceeded.",
                    )
                if resp.status_code != 200:
                    return AdapterResponse(
                        source_id=cls.METADATA.source_id,
                        region_id=clean_id,
                        status=SourceConnectionStatus.ERROR,
                        dataset_type=cls.METADATA.dataset_type,
                        product_version=cls.METADATA.product_version,
                        units=cls.METADATA.default_units,
                        observations=[],
                        error_message=f"Open-Meteo API returned HTTP {resp.status_code}.",
                    )
                data = resp.json()
        except httpx.TimeoutException:
            return AdapterResponse(
                source_id=cls.METADATA.source_id,
                region_id=clean_id,
                status=SourceConnectionStatus.TIMEOUT,
                dataset_type=cls.METADATA.dataset_type,
                product_version=cls.METADATA.product_version,
                units=cls.METADATA.default_units,
                observations=[],
                error_message=f"Request to Open-Meteo timed out after {timeout_seconds}s.",
            )
        except Exception as exc:
            return AdapterResponse(
                source_id=cls.METADATA.source_id,
                region_id=clean_id,
                status=SourceConnectionStatus.UNREACHABLE,
                dataset_type=cls.METADATA.dataset_type,
                product_version=cls.METADATA.product_version,
                units=cls.METADATA.default_units,
                observations=[],
                error_message=f"Open-Meteo connection failure: {exc}",
            )

        # Parse daily payload
        daily = data.get("daily", {})
        times = daily.get("time", [])
        precips = daily.get("precipitation_sum", [])

        observations: List[ObservationRecord] = []
        valid_cnt = 0
        missing_cnt = 0

        for t_str, p_val in zip(times, precips):
            obs_date = datetime.strptime(t_str, "%Y-%m-%d").date()
            val_clean, q_status, review_flag = cls.validate_rainfall_value(p_val)

            if q_status == QualityStatus.MISSING:
                missing_cnt += 1
            else:
                valid_cnt += 1

            observations.append(
                ObservationRecord(
                    date=obs_date,
                    rainfall_mm=val_clean,
                    raw_value=float(p_val) if p_val is not None else None,
                    raw_units="mm",
                    temporal_semantics="daily_accumulation",
                    interval_hours=24.0,
                    quality_status=q_status,
                    review_flag=review_flag,
                )
            )

        date_range = None
        if observations:
            date_range = {"start": str(observations[0].date), "end": str(observations[-1].date)}

        return AdapterResponse(
            source_id=cls.METADATA.source_id,
            region_id=clean_id,
            status=SourceConnectionStatus.CONNECTED,
            dataset_type=cls.METADATA.dataset_type,
            product_version=cls.METADATA.product_version,
            units=cls.METADATA.default_units,
            temporal_semantics="daily_accumulated_depth",
            is_rate_based=False,
            observations=observations,
            records_count=len(observations),
            valid_count=valid_cnt,
            missing_count=missing_cnt,
            date_range=date_range,
            metadata={
                "coordinates": coords,
                "model": "ECMWF ERA5 Reanalysis",
                "scientific_warning": "Modelled reanalysis data. Not ground truth gauge measurement.",
            },
        )

    @classmethod
    def validate_payload(cls, raw_payload: Any) -> Dict[str, Any]:
        """
        Validates Open-Meteo API JSON response structure.
        """
        if not isinstance(raw_payload, dict):
            raise AdapterPayloadError("Expected JSON dictionary from Open-Meteo.")

        if "daily" not in raw_payload:
            raise AdapterPayloadError("Missing 'daily' object in Open-Meteo payload.")

        daily = raw_payload["daily"]
        if "time" not in daily or "precipitation_sum" not in daily:
            raise AdapterPayloadError("Open-Meteo 'daily' must contain 'time' and 'precipitation_sum'.")

        if len(daily["time"]) != len(daily["precipitation_sum"]):
            raise AdapterPayloadError("Mismatch between 'time' and 'precipitation_sum' array lengths.")

        # Check negative values
        negatives = [v for v in daily["precipitation_sum"] if v is not None and float(v) < 0.0]
        if negatives:
            raise AdapterPayloadError(f"Payload contains {len(negatives)} negative rainfall values.")

        return {
            "total_days": len(daily["time"]),
            "time_range": {"start": daily["time"][0], "end": daily["time"][-1]} if daily["time"] else None,
            "units": raw_payload.get("daily_units", {}).get("precipitation_sum", "mm"),
        }
