from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timezone

from ..pipeline.ingestion import DataIngestionService
from ..schemas.map import MapLayersResponse, DistrictMapFeature

router = APIRouter(prefix="/map", tags=["Geospatial Map Layers"])
ingestion_service = DataIngestionService()

@router.get("/layers", response_model=MapLayersResponse)
def get_map_layers(
    layer: str = Query("flood", description="Hazard layer: flood, drought, rainfall, elevation")
) -> MapLayersResponse:
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_districts = ingestion_service.get_districts_metadata()

    district_features: List[DistrictMapFeature] = []
    for d in raw_districts:
        d_id = d["id"]

        # Derive indicator values
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
        "elevation_source": "SRTM 30m Digital Elevation Model",
        "precipitation_source": "NASA GPM IMERG 0.1° Late Run",
    }

    return MapLayersResponse(
        layer_type=layer,
        generated_at=now_iso,
        is_demo_data=True,
        districts=district_features,
        metadata=metadata,
    )
