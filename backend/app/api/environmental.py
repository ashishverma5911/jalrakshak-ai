"""
JalRakshak AI — Environmental Data API Router (Phase 3A)
Provides live weather model telemetry, system freshness status, and on-demand refresh.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

from ..core.config import (
    LIVE_DATA_ENABLED,
    LIVE_CACHE_TTL_HOURS,
    LIVE_STALE_THRESHOLD_HOURS,
    OPEN_METEO_FORECAST_URL,
    LIVE_REQUEST_TIMEOUT_SECONDS,
    LIVE_MAX_RETRIES,
)
from ..schemas.environmental import (
    EnvironmentalLiveResponse,
    EnvironmentalRefreshResponse,
    EnvironmentalSystemStatusResponse,
)
from ..services.environmental_cache import EnvironmentalCacheService
from ..pipeline.adapters.open_meteo_forecast import OpenMeteoForecastAdapter

router = APIRouter(prefix="/environmental", tags=["Environmental Telemetry & Live Data"])


@router.get("/live", response_model=EnvironmentalLiveResponse)
async def get_live_environmental(
    location: str = Query("gorakhpur", description="Target district identifier (e.g. gorakhpur, mahoba, patna)"),
    refresh: bool = Query(False, description="Force refresh from external provider")
) -> EnvironmentalLiveResponse:
    """
    Retrieves near-current weather model observations and 7-day NWP forecasts
    from the Open-Meteo forecast API for the target district centroid.
    Applies lazy request-triggered caching with 3-hour TTL and 24-hour stale fallback.
    """
    try:
        clean_id = OpenMeteoForecastAdapter.normalize_region_id(location)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If live data is disabled by feature flag and no outbound fetch is allowed:
    if not LIVE_DATA_ENABLED:
        cached = EnvironmentalCacheService.get_cached_district_data(clean_id)
        coords = OpenMeteoForecastAdapter.resolve_district_coordinates(clean_id)
        district_name = coords.get("name", clean_id.capitalize())
        now_utc = datetime.now(timezone.utc)

        if cached:
            return EnvironmentalCacheService._build_response_from_cache(
                cached_entry=cached,
                district_id=clean_id,
                district_name=district_name,
                coords=coords,
                now_utc=now_utc,
                data_mode="CACHED",
                is_cached=True,
                is_stale=False,
                provider_status={
                    "status": "cached_offline",
                    "info": "LIVE_DATA_ENABLED is False; serving local cached telemetry without outbound calls."
                }
            )
        else:
            return EnvironmentalCacheService._build_empty_pending_response(
                district_id=clean_id,
                district_name=district_name,
                coords=coords,
                now_utc=now_utc,
                error_message=(
                    "Live environmental data ingestion is currently disabled (LIVE_DATA_ENABLED=false). "
                    "Set LIVE_DATA_ENABLED=true in backend environment to enable external fetches."
                )
            )

    return await EnvironmentalCacheService.get_district_environmental_data(clean_id, force_refresh=refresh)


@router.get("/status", response_model=EnvironmentalSystemStatusResponse)
def get_environmental_status() -> EnvironmentalSystemStatusResponse:
    """
    Returns live ingestion pipeline configuration, cached districts list,
    and provider operational status.
    """
    cached_districts = EnvironmentalCacheService.list_cached_districts()
    status = "online" if LIVE_DATA_ENABLED else "disabled_by_config"

    return EnvironmentalSystemStatusResponse(
        feature_flag_enabled=LIVE_DATA_ENABLED,
        provider="Open-Meteo Weather Forecast (NWP)",
        endpoint=OPEN_METEO_FORECAST_URL,
        cache_ttl_hours=LIVE_CACHE_TTL_HOURS,
        stale_threshold_hours=LIVE_STALE_THRESHOLD_HOURS,
        timeout_seconds=LIVE_REQUEST_TIMEOUT_SECONDS,
        max_retries=LIVE_MAX_RETRIES,
        active_cached_districts=cached_districts,
        provider_connection_status=status,
    )


@router.post("/refresh", response_model=EnvironmentalRefreshResponse)
async def refresh_environmental_data(
    location: str = Query("gorakhpur", description="Target district identifier")
) -> EnvironmentalRefreshResponse:
    """
    Explicitly triggers a refresh of external NWP model telemetry for a district,
    subject to rate-limit cooldown (30s) and feature flag status.
    """
    clean_id = OpenMeteoForecastAdapter.normalize_region_id(location)
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    if not LIVE_DATA_ENABLED:
        return EnvironmentalRefreshResponse(
            success=False,
            district_id=clean_id,
            status="disabled",
            message="Live external data ingestion is disabled via LIVE_DATA_ENABLED configuration.",
            refreshed_at=now_iso,
            cache_expires_at=now_iso,
            data_mode="DATA_PENDING",
        )

    res = await EnvironmentalCacheService.get_district_environmental_data(clean_id, force_refresh=True)
    is_success = res.data_mode in ["LIVE_MODEL", "CACHED"]

    return EnvironmentalRefreshResponse(
        success=is_success,
        district_id=clean_id,
        status="refreshed" if is_success else "provider_error",
        message="Live telemetry refreshed from Open-Meteo." if is_success else "Provider unavailable; fallback active.",
        refreshed_at=res.freshness.retrieval_timestamp,
        cache_expires_at=res.freshness.cache_expires_at or now_iso,
        data_mode=res.data_mode,
    )
