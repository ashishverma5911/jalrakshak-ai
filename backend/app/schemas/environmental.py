"""
Pydantic Schemas for Live Environmental Data Integration (Phase 3A)
Provides typed contracts for Open-Meteo NWP observations, forecasts,
freshness metrics, and district representative point telemetry.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from pydantic import BaseModel, Field

from .common import DataMode, DataQualityStatus


class HourlyEnvironmentalPoint(BaseModel):
    timestamp: str = Field(..., description="Observation or forecast ISO 8601 UTC timestamp")
    precipitation_mm: Optional[float] = Field(None, description="Precipitation accumulation in mm. None if missing.")
    temperature_2m_c: Optional[float] = Field(None, description="Air temperature at 2m in degrees Celsius")
    relative_humidity_pct: Optional[float] = Field(None, description="Relative humidity at 2m (0-100%)")
    wind_speed_10m_kmh: Optional[float] = Field(None, description="Wind speed at 10m in km/h")
    et0_evapotranspiration_mm: Optional[float] = Field(None, description="Reference FAO-56 evapotranspiration in mm")
    is_forecast: bool = Field(False, description="True if timestamp is in the future relative to retrieval")
    quality_status: DataQualityStatus = Field("observed_estimate", description="Validation and quality classification")


class DailyAggregatedPrecipitation(BaseModel):
    date: str = Field(..., description="Calendar date (YYYY-MM-DD)")
    rainfall_mm: Optional[float] = Field(None, description="Daily aggregated rainfall in mm. None if data missing.")
    is_forecast: bool = Field(False, description="True if aggregated from forecast hours")
    hours_recorded: int = Field(24, description="Number of valid hourly records in the day")
    hours_missing: int = Field(0, description="Number of missing hours in the day")
    quality_status: DataQualityStatus = Field("observed_estimate", description="Validation status")


class CurrentEnvironmentalConditions(BaseModel):
    timestamp: str
    temperature_2m_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_10m_kmh: Optional[float] = None
    precipitation_rate_mm_hr: Optional[float] = None
    et0_evapotranspiration_mm: Optional[float] = None
    is_forecast: bool = False
    condition_summary: Optional[str] = None


class EnvironmentalDataFreshness(BaseModel):
    latest_timestamp: str
    retrieval_timestamp: str
    data_age_hours: float
    cache_ttl_hours: float
    is_cached: bool = False
    is_stale: bool = False
    cache_expires_at: Optional[str] = None


class EnvironmentalLiveResponse(BaseModel):
    district_id: str
    district_name: str
    coordinates: Dict[str, float]
    spatial_representation: str = "representative_point_estimate"
    spatial_disclaimer: str = (
        "District centroid representative point estimate. "
        "Not a spatial polygon average over the entire district boundary."
    )
    provider: str = "Open-Meteo"
    model_name: str = "ECMWF IFS / GFS Blended Numerical Weather Prediction"
    attribution: str = "Weather data by Open-Meteo.com (CC-BY 4.0)"
    access_url: str = "https://open-meteo.com/"
    data_mode: str = Field("LIVE_MODEL", description="Data mode: LIVE_MODEL, CACHED, DATA_STALE, DATA_PENDING, PROVIDER_ERROR")
    freshness: EnvironmentalDataFreshness
    current_conditions: Optional[CurrentEnvironmentalConditions] = None
    hourly_series: List[HourlyEnvironmentalPoint] = Field(default_factory=list)
    daily_precipitation: List[DailyAggregatedPrecipitation] = Field(default_factory=list)
    provider_status: Optional[Dict[str, Any]] = None
    scientific_notes: List[str] = Field(default_factory=list)


class EnvironmentalRefreshResponse(BaseModel):
    success: bool
    district_id: str
    status: str
    message: str
    refreshed_at: str
    cache_expires_at: str
    data_mode: str


class EnvironmentalSystemStatusResponse(BaseModel):
    feature_flag_enabled: bool
    provider: str
    endpoint: str
    cache_ttl_hours: float
    stale_threshold_hours: float
    timeout_seconds: float
    max_retries: int
    active_cached_districts: List[str] = Field(default_factory=list)
    provider_connection_status: str
