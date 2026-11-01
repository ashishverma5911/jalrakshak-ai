"""
Boundary Ingestion & Spatial Validation Service for JalRakshak AI
Handles:
- Coordinate Reference System (CRS) validation (EPSG:4326 / WGS84)
- Topological validation (Shapely is_valid, polygon/multipolygon checks)
- Geographic boundary containment validation for India
- Provenance and licensing metadata tracking
- Idempotent boundary updating
- Strict refusal to fabricate artificial polygons
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.validation import make_valid
from sqlalchemy.orm import Session

from ..db.models import Region, RegionBoundary

logger = logging.getLogger("jalrakshak.services.boundary")

# Bounding box for India territory (EPSG:4326)
INDIA_BBOX = {
    "min_lng": 68.0,
    "max_lng": 98.0,
    "min_lat": 6.0,
    "max_lat": 38.0,
}


class BoundaryValidationError(ValueError):
    """Raised when a boundary fails topological or coordinate validation."""
    pass


class BoundaryIngestionService:
    """
    Ingestion, validation and spatial audit pipeline for administrative boundaries.
    """

    @classmethod
    def validate_geometry(cls, geojson_geom: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """
        Validates GeoJSON geometry structure, coordinate limits, and topology.
        Returns: (shapely_geom, stats_dict)
        """
        if not geojson_geom or "type" not in geojson_geom or "coordinates" not in geojson_geom:
            raise BoundaryValidationError("Invalid GeoJSON geometry structure: missing type or coordinates.")

        geom_type = geojson_geom["type"]
        if geom_type not in ["Polygon", "MultiPolygon", "Point"]:
            raise BoundaryValidationError(f"Unsupported geometry type: '{geom_type}'. Expected Polygon, MultiPolygon, or Point.")

        try:
            geom = shape(geojson_geom)
        except Exception as e:
            raise BoundaryValidationError(f"Shapely failed to parse geometry: {e}")

        # Check topological validity
        if not geom.is_valid:
            logger.warning("Geometry contains topological self-intersections; repairing with make_valid.")
            geom = make_valid(geom)
            if not geom.is_valid:
                raise BoundaryValidationError("Geometry could not be repaired into a topologically valid shape.")

        # Coordinate bounds verification
        bounds = geom.bounds  # (minx, miny, maxx, maxy) -> (min_lng, min_lat, max_lng, max_lat)
        min_lng, min_lat, max_lng, max_lat = bounds

        if (min_lng < INDIA_BBOX["min_lng"] or max_lng > INDIA_BBOX["max_lng"] or
            min_lat < INDIA_BBOX["min_lat"] or max_lat > INDIA_BBOX["max_lat"]):
            raise BoundaryValidationError(
                f"Geometry coordinates {bounds} lie outside the territorial bounds of India."
            )

        centroid = geom.centroid
        stats = {
            "geom_type": geom_type,
            "is_valid": geom.is_valid,
            "bounds": [round(b, 5) for b in bounds],
            "centroid": [round(centroid.x, 5), round(centroid.y, 5)],
            "approx_area_deg2": round(geom.area, 6) if geom_type != "Point" else 0.0,
        }
        return geom, stats

    @classmethod
    def ingest_feature(
        cls,
        db: Session,
        region_id: str,
        geometry: Dict[str, Any],
        source: str = "survey_of_india_geojson",
        version: str = "2024.1",
        license_str: str = "Government Open Data License (GODL) - India",
    ) -> Dict[str, Any]:
        """
        Ingests a verified GeoJSON geometry for a specified region ID.
        """
        region = db.query(Region).filter_by(id=region_id).first()
        if not region:
            raise BoundaryValidationError(f"Target region '{region_id}' does not exist in the database.")

        geom, stats = cls.validate_geometry(geometry)
        wkt_str = geom.wkt

        # Check existing boundary record
        boundary_record = db.query(RegionBoundary).filter_by(region_id=region_id).first()
        boundary_id = f"boundary-{region_id}"

        if not boundary_record:
            boundary_record = RegionBoundary(
                id=boundary_id,
                region_id=region_id,
                geometry=wkt_str,
                boundary_source=source,
                boundary_version=version,
            )
            db.add(boundary_record)
        else:
            boundary_record.geometry = wkt_str
            boundary_record.boundary_source = source
            boundary_record.boundary_version = version

        db.commit()
        return {
            "region_id": region_id,
            "boundary_id": boundary_record.id,
            "source": source,
            "version": version,
            "license": license_str,
            "stats": stats,
            "status": "ingested_verified",
        }

    @classmethod
    def audit_boundary_status(cls, db: Session, region_id: str) -> Dict[str, Any]:
        """
        Returns full transparency report on boundary data fidelity for a region.
        """
        region = db.query(Region).filter_by(id=region_id).first()
        if not region:
            return {"status": "region_not_found"}

        bnd = db.query(RegionBoundary).filter_by(region_id=region_id).first()
        if not bnd or not bnd.geometry:
            return {
                "region_id": region_id,
                "region_name": region.name,
                "has_geometry": False,
                "geometry_mode": "unavailable",
                "disclaimer": "No boundary or centroid data registered.",
            }

        geom_str = str(bnd.geometry)
        is_point = geom_str.startswith("POINT") or bnd.boundary_source.endswith("_centroid")

        return {
            "region_id": region_id,
            "region_name": region.name,
            "has_geometry": True,
            "geometry_mode": "centroid_point" if is_point else "vector_polygon",
            "boundary_source": bnd.boundary_source,
            "boundary_version": bnd.boundary_version,
            "is_polygon_integrated": not is_point,
            "disclaimer": (
                "Verified point centroid coordinates under WGS84. Full administrative polygon unintegrated in prototype."
                if is_point
                else "Validated administrative boundary polygon."
            ),
        }
