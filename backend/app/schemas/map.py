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
    rainfall_anomaly_pct: Optional[float] = None
    spi3: Optional[float] = None
    observation_window: str = "Past 30-day window"
    source_timestamp: str = "28 Oct 2026, 10:30 AM"
    data_quality: str = "demo_reference"
    geometry_type: str = "centroid_point"
    geometry_available: bool = False
    is_data_available: bool = True
    last_updated: str

class MapLayersResponse(BaseModel):
    layer_type: str
    generated_at: str
    data_mode: str = "CACHED_VERIFIED"
    is_demo_data: bool = False
    is_data_available: bool = True
    geometry_status: str = "polygon_and_centroids"
    geometry_available: bool = True
    geometry_disclaimer: str = (
        "Pilot districts (Gorakhpur and Mahoba) are bounded by validated Survey of India / OSM polygon boundaries (EPSG:4326). "
        "Candidate districts use centroid coordinates pending polygon onboarding."
    )
    districts: List[DistrictMapFeature]
    metadata: Dict[str, Any]
