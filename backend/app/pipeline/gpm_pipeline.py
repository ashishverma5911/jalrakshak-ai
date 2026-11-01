"""
NASA GPM IMERG Late Run Ingestion Pipeline for JalRakshak AI
Manages Near-Real-Time (NRT) satellite precipitation estimates from the
Global Precipitation Measurement (GPM) Integrated Multi-satellitE Retrievals for GPM.

Scientific Specifications:
- Product Type: NASA GPM IMERG Late Run (3B-DAY-L)
- Spatial Resolution: 0.1° × 0.1° (~10 km at equator)
- Temporal Resolution: Daily accumulation (00:00 to 23:59 UTC)
- Latency: Approximately 12 to 14 hours post-observation
- Calibration: Combines passive microwave (GMI, SSMIS, AMSR2) with infrared (IR)
  geostationary sounders, calibrated against monthly climatology.
- Units: millimeters (mm/day)
- Rejection Rules:
  * Negative precipitation (< 0.0 mm) is physically impossible -> rejected.
  * Observations > 500.0 mm/day -> flagged as 'provisional_extreme'.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime, timezone
import pandas as pd

from .spatial_aggregation import SpatialAggregator, SpatialAggregationError
from .validation import PrecipitationValidationError

logger = logging.getLogger("jalrakshak.pipeline.gpm")


class GPMIMERGPipeline:
    """
    Ingestion, validation, and spatial integration service for NASA GPM IMERG Late Run.
    """

    PRODUCT_METADATA = {
        "product_id": "3B-DAY-L",
        "product_name": "NASA GPM IMERG Late Run",
        "run_type": "Late Run",
        "spatial_resolution": "0.1° × 0.1° (~10 km)",
        "temporal_resolution": "Daily accumulation (UTC)",
        "units": "mm/day",
        "latency_hours": 14,
        "provider": "NASA Earth Science Data Systems / Goddard Space Flight Center (GSFC)",
        "access_url": "https://gpm.nasa.gov/data/imerg",
        "calibration_note": "Near-real-time microwave-adjusted IR with monthly GPCC climatological ratio calibration.",
    }

    @classmethod
    def validate_gpm_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates an individual GPM observation record.
        """
        rainfall = record.get("rainfall_mm")
        if rainfall is None:
            return {**record, "quality_status": "missing", "rainfall_mm": None}

        try:
            val = float(rainfall)
        except (ValueError, TypeError):
            raise PrecipitationValidationError(f"Invalid non-numeric GPM precipitation: '{rainfall}'")

        if val < 0.0:
            raise PrecipitationValidationError(f"Physically impossible negative GPM rainfall: {val} mm")

        if val == 0.0:
            quality = "zero_precipitation"
        elif val > 500.0:
            quality = "provisional_extreme"
        else:
            quality = "observed"

        out = {
            **record,
            "rainfall_mm": round(val, 2),
            "quality_status": quality,
            "product_type": "NASA GPM IMERG Late Run",
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if val > 500.0:
            out["review_flag"] = "Provisional extreme measurement > 500 mm requires manual scientific review."
        return out

    @classmethod
    def get_recent_monitoring_series(
        cls,
        region_id: str,
        recent_days_df: pd.DataFrame,
        window_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Extracts recent short-term precipitation indicators using GPM Late Run series.
        """
        clean_id = region_id.lower().strip()
        if not clean_id.startswith("district-"):
            clean_id = f"district-{clean_id}"

        # Verify boundary exists
        SpatialAggregator.load_district_boundary(clean_id)

        if recent_days_df.empty:
            return {
                "region_id": clean_id,
                "window_days": window_days,
                "cumulative_mm": 0.0,
                "heavy_rain_days_count": 0,
                "status": "data_pending",
                "metadata": cls.PRODUCT_METADATA,
            }

        tail_df = recent_days_df.tail(window_days)
        cum_rain = float(tail_df["rainfall_mm"].sum())
        heavy_rain_days = int((tail_df["rainfall_mm"] >= 64.5).sum())

        return {
            "region_id": clean_id,
            "window_days": window_days,
            "cumulative_mm": round(cum_rain, 2),
            "heavy_rain_days_count": heavy_rain_days,
            "observation_start": str(tail_df["date"].iloc[0]),
            "observation_end": str(tail_df["date"].iloc[-1]),
            "status": "verified",
            "metadata": cls.PRODUCT_METADATA,
        }
