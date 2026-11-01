"""
NASA GPM IMERG Scientific Source Adapter for JalRakshak AI
Manages Near-Real-Time (Early/Late) and Research-Grade (Final) GPM IMERG observations.

Scientific Product Runs:
- Early Run (3B-DAY-E): ~4h latency, real-time flood monitoring, climatological calibration.
- Late Run (3B-DAY-L): ~14h latency, daily operational assessment, microwave-adjusted IR.
- Final Run (3B-DAY-F): ~3.5 months latency, gauge-calibrated research benchmark.

Critical Requirements:
1. Distinguishes precipitation rate (mm/hr) from daily accumulation (mm).
2. Explicitly enforces NASA Earthdata URS authentication (AUTHENTICATION_REQUIRED when credentials unset).
3. Preserves product run type and quality flags.
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
    AdapterAuthenticationError,
    DistrictIsolationError,
)
from ...core.config import (
    EARTHDATA_USERNAME,
    EARTHDATA_PASSWORD,
    EARTHDATA_BEARER_TOKEN,
)
from ..spatial_aggregation import SpatialAggregator, SpatialAggregationError

logger = logging.getLogger("jalrakshak.pipeline.adapter.gpm")
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

GPM_EARTHDATA_LOGIN_URL = "https://urs.earthdata.nasa.gov/api/v1/users/me"
GPM_GES_DISC_BASE_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3"


class GPMIMERGAdapter(ScientificSourceAdapter):
    """
    Adapter for NASA GPM IMERG satellite precipitation products.
    """

    METADATA = AdapterMetadata(
        source_id="nasa_gpm_imerg",
        name="NASA GPM IMERG Precipitation (Early / Late / Final Run)",
        provider="NASA Earth Science Data Systems / Goddard Space Flight Center (GSFC)",
        product_version="v07B (3B-DAY-L / 3B-DAY-E / 3B-DAY-F)",
        dataset_type=DatasetType.SATELLITE_DERIVED,
        spatial_resolution="0.1° × 0.1° (~10 km at equator)",
        temporal_resolution="Daily accumulation (00:00 to 23:59 UTC)",
        default_units="mm",
        is_rate_based=False,
        historical_coverage="2000 – Present",
        latency="Early: ~4h | Late: ~14h | Final: ~3.5 months",
        auth_required=True,
        access_method="NASA Earthdata URS authenticated HTTPS / OPeNDAP (https://gpm.nasa.gov/data/imerg)",
        citations=[
            "Huffman, G. J., et al. (2020). Integrated Multi-satellitE Retrievals for GPM (IMERG) technical documentation. NASA GSFC."
        ],
        limitations=(
            "Passive microwave and infrared estimates calibrate well for regional storm systems but smooth localized convective cloudbursts. "
            "Real-time operational streams require institutional Earthdata credentials. Unlinked from operational scoring unless fully calibrated."
        ),
    )

    @classmethod
    def get_metadata(cls) -> AdapterMetadata:
        return cls.METADATA

    @classmethod
    def get_run_metadata(cls, run_type: str = "Late") -> Dict[str, Any]:
        """Returns run-specific metadata distinguishing Early, Late, and Final runs."""
        run_norm = run_type.capitalize()
        specs = {
            "Early": {
                "product_id": "3B-DAY-E",
                "name": "NASA GPM IMERG Early Run",
                "latency_hours": 4,
                "purpose": "Flash flood alerting, preliminary rapid response",
                "calibration": "Climatological microwave calibration only",
            },
            "Late": {
                "product_id": "3B-DAY-L",
                "name": "NASA GPM IMERG Late Run",
                "latency_hours": 14,
                "purpose": "Daily crop monitoring and hazard assessment",
                "calibration": "Microwave-adjusted geostationary IR with monthly GPCC climatological ratio",
            },
            "Final": {
                "product_id": "3B-DAY-F",
                "name": "NASA GPM IMERG Final Run",
                "latency_months": 3.5,
                "purpose": "Climatological research, long-term trend analysis",
                "calibration": "Full GPCC gauge-calibrated research grade",
            },
        }
        return specs.get(run_norm, specs["Late"])

    @classmethod
    async def check_connection(cls, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Verifies NASA Earthdata authentication readiness and server reachability.
        Returns AUTHENTICATION_REQUIRED if Earthdata credentials are missing.
        """
        now = datetime.now(timezone.utc)
        has_user = bool(EARTHDATA_USERNAME and EARTHDATA_PASSWORD)
        has_token = bool(EARTHDATA_BEARER_TOKEN)

        result: Dict[str, Any] = {
            "source_id": cls.METADATA.source_id,
            "provider": cls.METADATA.provider,
            "checked_at": now.isoformat(),
            "status": SourceConnectionStatus.AUTHENTICATION_REQUIRED,
            "auth_configured": has_user or has_token,
            "latency_ms": None,
            "cached_granules_present": False,
        }

        # Check for local cached granules/data
        cached_files = list(DATA_DIR.glob("*gpm*")) + list(DATA_DIR.glob("*imerg*"))
        result["cached_granules_present"] = len(cached_files) > 0
        result["cached_files_count"] = len(cached_files)

        if not (has_user or has_token):
            result["status"] = SourceConnectionStatus.AUTHENTICATION_REQUIRED
            result["message"] = (
                "NASA Earthdata URS credentials (EARTHDATA_USERNAME / EARTHDATA_PASSWORD or EARTHDATA_BEARER_TOKEN) "
                "are not configured. Required to download live NASA GPM IMERG granules from GES DISC."
            )
            return result

        # Test Earthdata authentication
        try:
            start_t = datetime.now(timezone.utc)
            headers = {}
            auth = None
            if has_token:
                headers["Authorization"] = f"Bearer {EARTHDATA_BEARER_TOKEN}"
            elif has_user:
                auth = (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)

            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.get(GPM_EARTHDATA_LOGIN_URL, auth=auth, headers=headers)
                latency = (datetime.now(timezone.utc) - start_t).total_seconds() * 1000.0
                result["latency_ms"] = round(latency, 1)

                if resp.status_code == 200:
                    result["status"] = SourceConnectionStatus.CONNECTED
                    result["message"] = "NASA Earthdata authentication successful."
                elif resp.status_code in [401, 403]:
                    result["status"] = SourceConnectionStatus.AUTHENTICATION_FAILED
                    result["error"] = "NASA Earthdata rejected credentials (HTTP 401/403)."
                else:
                    result["status"] = SourceConnectionStatus.ERROR
                    result["status_code"] = resp.status_code
        except httpx.TimeoutException:
            result["status"] = SourceConnectionStatus.TIMEOUT
            result["error"] = f"NASA Earthdata login endpoint timed out after {timeout_seconds}s."
        except httpx.RequestError as exc:
            result["status"] = SourceConnectionStatus.UNREACHABLE
            result["error"] = f"NASA Earthdata server unreachable: {type(exc).__name__}."
        except Exception as exc:
            result["status"] = SourceConnectionStatus.ERROR
            result["error"] = str(exc)

        return result

    @classmethod
    async def fetch_series(
        cls,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        run_type: str = "Late"
    ) -> AdapterResponse:
        """
        Retrieves GPM IMERG daily observations for the specified district.
        Enforces district boundary verification and zero cross-district substitution.
        """
        clean_id = cls.normalize_region_id(region_id)
        run_meta = cls.get_run_metadata(run_type)

        # Validate boundary exists
        try:
            SpatialAggregator.load_district_boundary(clean_id)
        except SpatialAggregationError as sae:
            raise DistrictIsolationError(
                f"Candidate district '{clean_id}' lacks validated boundary. "
                f"GPM spatial extraction halted to avoid ungrounded centroid estimation: {sae}"
            )

        # Check credentials
        has_auth = bool((EARTHDATA_USERNAME and EARTHDATA_PASSWORD) or EARTHDATA_BEARER_TOKEN)
        
        # Check if local archived extracts exist
        csv_path = DATA_DIR / f"{clean_id.replace('district-', '')}_gpm_imerg_daily.csv"
        
        if not csv_path.exists() and not has_auth:
            return AdapterResponse(
                source_id=cls.METADATA.source_id,
                region_id=clean_id,
                status=SourceConnectionStatus.AUTHENTICATION_REQUIRED,
                dataset_type=cls.METADATA.dataset_type,
                product_version=run_meta["product_id"],
                units=cls.METADATA.default_units,
                observations=[],
                error_message=(
                    f"NASA Earthdata authentication required for live {run_meta['name']} retrieval. "
                    "Configure EARTHDATA_USERNAME and EARTHDATA_PASSWORD in environment."
                ),
                metadata=run_meta,
            )

        if not csv_path.exists():
            return AdapterResponse(
                source_id=cls.METADATA.source_id,
                region_id=clean_id,
                status=SourceConnectionStatus.CONNECTED if has_auth else SourceConnectionStatus.UNREACHABLE,
                dataset_type=cls.METADATA.dataset_type,
                product_version=run_meta["product_id"],
                units=cls.METADATA.default_units,
                observations=[],
                error_message=f"No GPM IMERG extracted daily records available for '{clean_id}'.",
                metadata=run_meta,
            )

        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        if start_date:
            df = df[df["date"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["date"] <= pd.to_datetime(end_date)]

        observations: List[ObservationRecord] = []
        valid_cnt = 0
        missing_cnt = 0

        for _, row in df.iterrows():
            obs_date = row["date"].date() if isinstance(row["date"], (pd.Timestamp, datetime)) else row["date"]
            raw_val = row.get("rainfall_mm")
            raw_unit = str(row.get("unit", "mm")).strip().lower()

            # Unit & Temporal Semantics Verification
            # 1. Daily products (3B-DAY) are ALREADY daily accumulated depth (mm)
            if raw_unit in ["mm", "mm/day", "daily_accumulation", "depth_mm"]:
                accum_val = raw_val
                temporal_sem = "daily_accumulation"
                interval_h = 24.0
            # 2. Rate-based products (mm/hr): require explicit duration. NEVER blindly assume 24 hours.
            elif raw_unit in ["mm/hr", "mm/hour"]:
                if pd.isna(raw_val) or raw_val is None:
                    accum_val = None
                    temporal_sem = "missing_rate"
                    interval_h = None
                else:
                    # Check for explicit duration specification
                    dur_val = row.get("duration_hours")
                    if dur_val is None and "interval_minutes" in row and pd.notna(row["interval_minutes"]):
                        dur_val = float(row["interval_minutes"]) / 60.0
                    elif dur_val is None and (row.get("is_half_hourly") or row.get("granule_type") == "3B-HHR"):
                        dur_val = 0.5
                    elif dur_val is None and row.get("is_daily_mean_rate"):
                        dur_val = 24.0

                    if dur_val is None or pd.isna(dur_val):
                        raise AdapterPayloadError(
                            f"Ambiguous temporal interval for GPM precipitation rate ({raw_val} {raw_unit}) on {obs_date}. "
                            "Explicit 'duration_hours' or 'interval_minutes' is required. Blindly assuming 24 hours is prohibited."
                        )

                    dur_hours = float(dur_val)
                    accum_val = cls.convert_rate_to_accumulation(float(raw_val), duration_hours=dur_hours)
                    temporal_sem = f"converted_rate_{dur_hours}h"
                    interval_h = dur_hours
            else:
                raise AdapterPayloadError(f"Unsupported GPM precipitation unit '{raw_unit}' on date {obs_date}.")

            val_clean, q_status, review_flag = cls.validate_rainfall_value(accum_val)

            if q_status == QualityStatus.MISSING:
                missing_cnt += 1
            else:
                valid_cnt += 1

            observations.append(
                ObservationRecord(
                    date=obs_date,
                    rainfall_mm=val_clean,
                    raw_value=float(raw_val) if pd.notna(raw_val) else None,
                    raw_units=raw_unit,
                    temporal_semantics=temporal_sem,
                    interval_hours=interval_h,
                    quality_status=q_status,
                    review_flag=review_flag,
                )
            )

        date_range = None
        if observations:
            date_range = {"start": str(observations[0].date), "end": str(observations[-1].date)}

        return AdapterResponse(
            source_id=cls.METADATA.source_id,
            region_id=clean_id,
            status=SourceConnectionStatus.CONNECTED,
            dataset_type=cls.METADATA.dataset_type,
            product_version=run_meta["product_id"],
            units=cls.METADATA.default_units,
            observations=observations,
            records_count=len(observations),
            valid_count=valid_cnt,
            missing_count=missing_cnt,
            date_range=date_range,
            metadata=run_meta,
        )

    @classmethod
    def validate_payload(cls, raw_payload: Any) -> Dict[str, Any]:
        """
        Validates GPM IMERG payload structure, columns, and physical bounds.
        """
        if isinstance(raw_payload, list):
            df = pd.DataFrame(raw_payload)
        elif isinstance(raw_payload, pd.DataFrame):
            df = raw_payload
        else:
            raise AdapterPayloadError("Expected list of records or DataFrame for GPM payload.")

        for required in ["date", "rainfall_mm"]:
            if required not in df.columns:
                raise AdapterPayloadError(f"Missing required GPM column: '{required}'")

        # Check negative
        invalid_mask = df["rainfall_mm"] < 0.0
        if invalid_mask.any():
            raise AdapterPayloadError(f"Payload contains {invalid_mask.sum()} negative rainfall values.")

        return {
            "total_records": len(df),
            "max_precipitation_mm": round(float(df["rainfall_mm"].max()), 2) if not df.empty else 0.0,
            "provisional_extremes": int((df["rainfall_mm"] > 500.0).sum()),
        }
