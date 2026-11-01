"""
UCSB CHIRPS v2.0 Scientific Source Adapter for JalRakshak AI
Manages Climate Hazards Group InfraRed Precipitation with Station data (CHIRPS 0.05°).

Scientific Details:
- Spatial Resolution: 0.05° × 0.05° (~5.3 km)
- Temporal Resolution: Daily continuous accumulation
- Units: millimeters (mm/day)
- Native Representation: Gridded accumulation (NOT rate)
- Baseline: 1991–2020 30-year climatological normal reference
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone
from pathlib import Path
import httpx
import pandas as pd

from .base import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterResponse,
    ObservationRecord,
    SourceConnectionStatus,
    DatasetType,
    QualityStatus,
    AdapterPayloadError,
    DistrictIsolationError,
)
from ..chirps_pipeline import CHIRPSPipeline
from ...core.config import CHIRPS_BASE_URL

logger = logging.getLogger("jalrakshak.pipeline.adapter.chirps")
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


class CHIRPSAdapter(ScientificSourceAdapter):
    """
    Adapter for UCSB CHIRPS v2.0 station-blended daily precipitation series.
    """

    METADATA = AdapterMetadata(
        source_id="chirps_daily",
        name="UCSB CHIRPS Daily Station-Blended Precipitation",
        provider="University of California, Santa Barbara (UCSB) / USGS",
        product_version="v2.0",
        dataset_type=DatasetType.SATELLITE_DERIVED,
        spatial_resolution="0.05° × 0.05° (~5.3 km)",
        temporal_resolution="Daily accumulation (UTC)",
        default_units="mm",
        is_rate_based=False,
        historical_coverage="1981 – Present (1991–2020 30-year normal baseline)",
        latency="Approximately 3 to 4 weeks post-month for final station-blended product",
        auth_required=False,
        access_method="Public HTTP / FTP data portal (https://data.chc.ucsb.edu/products/CHIRPS-2.0/)",
        citations=[
            "Funk, C., et al. (2015). The climate hazards infrared precipitation with stations—a new environmental record for monitoring extremes. Scientific Data, 2, 150066."
        ],
        limitations=(
            "Station interpolation over sparse ground gauge networks can attenuate extreme single-day storm peaks. "
            "Optimal for climatological departure, SPI distributions, and regional drought assessment."
        ),
    )

    @classmethod
    def get_metadata(cls) -> AdapterMetadata:
        return cls.METADATA

    @classmethod
    async def check_connection(cls, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Verifies endpoint reachability to the UCSB CHC repository and checks local verified archives.
        """
        now = datetime.now(timezone.utc)
        result: Dict[str, Any] = {
            "source_id": cls.METADATA.source_id,
            "provider": cls.METADATA.provider,
            "checked_at": now.isoformat(),
            "status": SourceConnectionStatus.UNREACHABLE,
            "latency_ms": None,
            "local_archive_ready": False,
            "districts_cached": [],
        }

        # Check local verified archives
        cached_districts = []
        for slug in ["gorakhpur", "mahoba"]:
            p = DATA_DIR / f"{slug}_chirps_daily_verified.csv"
            if p.exists():
                cached_districts.append(f"district-{slug}")
        result["districts_cached"] = cached_districts
        result["local_archive_ready"] = len(cached_districts) > 0

        # Remote reachability check
        try:
            start_t = datetime.now(timezone.utc)
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                resp = await client.head(CHIRPS_BASE_URL)
                latency = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000.0
                result["latency_ms"] = round(latency, 1)

                if resp.status_code in [200, 301, 302, 403]:
                    # 200/301/302 indicates host is alive and responding
                    result["status"] = SourceConnectionStatus.CONNECTED
                    result["remote_endpoint"] = CHIRPS_BASE_URL
                else:
                    result["status"] = SourceConnectionStatus.ERROR
                    result["status_code"] = resp.status_code
        except httpx.TimeoutException:
            result["status"] = SourceConnectionStatus.TIMEOUT
            result["error"] = f"Connection to CHC repository timed out after {timeout_seconds}s."
        except httpx.RequestError as exc:
            result["status"] = SourceConnectionStatus.UNREACHABLE
            result["error"] = f"Failed to reach CHC server: {type(exc).__name__}."
        except Exception as exc:
            result["status"] = SourceConnectionStatus.ERROR
            result["error"] = str(exc)

        return result

    @classmethod
    async def fetch_series(
        cls,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> AdapterResponse:
        """
        Retrieves verified daily precipitation series for the specified district.
        Enforces district isolation: rejects candidate districts without onboarded verified series.
        """
        clean_id = cls.normalize_region_id(region_id)
        slug = clean_id.replace("district-", "")

        # Verify district is an onboarded pilot
        if clean_id not in ["district-gorakhpur", "district-mahoba"]:
            raise DistrictIsolationError(
                f"Candidate district '{clean_id}' has no onboarded verified CHIRPS series. "
                f"Cross-district substitution is strictly forbidden under the zero data bleed policy."
            )

        try:
            df = CHIRPSPipeline.load_verified_daily_series(
                district_slug=slug,
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None,
            )
        except FileNotFoundError as fnf:
            return AdapterResponse(
                source_id=cls.METADATA.source_id,
                region_id=clean_id,
                status=SourceConnectionStatus.UNREACHABLE,
                dataset_type=cls.METADATA.dataset_type,
                product_version=cls.METADATA.product_version,
                units=cls.METADATA.default_units,
                observations=[],
                error_message=str(fnf),
            )

        observations: List[ObservationRecord] = []
        valid_cnt = 0
        missing_cnt = 0

        for _, row in df.iterrows():
            obs_date = row["date"].date() if isinstance(row["date"], (pd.Timestamp, datetime)) else row["date"]
            val_clean, q_status, review_flag = cls.validate_rainfall_value(row.get("rainfall_mm"))

            if q_status == QualityStatus.MISSING:
                missing_cnt += 1
            else:
                valid_cnt += 1

            observations.append(
                ObservationRecord(
                    date=obs_date,
                    rainfall_mm=val_clean,
                    raw_value=float(row["rainfall_mm"]) if pd.notna(row.get("rainfall_mm")) else None,
                    raw_units="mm",
                    temporal_semantics="daily_accumulation",
                    interval_hours=24.0,
                    quality_status=q_status,
                    review_flag=review_flag,
                )
            )

        date_range = None
        if observations:
            date_range = {
                "start": str(observations[0].date),
                "end": str(observations[-1].date),
            }

        return AdapterResponse(
            source_id=cls.METADATA.source_id,
            region_id=clean_id,
            status=SourceConnectionStatus.CONNECTED,
            dataset_type=cls.METADATA.dataset_type,
            product_version=cls.METADATA.product_version,
            units=cls.METADATA.default_units,
            temporal_semantics="daily_accumulated_depth",
            is_rate_based=False,
            observations=observations,
            records_count=len(observations),
            valid_count=valid_cnt,
            missing_count=missing_cnt,
            date_range=date_range,
            metadata={
                "spatial_resolution": cls.METADATA.spatial_resolution,
                "temporal_resolution": cls.METADATA.temporal_resolution,
                "climatology_normal_period": "1991-2020",
                "is_cached_archive": True,
                "provenance_archive": f"{slug}_chirps_daily_verified.csv",
            },
        )

    @classmethod
    def validate_payload(cls, raw_payload: Any) -> Dict[str, Any]:
        """
        Validates raw CHIRPS DataFrame or dictionary structure.
        """
        if not isinstance(raw_payload, pd.DataFrame):
            if isinstance(raw_payload, list) and len(raw_payload) > 0 and isinstance(raw_payload[0], dict):
                df = pd.DataFrame(raw_payload)
            else:
                raise AdapterPayloadError("Expected pandas DataFrame or non-empty list of dicts for CHIRPS payload.")
        else:
            df = raw_payload

        for col in ["date", "rainfall_mm"]:
            if col not in df.columns:
                raise AdapterPayloadError(f"CHIRPS payload missing required column: '{col}'")

        # Validate values
        negative_count = (df["rainfall_mm"] < 0.0).sum()
        if negative_count > 0:
            raise AdapterPayloadError(f"Payload contains {negative_count} physically invalid negative precipitation records.")

        return {
            "total_rows": len(df),
            "date_start": str(df["date"].min()),
            "date_end": str(df["date"].max()),
            "mean_rainfall_mm": round(float(df["rainfall_mm"].mean()), 2),
            "max_rainfall_mm": round(float(df["rainfall_mm"].max()), 2),
            "extreme_days_count": int((df["rainfall_mm"] > 500.0).sum()),
        }
