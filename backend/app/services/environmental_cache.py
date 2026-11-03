"""
JalRakshak AI — Environmental Data Cache & Ingestion Service (Phase 3A)
Provides request-triggered lazy caching, concurrency deduplication,
graceful stale fallback, and zero-cost free-tier resilience for Open-Meteo data.

Invariants:
- Cache-first retrieval with 3-hour TTL and 24-hour stale threshold.
- Concurrency deduplication (asyncio.Lock per district) avoids dogpiling Open-Meteo API.
- Request-triggered lazy refresh (no always-running daemon threads or background workers).
- Never returns fabricated demo fixtures as live observations.
- Never converts missing observations into zeros.
- Graceful degradation: returns CACHED or DATA_STALE on provider outage; DATA_PENDING if no cache.
"""

import os
import json
import asyncio
import logging
import weakref
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ..core.config import (
    DATA_DIR,
    LIVE_DATA_ENABLED,
    LIVE_CACHE_TTL_HOURS,
    LIVE_STALE_THRESHOLD_HOURS,
    OPEN_METEO_FORECAST_URL,
    LIVE_REQUEST_TIMEOUT_SECONDS,
    LIVE_MAX_RETRIES,
)
from ..pipeline.adapters.open_meteo_forecast import OpenMeteoForecastAdapter, DISTRICT_COORDINATES
from ..pipeline.adapters.base import (
    SourceConnectionStatus,
    AdapterConnectionError,
    AdapterRateLimitError,
    AdapterPayloadError,
    DistrictIsolationError,
)
from ..schemas.environmental import (
    EnvironmentalLiveResponse,
    EnvironmentalDataFreshness,
    CurrentEnvironmentalConditions,
    HourlyEnvironmentalPoint,
    DailyAggregatedPrecipitation,
)

logger = logging.getLogger("jalrakshak.services.environmental_cache")

# Persistent disk cache directory
CACHE_DIR = DATA_DIR / "cache"
CACHE_FILE = CACHE_DIR / "environmental_forecast_cache.json"

# In-memory storage and synchronization locks
_memory_cache: Dict[str, Dict[str, Any]] = {}
_last_refresh_timestamps: Dict[str, datetime] = {}

# Event-loop-scoped lock registries to prevent cross-loop contamination and lifecycle leaks
_provider_locks_by_loop: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
_district_locks_by_loop: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()

# Global rate limit circuit breaker state (zero cost, in-memory)
_provider_cooldown_until: Optional[datetime] = None
_provider_cooldown_reason: Optional[str] = None
_negative_cache: Dict[str, datetime] = {}


class EnvironmentalCacheService:
    """
    Manages operational weather model cache lifecycle and resilience for all districts.
    """

    @classmethod
    def _ensure_cache_dir(cls) -> None:
        """Ensures cache directory exists."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _load_disk_cache(cls) -> None:
        """Loads persistent cache from disk on cold start."""
        global _memory_cache
        if not _memory_cache and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _memory_cache = json.load(f)
                    logger.info(f"Loaded {len(_memory_cache)} district forecast caches from disk.")
            except Exception as e:
                logger.warning(f"Could not read disk cache: {e}; starting with empty in-memory cache.")
                _memory_cache = {}

    @classmethod
    def _save_disk_cache(cls) -> None:
        """Flushes in-memory cache safely to disk with atomic write."""
        cls._ensure_cache_dir()
        temp_file = CACHE_DIR / f"temp_{os.getpid()}_cache.json"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(_memory_cache, f, default=str)
            temp_file.replace(CACHE_FILE)
        except Exception as e:
            logger.warning(f"Failed to persist environmental cache to disk: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    @classmethod
    def _get_provider_lock(cls) -> asyncio.Lock:
        """Retrieves or initializes the global provider lock scoped to the active event loop."""
        loop = asyncio.get_running_loop()
        lock = _provider_locks_by_loop.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            _provider_locks_by_loop[loop] = lock
        return lock

    @classmethod
    def _get_district_lock(cls, district_id: str) -> asyncio.Lock:
        """Retrieves or initializes a district concurrency lock scoped to the active event loop."""
        loop = asyncio.get_running_loop()
        locks_for_loop = _district_locks_by_loop.get(loop)
        if locks_for_loop is None:
            locks_for_loop = {}
            _district_locks_by_loop[loop] = locks_for_loop
        if district_id not in locks_for_loop:
            locks_for_loop[district_id] = asyncio.Lock()
        return locks_for_loop[district_id]

    @classmethod
    def get_cached_district_data(cls, district_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw cached entry for district if present."""
        cls._load_disk_cache()
        clean_id = OpenMeteoForecastAdapter.normalize_region_id(district_id)
        return _memory_cache.get(clean_id)

    @classmethod
    def list_cached_districts(cls) -> List[str]:
        """Returns list of currently cached district IDs."""
        cls._load_disk_cache()
        return list(_memory_cache.keys())

    @classmethod
    def is_provider_in_cooldown(cls) -> bool:
        """Returns True if upstream provider is currently in rate limit cooldown."""
        global _provider_cooldown_until
        if _provider_cooldown_until is None:
            return False
        now_utc = datetime.now(timezone.utc)
        if now_utc >= _provider_cooldown_until:
            _provider_cooldown_until = None
            return False
        return True

    @classmethod
    def get_cooldown_remaining_seconds(cls) -> float:
        """Returns remaining seconds for active provider cooldown, or 0.0."""
        global _provider_cooldown_until
        if not cls.is_provider_in_cooldown():
            return 0.0
        now_utc = datetime.now(timezone.utc)
        return max(0.0, round((_provider_cooldown_until - now_utc).total_seconds(), 1))

    @classmethod
    def get_cooldown_reason(cls) -> Optional[str]:
        """Returns the reason recorded for active provider cooldown."""
        if cls.is_provider_in_cooldown():
            return _provider_cooldown_reason
        return None

    @classmethod
    def set_provider_cooldown(cls, seconds: Optional[int] = None, reason: Optional[str] = None) -> float:
        """
        Activates global provider cooldown.
        Applies conservative bounded fallback (30s to 300s, default 60s).
        """
        global _provider_cooldown_until, _provider_cooldown_reason
        cooldown_sec = seconds if seconds is not None and seconds > 0 else 60
        cooldown_sec = max(30, min(300, cooldown_sec))
        now_utc = datetime.now(timezone.utc)
        _provider_cooldown_until = now_utc + timedelta(seconds=cooldown_sec)
        _provider_cooldown_reason = reason or "Open-Meteo HTTP 429 Rate Limit"
        logger.warning(
            f"Global provider cooldown activated for {cooldown_sec}s until {_provider_cooldown_until.isoformat()}. "
            f"Reason: {_provider_cooldown_reason}"
        )
        return float(cooldown_sec)

    @classmethod
    def reset_cooldown(cls) -> None:
        """Resets provider cooldown and negative cache (for testing/recovery)."""
        global _provider_cooldown_until, _provider_cooldown_reason, _negative_cache
        _provider_cooldown_until = None
        _provider_cooldown_reason = None
        _negative_cache.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clears memory, locks, and disk cache (primarily for test isolation)."""
        global _memory_cache
        _memory_cache.clear()
        _provider_locks_by_loop.clear()
        _district_locks_by_loop.clear()
        cls.reset_cooldown()
        if CACHE_FILE.exists():
            try:
                CACHE_FILE.unlink()
            except Exception:
                pass

    @classmethod
    async def get_district_environmental_data(
        cls,
        district_id: str,
        force_refresh: bool = False,
    ) -> EnvironmentalLiveResponse:
        """
        Retrieves live or cached environmental weather model data for a district.
        Applies cache-first lookup, bounded external HTTP fetching, concurrency lock,
        global HTTP 429 cooldown protection, negative caching,
        and honest fallback to STALE or DATA_PENDING on provider outages.
        """
        clean_id = OpenMeteoForecastAdapter.normalize_region_id(district_id)
        coords = OpenMeteoForecastAdapter.resolve_district_coordinates(clean_id)
        district_name = coords.get("name", clean_id.replace("district-", "").capitalize())

        now_utc = datetime.now(timezone.utc)
        ttl_delta = timedelta(hours=LIVE_CACHE_TTL_HOURS)
        stale_delta = timedelta(hours=LIVE_STALE_THRESHOLD_HOURS)

        cached_entry = cls.get_cached_district_data(clean_id)

        # 1. Check if cache is fresh and force_refresh is not requested
        if cached_entry and not force_refresh:
            try:
                retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                if (now_utc - retrieved_at) <= ttl_delta:
                    # Fresh cache hit
                    return cls._build_response_from_cache(
                        cached_entry=cached_entry,
                        district_id=clean_id,
                        district_name=district_name,
                        coords=coords,
                        now_utc=now_utc,
                        data_mode="LIVE_MODEL",
                        is_cached=True,
                        is_stale=False,
                    )
            except Exception as e:
                logger.warning(f"Error parsing cached timestamp for {clean_id}: {e}")

        # 2. Check global provider rate limit cooldown (fast path: suppress outbound calls)
        if cls.is_provider_in_cooldown():
            rem_sec = cls.get_cooldown_remaining_seconds()
            reason = cls.get_cooldown_reason() or "HTTP 429 Rate Limit"
            logger.info(
                f"Global provider cooldown active ({rem_sec:.1f}s remaining). "
                f"Suppressing outbound call for {clean_id}."
            )
            if cached_entry:
                try:
                    retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                    age_delta = now_utc - retrieved_at
                    if age_delta <= stale_delta:
                        data_mode = "CACHED" if age_delta <= ttl_delta else "DATA_STALE"
                        return cls._build_response_from_cache(
                            cached_entry=cached_entry,
                            district_id=clean_id,
                            district_name=district_name,
                            coords=coords,
                            now_utc=now_utc,
                            data_mode=data_mode,
                            is_cached=True,
                            is_stale=age_delta > ttl_delta,
                            provider_status={
                                "status": "provider_cooldown_active",
                                "cooldown_remaining_seconds": rem_sec,
                                "error": f"Upstream provider rate limited: {reason}",
                                "notice": f"Provider cooldown active ({round(rem_sec)}s remaining). Displaying cached telemetry.",
                            },
                        )
                except Exception as e:
                    logger.error(f"Error checking cached entry during cooldown: {e}")

            # No cache or cache > 24 hours
            return cls._build_empty_pending_response(
                district_id=clean_id,
                district_name=district_name,
                coords=coords,
                now_utc=now_utc,
                error_message=(
                    f"Open-Meteo rate limit cooldown active ({round(rem_sec)}s remaining). "
                    "Outbound requests suppressed to protect quota. Telemetry pending."
                ),
                provider_status_extra={
                    "cooldown_active": True,
                    "cooldown_remaining_seconds": rem_sec,
                    "reason": reason,
                },
            )

        # 3. Check negative cache for this district (suppress repeat failures)
        neg_until = _negative_cache.get(clean_id)
        if neg_until and now_utc < neg_until:
            rem_neg = round((neg_until - now_utc).total_seconds(), 1)
            logger.info(f"Negative cache active for {clean_id} for {rem_neg}s; suppressing outbound call.")
            if cached_entry:
                try:
                    retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                    if (now_utc - retrieved_at) <= stale_delta:
                        return cls._build_response_from_cache(
                            cached_entry=cached_entry,
                            district_id=clean_id,
                            district_name=district_name,
                            coords=coords,
                            now_utc=now_utc,
                            data_mode="DATA_STALE",
                            is_cached=True,
                            is_stale=True,
                            provider_status={
                                "status": "negative_cached",
                                "error": "Recent provider error. Retries suppressed.",
                                "negative_cache_remaining_seconds": rem_neg,
                            },
                        )
                except Exception:
                    pass
            return cls._build_empty_pending_response(
                district_id=clean_id,
                district_name=district_name,
                coords=coords,
                now_utc=now_utc,
                error_message=f"Recent provider failure for {district_name}. Negative cache active for {round(rem_neg)}s.",
            )

        # 4. Acquire per-district lock to deduplicate concurrent requests
        lock = cls._get_district_lock(clean_id)
        async with lock:
            # Double check cache inside lock: another request might have refreshed it
            if not force_refresh:
                cached_entry = cls.get_cached_district_data(clean_id)
                if cached_entry:
                    try:
                        retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                        if (now_utc - retrieved_at) <= ttl_delta:
                            return cls._build_response_from_cache(
                                cached_entry=cached_entry,
                                district_id=clean_id,
                                district_name=district_name,
                                coords=coords,
                                now_utc=now_utc,
                                data_mode="LIVE_MODEL",
                                is_cached=True,
                                is_stale=False,
                            )
                    except Exception:
                        pass

            # Anti-spam cooldown for force_refresh (max 1 refresh every 30 seconds per district)
            last_ref = _last_refresh_timestamps.get(clean_id)
            if force_refresh and last_ref and (now_utc - last_ref).total_seconds() < 30.0:
                if cached_entry:
                    return cls._build_response_from_cache(
                        cached_entry=cached_entry,
                        district_id=clean_id,
                        district_name=district_name,
                        coords=coords,
                        now_utc=now_utc,
                        data_mode="CACHED",
                        is_cached=True,
                        is_stale=False,
                        provider_status={"info": "Refresh rate limited. Using fresh cached telemetry."},
                    )

            # Re-check global provider cooldown inside lock
            if cls.is_provider_in_cooldown():
                rem_sec = cls.get_cooldown_remaining_seconds()
                reason = cls.get_cooldown_reason() or "HTTP 429 Rate Limit"
                if cached_entry:
                    try:
                        retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                        if (now_utc - retrieved_at) <= stale_delta:
                            return cls._build_response_from_cache(
                                cached_entry=cached_entry,
                                district_id=clean_id,
                                district_name=district_name,
                                coords=coords,
                                now_utc=now_utc,
                                data_mode="DATA_STALE",
                                is_cached=True,
                                is_stale=True,
                                provider_status={
                                    "status": "provider_cooldown_active",
                                    "cooldown_remaining_seconds": rem_sec,
                                    "error": f"Upstream provider rate limited: {reason}",
                                },
                            )
                    except Exception:
                        pass
                return cls._build_empty_pending_response(
                    district_id=clean_id,
                    district_name=district_name,
                    coords=coords,
                    now_utc=now_utc,
                    error_message=f"Open-Meteo cooldown active ({round(rem_sec)}s remaining). Telemetry pending.",
                    provider_status_extra={
                        "cooldown_active": True,
                        "cooldown_remaining_seconds": rem_sec,
                        "reason": reason,
                    },
                )

            # 5. Fetch from Open-Meteo external provider
            provider_error_msg = None
            rate_limit_hit = False
            cooldown_sec_applied = 60.0

            try:
                logger.info(f"Fetching live forecast for {clean_id} from Open-Meteo...")
                # Cross-district lock ensures multiple districts don't burst simultaneous outbound calls
                provider_lock = cls._get_provider_lock()
                async with provider_lock:
                    # Critical Double-Check: Another concurrent request may have tripped 429
                    # while this request was waiting to acquire the provider lock!
                    if cls.is_provider_in_cooldown():
                        rem_sec = cls.get_cooldown_remaining_seconds()
                        reason = cls.get_cooldown_reason() or "HTTP 429 Rate Limit"
                        logger.info(
                            f"Provider cooldown detected after acquiring provider lock for {clean_id} "
                            f"({rem_sec:.1f}s remaining). Suppressing outbound call."
                        )
                        if cached_entry:
                            try:
                                retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                                if (now_utc - retrieved_at) <= stale_delta:
                                    return cls._build_response_from_cache(
                                        cached_entry=cached_entry,
                                        district_id=clean_id,
                                        district_name=district_name,
                                        coords=coords,
                                        now_utc=now_utc,
                                        data_mode="DATA_STALE",
                                        is_cached=True,
                                        is_stale=True,
                                        provider_status={
                                            "status": "provider_cooldown_active",
                                            "cooldown_remaining_seconds": rem_sec,
                                            "error": f"Upstream provider rate limited: {reason}",
                                            "notice": f"Provider cooldown active ({round(rem_sec)}s remaining). Displaying cached telemetry.",
                                        },
                                    )
                            except Exception:
                                pass

                        return cls._build_empty_pending_response(
                            district_id=clean_id,
                            district_name=district_name,
                            coords=coords,
                            now_utc=now_utc,
                            error_message=(
                                f"Open-Meteo rate limit cooldown active ({round(rem_sec)}s remaining). "
                                "Outbound requests suppressed to protect quota. Telemetry pending."
                            ),
                            provider_status_extra={
                                "cooldown_active": True,
                                "cooldown_remaining_seconds": rem_sec,
                                "reason": reason,
                            },
                        )

                    # Also re-check negative cache inside provider lock
                    neg_until = _negative_cache.get(clean_id)
                    if neg_until and now_utc < neg_until:
                        rem_neg = round((neg_until - now_utc).total_seconds(), 1)
                        if cached_entry:
                            try:
                                retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                                if (now_utc - retrieved_at) <= stale_delta:
                                    return cls._build_response_from_cache(
                                        cached_entry=cached_entry,
                                        district_id=clean_id,
                                        district_name=district_name,
                                        coords=coords,
                                        now_utc=now_utc,
                                        data_mode="DATA_STALE",
                                        is_cached=True,
                                        is_stale=True,
                                        provider_status={
                                            "status": "negative_cached",
                                            "error": "Recent provider error. Retries suppressed.",
                                            "negative_cache_remaining_seconds": rem_neg,
                                        },
                                    )
                            except Exception:
                                pass
                        return cls._build_empty_pending_response(
                            district_id=clean_id,
                            district_name=district_name,
                            coords=coords,
                            now_utc=now_utc,
                            error_message=f"Recent provider failure for {district_name}. Negative cache active for {round(rem_neg)}s.",
                        )

                    raw_payload = await OpenMeteoForecastAdapter.fetch_forecast_raw(
                        lat=coords["lat"],
                        lng=coords["lng"],
                        past_days=7,
                        forecast_days=7,
                    )

                parsed_data = OpenMeteoForecastAdapter.validate_and_parse_hourly(
                    payload=raw_payload,
                    district_id=clean_id,
                    coords=coords,
                    retrieval_time=now_utc,
                )

                daily_data = OpenMeteoForecastAdapter.aggregate_hourly_to_daily(
                    parsed_data["records"]
                )

                # Store in cache
                cache_payload = {
                    "district_id": clean_id,
                    "retrieval_timestamp": now_utc.isoformat(),
                    "expires_at": (now_utc + ttl_delta).isoformat(),
                    "coordinates": coords,
                    "hourly_records": [
                        {k: v for k, v in r.items() if k != "dt"}
                        for r in parsed_data["records"]
                    ],
                    "daily_records": daily_data,
                    "raw_metadata": {
                        "elevation": raw_payload.get("elevation"),
                        "timezone": raw_payload.get("timezone", "UTC"),
                        "generationtime_ms": raw_payload.get("generationtime_ms"),
                    },
                }

                _memory_cache[clean_id] = cache_payload
                _last_refresh_timestamps[clean_id] = now_utc
                _negative_cache.pop(clean_id, None)
                cls._save_disk_cache()

                logger.info(f"Successfully refreshed and cached live forecast for {clean_id}.")

                return cls._build_response_from_cache(
                    cached_entry=cache_payload,
                    district_id=clean_id,
                    district_name=district_name,
                    coords=coords,
                    now_utc=now_utc,
                    data_mode="LIVE_MODEL",
                    is_cached=False,
                    is_stale=False,
                )

            except AdapterRateLimitError as rle:
                rate_limit_hit = True
                provider_error_msg = str(rle)
                cooldown_sec_applied = cls.set_provider_cooldown(
                    seconds=rle.retry_after_seconds,
                    reason=rle.reason or "Open-Meteo rate limit exceeded (HTTP 429)",
                )
                _negative_cache[clean_id] = _provider_cooldown_until
                logger.warning(
                    f"Open-Meteo HTTP 429 encountered for {clean_id}. "
                    f"Activated global cooldown for {cooldown_sec_applied}s."
                )

            except Exception as exc:
                provider_error_msg = str(exc)
                logger.warning(f"Live provider fetch failed for {clean_id}: {exc}")
                _negative_cache[clean_id] = now_utc + timedelta(seconds=30)

            # 6. Handle provider failure: Graceful Fallback
            if cached_entry:
                try:
                    retrieved_at = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
                    age_delta = now_utc - retrieved_at

                    if age_delta <= stale_delta:
                        # Stale cache fallback (between 3h and 24h old)
                        data_mode = "CACHED" if age_delta <= ttl_delta else "DATA_STALE"
                        is_stale = age_delta > ttl_delta

                        notice = (
                            f"Open-Meteo rate limited (cooldown {round(cooldown_sec_applied)}s). Displaying cached telemetry."
                            if rate_limit_hit
                            else "Open-Meteo unreachable. Displaying cached environmental telemetry."
                        )

                        return cls._build_response_from_cache(
                            cached_entry=cached_entry,
                            district_id=clean_id,
                            district_name=district_name,
                            coords=coords,
                            now_utc=now_utc,
                            data_mode=data_mode,
                            is_cached=True,
                            is_stale=is_stale,
                            provider_status={
                                "status": "provider_error_using_cache",
                                "error": provider_error_msg,
                                "notice": notice,
                                "cooldown_active": rate_limit_hit,
                                "cooldown_remaining_seconds": cls.get_cooldown_remaining_seconds() if rate_limit_hit else 0.0,
                            },
                        )
                except Exception as parse_err:
                    logger.error(f"Failed to evaluate stale cache fallback: {parse_err}")

            # 7. No cache available or cache > 24 hours old: DATA_PENDING with honest error
            extra_status = {}
            if rate_limit_hit:
                extra_status = {
                    "cooldown_active": True,
                    "cooldown_remaining_seconds": cls.get_cooldown_remaining_seconds(),
                }
            return cls._build_empty_pending_response(
                district_id=clean_id,
                district_name=district_name,
                coords=coords,
                now_utc=now_utc,
                error_message=provider_error_msg or "Environmental data pending initialization.",
                provider_status_extra=extra_status,
            )

    @classmethod
    def _build_response_from_cache(
        cls,
        cached_entry: Dict[str, Any],
        district_id: str,
        district_name: str,
        coords: Dict[str, Any],
        now_utc: datetime,
        data_mode: str,
        is_cached: bool,
        is_stale: bool,
        provider_status: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentalLiveResponse:
        """Constructs typed EnvironmentalLiveResponse from cached structure."""
        retrieval_dt = datetime.fromisoformat(cached_entry["retrieval_timestamp"])
        data_age_hours = round((now_utc - retrieval_dt).total_seconds() / 3600.0, 2)
        ttl_hours = LIVE_CACHE_TTL_HOURS
        expires_at = (retrieval_dt + timedelta(hours=ttl_hours)).isoformat()

        hourly_records = cached_entry.get("hourly_records", [])
        daily_records = cached_entry.get("daily_records", [])

        # Parse current conditions from the latest non-forecast or nearest hour
        current_conditions = None
        latest_timestamp = now_utc.isoformat()

        if hourly_records:
            # Find the most recent record with timestamp <= now_utc, or the first record
            past_records = [r for r in hourly_records if datetime.fromisoformat(r["timestamp"]) <= now_utc]
            target_pt = past_records[-1] if past_records else hourly_records[0]
            latest_timestamp = target_pt["timestamp"]

            summary_parts = []
            if target_pt.get("temperature_2m_c") is not None:
                summary_parts.append(f"{target_pt['temperature_2m_c']}°C")
            if target_pt.get("relative_humidity_pct") is not None:
                summary_parts.append(f"{target_pt['relative_humidity_pct']}% RH")
            if target_pt.get("precipitation_mm") is not None and target_pt["precipitation_mm"] > 0.0:
                summary_parts.append(f"{target_pt['precipitation_mm']} mm/hr rain")
            elif target_pt.get("precipitation_mm") == 0.0:
                summary_parts.append("No rain")

            current_conditions = CurrentEnvironmentalConditions(
                timestamp=target_pt["timestamp"],
                temperature_2m_c=target_pt.get("temperature_2m_c"),
                relative_humidity_pct=target_pt.get("relative_humidity_pct"),
                wind_speed_10m_kmh=target_pt.get("wind_speed_10m_kmh"),
                precipitation_rate_mm_hr=target_pt.get("precipitation_mm"),
                et0_evapotranspiration_mm=target_pt.get("et0_evapotranspiration_mm"),
                is_forecast=target_pt.get("is_forecast", False),
                condition_summary=" | ".join(summary_parts) if summary_parts else "Nominal conditions",
            )

        freshness = EnvironmentalDataFreshness(
            latest_timestamp=latest_timestamp,
            retrieval_timestamp=cached_entry["retrieval_timestamp"],
            data_age_hours=data_age_hours,
            cache_ttl_hours=ttl_hours,
            is_cached=is_cached,
            is_stale=is_stale,
            cache_expires_at=expires_at,
        )

        hourly_pts = [
            HourlyEnvironmentalPoint(
                timestamp=r["timestamp"],
                precipitation_mm=r.get("precipitation_mm"),
                temperature_2m_c=r.get("temperature_2m_c"),
                relative_humidity_pct=r.get("relative_humidity_pct"),
                wind_speed_10m_kmh=r.get("wind_speed_10m_kmh"),
                et0_evapotranspiration_mm=r.get("et0_evapotranspiration_mm"),
                is_forecast=r.get("is_forecast", False),
                quality_status=r.get("quality_status", "observed_estimate"),
            )
            for r in hourly_records
        ]

        daily_pts = [
            DailyAggregatedPrecipitation(
                date=d["date"],
                rainfall_mm=d.get("rainfall_mm"),
                is_forecast=d.get("is_forecast", False),
                hours_recorded=d.get("hours_recorded", 24),
                hours_missing=d.get("hours_missing", 0),
                quality_status=d.get("quality_status", "observed_estimate"),
            )
            for d in daily_records
        ]

        notes = [
            "Source: Open-Meteo ECMWF IFS / GFS Blended Numerical Weather Prediction.",
            "District representative-point estimate at district centroid coordinates. Not a spatial polygon average.",
            "Precipitation metrics distinguish model-derived near-current estimates from future forecasts.",
            "Missing observations are retained as null; never silently imputed or coerced to zero.",
        ]
        if is_stale:
            notes.append(f"Notice: Data exceeds {LIVE_CACHE_TTL_HOURS}h freshness threshold. Displaying cached telemetry.")

        return EnvironmentalLiveResponse(
            district_id=district_id,
            district_name=district_name,
            coordinates={"lat": coords["lat"], "lng": coords["lng"]},
            spatial_representation="representative_point_estimate",
            provider="Open-Meteo",
            model_name="ECMWF IFS / GFS Blended Numerical Weather Prediction",
            attribution="Weather data by Open-Meteo.com (CC-BY 4.0)",
            access_url="https://open-meteo.com/",
            data_mode=data_mode,
            freshness=freshness,
            current_conditions=current_conditions,
            hourly_series=hourly_pts,
            daily_precipitation=daily_pts,
            provider_status=provider_status,
            scientific_notes=notes,
        )

    @classmethod
    def _build_empty_pending_response(
        cls,
        district_id: str,
        district_name: str,
        coords: Dict[str, Any],
        now_utc: datetime,
        error_message: str,
        provider_status_extra: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentalLiveResponse:
        """Constructs honest DATA_PENDING response when no telemetry exists or provider is down."""
        freshness = EnvironmentalDataFreshness(
            latest_timestamp=now_utc.isoformat(),
            retrieval_timestamp=now_utc.isoformat(),
            data_age_hours=0.0,
            cache_ttl_hours=LIVE_CACHE_TTL_HOURS,
            is_cached=False,
            is_stale=True,
        )

        status_dict = {
            "status": "data_pending",
            "error": error_message,
            "message": "Live telemetry is currently pending or unreachable. No fabricated values generated.",
        }
        if provider_status_extra:
            status_dict.update(provider_status_extra)

        return EnvironmentalLiveResponse(
            district_id=district_id,
            district_name=district_name,
            coordinates={"lat": coords["lat"], "lng": coords["lng"]},
            spatial_representation="representative_point_estimate",
            provider="Open-Meteo",
            model_name="ECMWF IFS / GFS Blended Numerical Weather Prediction",
            attribution="Weather data by Open-Meteo.com (CC-BY 4.0)",
            access_url="https://open-meteo.com/",
            data_mode="DATA_PENDING",
            freshness=freshness,
            current_conditions=None,
            hourly_series=[],
            daily_precipitation=[],
            provider_status=status_dict,
            scientific_notes=[
                "Live observations are currently pending or provider is unreachable.",
                "In accordance with JalRakshak scientific integrity rules, missing observations remain null.",
            ],
        )
