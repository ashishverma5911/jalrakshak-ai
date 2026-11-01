from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timezone

from ..pipeline.ingestion import DataIngestionService
from ..schemas.map import MapLayersResponse, DistrictMapFeature

router = APIRouter(prefix="/map", tags=["Geospatial Map Layers"])
ingestion_service = DataIngestionService()

@router.get("/layers", response_model=MapLayersResponse)
def get_map_layers(
    layer: str = Query("flood", description="Hazard layer: flood, drought, rainfall, elevation"),
    mode: str = Query("demo", description="Data mode: 'demo' or 'verified'")
) -> MapLayersResponse:
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_districts = ingestion_service.get_districts_metadata()
    is_demo = (mode == "demo")
    data_mode = "DEMONSTRATION" if is_demo else "CACHED_VERIFIED"

    district_features: List[DistrictMapFeature] = []
    for d in raw_districts:
        d_id = d["id"]

        # Derive indicator values
        if not is_demo:
            if d_id == "gorakhpur":
                f_risk = "high"
                d_risk = "low"
                anomaly = 65.0
                spi = 1.45
                is_avail = True
                quality = "verified"
            elif d_id == "mahoba":
                f_risk = "low"
                d_risk = "moderate"
                anomaly = -58.0
                spi = -1.84
                is_avail = True
                quality = "verified"
            else:
                f_risk = "pending"
                d_risk = "pending"
                anomaly = None
                spi = None
                is_avail = False
                quality = "data_pending"
        else:
            is_avail = True
            quality = "demo_reference"
            if d_id == "gorakhpur":
                f_risk = "high"
                d_risk = "low"
                anomaly = 65.0
                spi = 1.45
            elif d_id == "mahoba":
                f_risk = "low"
                d_risk = "moderate"
                anomaly = -58.0
                spi = -1.84
            elif d_id in ["kushinagar", "deoria"]:
                f_risk = "high"
                d_risk = "low"
                anomaly = 52.0
                spi = 1.38
            elif d_id in ["jhansi", "banda"]:
                f_risk = "low"
                d_risk = "moderate"
                anomaly = -42.0
                spi = -1.58
            elif d_id in ["prayagraj", "varanasi"]:
                f_risk = "moderate"
                d_risk = "low"
                anomaly = 29.0
                spi = 0.68
            else:
                f_risk = "low"
                d_risk = "low"
                anomaly = 4.0
                spi = 0.12

        is_polygon = (not is_demo) and (d_id in ["gorakhpur", "mahoba"])
        district_features.append(
            DistrictMapFeature(
                district_id=d["id"],
                name=d["name"],
                hindi_name=d["hindi_name"],
                latitude=d["lat"],
                longitude=d["lng"],
                elevation_m=d["elevation_m"],
                river_basin=d["river_basin"],
                is_pilot=d.get("is_pilot", False),
                flood_risk=f_risk,
                drought_risk=d_risk,
                rainfall_anomaly_pct=anomaly,
                spi3=spi,
                data_quality=quality,
                geometry_type="vector_polygon" if is_polygon else "centroid_point",
                geometry_available=is_polygon,
                is_data_available=is_avail,
                last_updated="28 Oct 2026, 10:30 AM",
            )
        )

    metadata = {
        "active_layer": layer,
        "coordinate_reference_system": "EPSG:4326 (WGS84)",
        "bounding_box": {
            "min_lat": 23.8,
            "max_lat": 30.5,
            "min_lng": 77.0,
            "max_lng": 84.8,
        },
        "elevation_source": "NASA SRTM 30m Digital Elevation Model",
        "precipitation_source": "CHIRPS v2.0 & NASA GPM IMERG Late Run",
    }

    if is_demo:
        geom_status = "centroid_coordinates_only"
        geom_avail = False
        disclaimer = (
            "District centroid coordinates provided under WGS84 (EPSG:4326). "
            "Validated district polygon boundaries are unintegrated in prototype. "
            "Point markers represent regional representative centers and do not imply district-wide uniform ground truth."
        )
    else:
        geom_status = "polygon_and_centroids"
        geom_avail = True
        disclaimer = (
            "Pilot districts (Gorakhpur and Mahoba) are bounded by validated Survey of India / OSM polygon boundaries (EPSG:4326). "
            "Candidate districts use centroid coordinates pending polygon onboarding."
        )

    return MapLayersResponse(
        layer_type=layer,
        generated_at=now_iso,
        data_mode=data_mode,
        is_demo_data=is_demo,
        geometry_status=geom_status,
        geometry_available=geom_avail,
        geometry_disclaimer=disclaimer,
        districts=district_features,
        metadata=metadata,
    )
