from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

DataQualityStatus = Literal["verified", "provisional", "stale", "missing", "simulated_demo", "forecast", "observed_estimate", "data_pending"]
DataMode = Literal["LIVE_VERIFIED", "CACHED_VERIFIED", "DEMONSTRATION", "DATA_PENDING", "DATA_STALE", "LIVE_MODEL", "PROVIDER_ERROR", "MANUAL_UPLOAD", "FORECAST"]
HazardType = Literal["flood", "drought", "multi_hazard", "rainfall"]

class SourceMetadata(BaseModel):
    source_id: str
    source_name: str
    spatial_resolution: str
    temporal_resolution: str
    dataset_version: Optional[str] = "v2.0"
    access_url: Optional[str] = None
    units: str
    data_mode: DataMode = "CACHED_VERIFIED"
    retrieval_timestamp: Optional[str] = None
    license: Optional[str] = None

class RiskIndicator(BaseModel):
    indicator_id: str
    name: str
    value: Optional[float] = None
    units: str
    category: Literal["observed_measurement", "derived_indicator", "validated_model", "official_alert"]
    calculation_window: str
    reference_baseline: str
    observation_timestamp: str
    retrieval_timestamp: str
    quality_status: DataQualityStatus
    data_mode: DataMode = "CACHED_VERIFIED"
    dataset_version: str = "v2.0"
    spatial_resolution: str = "0.05° (~5 km)"
    methodology_version: str = "v2.0-scientific"
    limitations: str
    is_demo_data: bool = False
    is_data_available: bool = True

class LocationReference(BaseModel):
    location_id: str
    name: str
    hindi_name: str
    latitude: float
    longitude: float
    elevation_m: float
    river_basin: str
    region: str
    is_pilot: bool = False

class HazardAssessmentResponse(BaseModel):
    location: LocationReference
    hazard: HazardType
    risk_level: Literal["high", "moderate", "low", "nodata", "pending"]
    assessment_period: str
    generated_at: str
    data_mode: DataMode = "CACHED_VERIFIED"
    is_demo_data: bool = False
    is_data_available: bool = True
    disclaimer: str = (
        "JalRakshak is a research decision-support prototype. "
        "Values represent derived transparent indicators, not official government warnings."
    )
    indicators: List[RiskIndicator]
    sources: List[SourceMetadata]
    scientific_notes: List[str]
