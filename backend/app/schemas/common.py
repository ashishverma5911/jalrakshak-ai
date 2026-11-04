from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

# Data quality classification definitions:
# - 'provisional': Operational model-derived data not independently validated against ground observations.
# - 'verified': Pipeline-validated data that passed schema, physical bounds, and range verification.
#   Does not imply independent ground-truth station validation unless explicitly derived from calibrated observation products.
# - 'stale': Cached data exceeding active TTL where upstream retrieval failed.
# - 'missing': Explicitly null or missing data (< 83% coverage). Never silently imputed or coerced to zero.
# - 'simulated_demo': Synthetic reproducible demonstration data.
# - 'forecast': Predictive model estimate for future UTC hours or pure forecast days.
# - 'historical_model_estimate': Archived operational NWP model analysis for past UTC hours or pure past days.
# - 'live_model_estimate': Operational NWP model estimate for the current UTC hour.
# - 'mixed_model_estimate': Daily aggregate incorporating both past/live model analysis and forward forecast hours.
# - 'data_pending': Administrative region registered in spatial hierarchy but awaiting data ingestion.
DataQualityStatus = Literal[
    "verified",
    "provisional",
    "stale",
    "missing",
    "simulated_demo",
    "forecast",
    "observed_estimate",
    "data_pending",
    "historical_model_estimate",
    "live_model_estimate",
    "mixed_model_estimate",
]
DataMode = Literal[
    "LIVE_VERIFIED",
    "CACHED_VERIFIED",
    "DEMONSTRATION",
    "DATA_PENDING",
    "DATA_STALE",
    "LIVE_MODEL",
    "PROVIDER_ERROR",
    "MANUAL_UPLOAD",
    "FORECAST",
    "HISTORICAL_MODEL_ESTIMATE",
    "LIVE_MODEL_ESTIMATE",
    "MODEL_DERIVED",
    "CACHED",
]
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
    category: Literal[
        "observed_measurement",
        "derived_indicator",
        "validated_model",
        "official_alert",
        "model_derived",
    ]
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
