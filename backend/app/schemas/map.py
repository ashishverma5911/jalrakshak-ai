from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DistrictMapFeature(BaseModel):
    district_id: str
    name: str
    hindi_name: str
    latitude: float
    longitude: float
    elevation_m: float
    river_basin: str
    is_pilot: bool
    flood_risk: str
    drought_risk: str
    rainfall_anomaly_pct: float
    spi3: float
    observation_window: str = "Past 30-day window"
    source_timestamp: str = "28 Oct 2026, 10:30 AM"
    data_quality: str = "demo_reference"
    geometry_type: str = "centroid_point"
    geometry_available: bool = False
    last_updated: str

class MapLayersResponse(BaseModel):
    layer_type: str
    generated_at: str
    is_demo_data: bool = True
    geometry_status: str = "centroid_coordinates_only"
    geometry_available: bool = False
    geometry_disclaimer: str = (
        "District centroid coordinates provided under WGS84 (EPSG:4326). "
        "Validated district polygon boundaries are unintegrated in prototype. "
        "Point markers represent regional representative centers and do not imply district-wide uniform ground truth."
    )
    districts: List[DistrictMapFeature]
    metadata: Dict[str, Any]
