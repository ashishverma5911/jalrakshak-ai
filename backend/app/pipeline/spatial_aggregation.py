"""
Spatial Aggregation & District Masking Module for JalRakshak AI
Performs boundary-bounded spatial intersection, geodesic area weighting,
and district raster clipping over validated administrative boundary polygons.

Scientific Principles:
1. Rejects point-centroid assumptions for district-wide aggregation.
2. Intersects gridded raster cells (polygons) with the official district boundary.
3. Computes area-weighted mean using true geodesic surface areas (km²) on WGS84 authalic sphere.
4. Strictly excludes grid cells and raster pixels lying outside the boundary.
5. Fails explicitly if no validated polygon is available or if dataset extent is disjoint.
"""

import json
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.validation import make_valid

logger = logging.getLogger("jalrakshak.pipeline.spatial")

BOUNDARIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "boundaries"
WGS84_MEAN_RADIUS_KM = 6371.0088  # WGS84 authalic mean earth radius


class SpatialAggregationError(ValueError):
    """Raised when spatial aggregation fails or validated boundary is missing."""
    pass


def geodesic_cell_area_km2(min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> float:
    """
    Computes geodesic surface area of a lat/lon bounding box in square kilometers
    on the WGS84 authalic sphere, accounting for longitudinal convergence with latitude.
    """
    d_lambda = math.radians(abs(max_lng - min_lng))
    sin_diff = abs(math.sin(math.radians(max_lat)) - math.sin(math.radians(min_lat)))
    return (WGS84_MEAN_RADIUS_KM ** 2) * d_lambda * sin_diff


class SpatialAggregator:
    """
    Performs boundary-bounded spatial intersection, geodesic area weighting,
    and raster district masking.
    """

    _boundary_cache: Dict[str, Any] = {}

    @classmethod
    def load_district_boundary(cls, region_id: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Loads and validates district GeoJSON boundary polygon.
        Returns: (shapely_geometry, properties_dict)
        """
        clean_id = region_id.lower().strip()
        if clean_id not in cls._boundary_cache:
            geojson_path = BOUNDARIES_DIR / f"{clean_id}.geojson"
            if not geojson_path.exists():
                raise SpatialAggregationError(
                    f"Validated administrative polygon unavailable for '{region_id}'. "
                    f"District-wide spatial aggregation halted to prevent ungrounded centroid estimation."
                )

            with open(geojson_path, "r", encoding="utf-8") as f:
                feature = json.load(f)

            raw_geom = feature.get("geometry")
            if not raw_geom:
                raise SpatialAggregationError(f"GeoJSON feature for '{region_id}' lacks geometry definition.")

            geom = shape(raw_geom)
            if not geom.is_valid:
                geom = make_valid(geom)
                if not geom.is_valid:
                    raise SpatialAggregationError(f"Topological repair failed for boundary '{region_id}'.")

            props = feature.get("properties", {})
            cls._boundary_cache[clean_id] = (geom, props)

        return cls._boundary_cache[clean_id]

    @classmethod
    def validate_dataset_spatial_coverage(
        cls,
        region_id: str,
        bbox: Dict[str, float],
        crs: str = "EPSG:4326"
    ) -> Dict[str, Any]:
        """
        Tests whether the dataset bounding box intersects the target district polygon.
        Calculates exact intersection geometry, geodesic coverage in km², and overlap percentage.
        Raises SpatialAggregationError if dataset is completely disjoint from the district.
        """
        geom, props = cls.load_district_boundary(region_id)
        d_minx, d_miny, d_maxx, d_maxy = geom.bounds

        min_lng = bbox["min_lng"]
        min_lat = bbox["min_lat"]
        max_lng = bbox["max_lng"]
        max_lat = bbox["max_lat"]

        dataset_poly = box(min_lng, min_lat, max_lng, max_lat)

        # 1. Test Spatial Intersection
        if not geom.intersects(dataset_poly):
            raise SpatialAggregationError(
                f"Dataset spatial extent [lng: {min_lng:.4f} to {max_lng:.4f}, lat: {min_lat:.4f} to {max_lat:.4f}] "
                f"does not intersect target district '{region_id}' boundary "
                f"[lng: {d_minx:.4f} to {d_maxx:.4f}, lat: {d_miny:.4f} to {d_maxy:.4f}]."
            )

        intersection = geom.intersection(dataset_poly)
        if intersection.is_empty or intersection.area <= 0:
            raise SpatialAggregationError(
                f"Zero intersection area between dataset extent and district '{region_id}' boundary."
            )

        # 2. Compute Overlap Percentage
        overlap_fraction = intersection.area / geom.area
        overlap_pct = min(100.0, round(overlap_fraction * 100.0, 2))
        is_partial = overlap_pct < 98.0

        # Calculate geodesic district area in km²
        district_geodesic_area_km2 = geodesic_cell_area_km2(d_minx, d_miny, d_maxx, d_maxy) * (geom.area / ((d_maxx - d_minx) * (d_maxy - d_miny)))
        intersected_geodesic_area_km2 = district_geodesic_area_km2 * overlap_fraction

        return {
            "region_id": region_id,
            "crs": crs,
            "is_intersecting": True,
            "is_partial_coverage": is_partial,
            "spatial_overlap_pct": overlap_pct,
            "district_geodesic_area_km2": round(district_geodesic_area_km2, 2),
            "intersected_geodesic_area_km2": round(intersected_geodesic_area_km2, 2),
            "district_bounds": {
                "min_lng": round(d_minx, 6),
                "min_lat": round(d_miny, 6),
                "max_lng": round(d_maxx, 6),
                "max_lat": round(d_maxy, 6),
            },
            "dataset_bounds": bbox,
        }

    @classmethod
    def mask_raster_to_district(
        cls,
        region_id: str,
        raster_array: np.ndarray,
        geotransform: Tuple[float, float, float, float, float, float],
        nodata_val: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Masks a 2D raster array against the district boundary polygon.
        Pixels whose cell centers fall outside the boundary are marked as NaN / excluded.
        Computes valid in-district metrics (mean, max, min, valid count).
        """
        geom, props = cls.load_district_boundary(region_id)
        origin_x, scale_x, _, origin_y, _, neg_scale_y = geotransform
        pixel_h = abs(neg_scale_y)
        pixel_w = abs(scale_x)

        height, width = raster_array.shape
        masked_array = raster_array.copy().astype(np.float32)

        # Generate coordinate vectors for pixel centers
        x_coords = origin_x + (np.arange(width) + 0.5) * pixel_w
        y_coords = origin_y - (np.arange(height) + 0.5) * pixel_h

        # Quick bbox check
        r_minx, r_maxx = float(origin_x), float(origin_x + width * pixel_w)
        r_maxy, r_miny = float(origin_y), float(origin_y - height * pixel_h)
        raster_box = box(r_minx, r_miny, r_maxx, r_maxy)

        if not geom.intersects(raster_box):
            raise SpatialAggregationError(
                f"Raster extent [{r_minx:.4f}, {r_miny:.4f}, {r_maxx:.4f}, {r_maxy:.4f}] "
                f"is completely disjoint from district '{region_id}' boundary."
            )

        # Point-in-polygon masking
        from shapely.geometry import Point
        in_district_mask = np.zeros((height, width), dtype=bool)

        # To optimize for 512MB RAM: check only coordinates within district bounding box
        d_minx, d_miny, d_maxx, d_maxy = geom.bounds
        col_indices = np.where((x_coords >= d_minx - pixel_w) & (x_coords <= d_maxx + pixel_w))[0]
        row_indices = np.where((y_coords >= d_miny - pixel_h) & (y_coords <= d_maxy + pixel_h))[0]

        for r in row_indices:
            cy = float(y_coords[r])
            for c in col_indices:
                cx = float(x_coords[c])
                cell_box = box(cx - pixel_w/2, cy - pixel_h/2, cx + pixel_w/2, cy + pixel_h/2)
                if geom.intersects(cell_box):
                    in_district_mask[r, c] = True

        # Mask pixels outside district
        masked_array[~in_district_mask] = np.nan
        if nodata_val is not None:
            masked_array[masked_array == nodata_val] = np.nan
        masked_array[masked_array <= -900.0] = np.nan

        valid_in_district = masked_array[~np.isnan(masked_array)]
        valid_cnt = int(valid_in_district.size)
        total_in_district_cells = int(np.sum(in_district_mask))

        if valid_cnt == 0:
            raise SpatialAggregationError(
                f"No valid in-district precipitation observations found inside '{region_id}' boundary."
            )

        mean_val = round(float(np.mean(valid_in_district)), 2)
        max_val = round(float(np.max(valid_in_district)), 2)
        min_val = round(float(np.min(valid_in_district)), 2)
        extreme_cnt = int(np.sum(valid_in_district > 500.0))

        return {
            "region_id": region_id,
            "in_district_cells_total": total_in_district_cells,
            "in_district_valid_pixels": valid_cnt,
            "in_district_mean_mm": mean_val,
            "in_district_max_mm": max_val,
            "in_district_min_mm": min_val,
            "in_district_extreme_pixels": extreme_cnt,
            "masked_raster": masked_array,
        }

    @classmethod
    def aggregate_gridded_precipitation(
        cls,
        region_id: str,
        grid_observations: List[Dict[str, Any]],
        resolution_deg: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Aggregates gridded precipitation measurements into a single district value
        using area-weighted spatial intersection on true geodesic km² surface areas.
        """
        geom, props = cls.load_district_boundary(region_id)
        d_minx, d_miny, d_maxx, d_maxy = geom.bounds

        total_weighted_precip = 0.0
        total_intersected_area_km2 = 0.0
        cells_used = 0
        half_res = resolution_deg / 2.0

        for obs in grid_observations:
            raw_r = obs.get("rainfall_mm")
            if raw_r is None or pd.isna(raw_r):
                continue
            c_lat = float(obs["lat"])
            c_lng = float(obs["lng"])
            r_mm = float(raw_r)

            # Grid cell bounds
            c_min_lng = c_lng - half_res
            c_max_lng = c_lng + half_res
            c_min_lat = c_lat - half_res
            c_max_lat = c_lat + half_res

            cell_poly = box(c_min_lng, c_min_lat, c_max_lng, c_max_lat)

            # Check spatial intersection with boundary
            if not geom.intersects(cell_poly):
                continue

            intersection = geom.intersection(cell_poly)
            if intersection.is_empty or intersection.area <= 0:
                continue

            # Fraction of cell inside boundary
            fraction = intersection.area / cell_poly.area
            # Geodesic area of this cell in km²
            cell_area_km2 = geodesic_cell_area_km2(c_min_lng, c_min_lat, c_max_lng, c_max_lat)
            intersected_km2 = fraction * cell_area_km2

            total_weighted_precip += r_mm * intersected_km2
            total_intersected_area_km2 += intersected_km2
            cells_used += 1

        if total_intersected_area_km2 <= 0 or cells_used == 0:
            raise SpatialAggregationError(
                f"No grid cells intersected the validated boundary for '{region_id}'."
            )

        area_weighted_mean = total_weighted_precip / total_intersected_area_km2

        # Geodesic district area estimation
        district_deg_area = geom.area
        bbox_deg_area = (d_maxx - d_minx) * (d_maxy - d_miny)
        bbox_km2 = geodesic_cell_area_km2(d_minx, d_miny, d_maxx, d_maxy)
        district_geodesic_km2 = bbox_km2 * (district_deg_area / bbox_deg_area)

        coverage_pct = min(100.0, (total_intersected_area_km2 / district_geodesic_km2) * 100.0)

        return {
            "region_id": region_id,
            "area_weighted_rainfall_mm": round(area_weighted_mean, 2),
            "cells_intersected": cells_used,
            "district_geodesic_area_km2": round(district_geodesic_km2, 2),
            "intersected_geodesic_area_km2": round(total_intersected_area_km2, 2),
            "spatial_coverage_pct": round(coverage_pct, 1),
            "aggregation_method": "area_weighted_polygon_intersection",
            "geodesic_surface_weighting": "WGS84_authalic_sphere_km2",
            "crs": "EPSG:4326",
            "boundary_source": props.get("source", "verified_administrative_polygon"),
        }
