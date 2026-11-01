"""
NASA SRTM 30m Digital Elevation Model Adapter for JalRakshak AI
Manages static topographic elevation benchmarks and terrain vulnerability metrics.

Scientific Invariant:
NASA SRTM 1 arc-second (~30m) DEM is a STATIC reference dataset.
It is explicitly NOT a dynamic time-series precipitation feed and must never be
forced into a live fetch_latest() time-series workflow.
"""

import logging
from typing import Dict, Any, Optional
from datetime import date, datetime, timezone

from .base import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterResponse,
    SourceConnectionStatus,
    DatasetType,
    AdapterPayloadError,
    DistrictIsolationError,
)
from ..srtm_pipeline import SRTMElevationPipeline, SRTM_DISTRICT_BENCHMARKS
from ..spatial_aggregation import SpatialAggregator, SpatialAggregationError

logger = logging.getLogger("jalrakshak.pipeline.adapter.srtm")


class SRTMAdapter(ScientificSourceAdapter):
    """
    Adapter for NASA SRTM 30m Digital Elevation Model static terrain benchmarks.
    """

    METADATA = AdapterMetadata(
        source_id="nasa_srtm_30m",
        name="NASA SRTM 1 Arc-Second Global DEM (30m)",
        provider="NASA Jet Propulsion Laboratory (JPL) / USGS LP DAAC",
        product_version="v3.0 void-filled",
        dataset_type=DatasetType.STATIC_REFERENCE,
        spatial_resolution="1 arc-second (~30 meters)",
        temporal_resolution="Static reference benchmark (Shuttle Radar Topography Mission)",
        default_units="meters",
        is_rate_based=False,
        historical_coverage="February 2000 mission (Global landmass 60°N to 56°S)",
        latency="Static Reference (Zero latency)",
        auth_required=False,
        access_method="Static Verified Elevation Benchmark (USGS EarthExplorer archive)",
        citations=[
            "Farr, T. G., et al. (2007). The Shuttle Radar Topography Mission. Reviews of Geophysics, 45(2), RG2004."
        ],
        limitations=(
            "Measures Digital Surface Model (DSM) top canopy and rooftop reflections. "
            "Does not resolve sub-grid micro-embankments, artificial drainage cuts, or newly built levees."
        ),
    )

    @classmethod
    def get_metadata(cls) -> AdapterMetadata:
        return cls.METADATA

    @classmethod
    async def check_connection(cls) -> Dict[str, Any]:
        """
        Verifies static terrain benchmark availability for calibrated districts.
        Explicitly reports STATIC_REFERENCE status. Dynamic stream polling is disabled.
        """
        calibrated = list(SRTM_DISTRICT_BENCHMARKS.keys())
        return {
            "source_id": cls.METADATA.source_id,
            "provider": cls.METADATA.provider,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": SourceConnectionStatus.STATIC_REFERENCE,
            "is_static": True,
            "calibrated_districts": calibrated,
            "message": (
                "NASA SRTM 30m DEM operates as a static topographic elevation benchmark. "
                "Dynamic time-series polling is disabled by design."
            ),
        }

    @classmethod
    async def fetch_series(
        cls,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> AdapterResponse:
        """
        Explicitly rejects time-series fetching for static elevation dataset.
        Directs callers to get_elevation_profile().
        """
        clean_id = cls.normalize_region_id(region_id)
        raise NotImplementedError(
            f"NASA SRTM DEM is a static topographic dataset and does not produce time-series precipitation. "
            f"Use SRTMAdapter.get_elevation_profile('{clean_id}') to query terrain metrics."
        )

    @classmethod
    def get_elevation_profile(cls, region_id: str) -> Dict[str, Any]:
        """
        Retrieves static SRTM 30m elevation statistics and terrain flood vulnerability index.
        Enforces district boundary verification and zero cross-district substitution.
        """
        clean_id = cls.normalize_region_id(region_id)

        # Confirm validated boundary exists
        try:
            SpatialAggregator.load_district_boundary(clean_id)
        except SpatialAggregationError as sae:
            raise DistrictIsolationError(
                f"Candidate district '{clean_id}' lacks validated boundary polygon: {sae}"
            )

        if clean_id not in SRTM_DISTRICT_BENCHMARKS:
            raise DistrictIsolationError(
                f"SRTM 30m elevation benchmark is uncalibrated for candidate district '{clean_id}'. "
                f"Pilot district elevation data is never substituted."
            )

        return SRTMElevationPipeline.get_elevation_profile(clean_id)

    @classmethod
    def validate_payload(cls, raw_payload: Any) -> Dict[str, Any]:
        """
        Validates terrain profile metrics against physical terrestrial bounds.
        """
        if not isinstance(raw_payload, dict):
            raise AdapterPayloadError("Expected dictionary containing terrain metrics.")

        required_keys = ["mean_elevation_m", "min_elevation_m", "max_elevation_m", "elevation_std_m"]
        for k in required_keys:
            if k not in raw_payload:
                raise AdapterPayloadError(f"Missing required elevation metric: '{k}'")

        mean_elev = float(raw_payload["mean_elevation_m"])
        min_elev = float(raw_payload["min_elevation_m"])
        max_elev = float(raw_payload["max_elevation_m"])
        std_elev = float(raw_payload["elevation_std_m"])

        # Terrestrial bounds: -500m (Dead Sea) to 8849m (Everest)
        if not (-500.0 <= min_elev <= max_elev <= 9000.0):
            raise AdapterPayloadError(f"Physical bounds violation: elevations [{min_elev}, {max_elev}] m.")

        if std_elev < 0.0:
            raise AdapterPayloadError(f"Standard deviation cannot be negative: {std_elev} m.")

        return {
            "mean_elevation_m": mean_elev,
            "relief_range_m": round(max_elev - min_elev, 2),
            "topographic_roughness_std": std_elev,
            "status": "valid",
        }
