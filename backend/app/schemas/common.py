from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

DataQualityStatus = Literal["verified", "provisional", "stale", "missing", "simulated_demo"]
HazardType = Literal["flood", "drought", "multi_hazard", "rainfall"]

class SourceMetadata(BaseModel):
    source_id: str
    source_name: str
    spatial_resolution: str
    temporal_resolution: str
    access_url: Optional[str] = None
    units: str
    retrieval_timestamp: Optional[str] = None

class RiskIndicator(BaseModel):
    indicator_id: str
    name: str
    value: float
    units: str
    category: Literal["observed_measurement", "derived_indicator", "validated_model", "official_alert"]
    calculation_window: str
    reference_baseline: str
    observation_timestamp: str
    retrieval_timestamp: str
    quality_status: DataQualityStatus
    methodology_version: str = "v1.0-transparent"
    limitations: str
    is_demo_data: bool = True

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
    risk_level: Literal["high", "moderate", "low", "nodata"]
    assessment_period: str
    generated_at: str
    is_demo_data: bool = True
    disclaimer: str = (
        "JalRakshak is a research decision-support prototype. "
        "Values represent derived transparent indicators, not official government warnings."
    )
    indicators: List[RiskIndicator]
    sources: List[SourceMetadata]
    scientific_notes: List[str]
