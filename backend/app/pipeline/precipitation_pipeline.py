"""
Precipitation Ingestion & Scientific Validation Pipeline for JalRakshak AI
Features:
- Scientific rainfall validation:
  * Rejects negative precipitation (< 0.0 mm)
  * Flags precipitation > 500.0 mm as 'provisional_extreme' for scientific review
  * Preserves NULL/missing observations with quality_status='missing'
  * Differentiates true zero measurements ('zero_precipitation') from observed rain ('observed')
- Idempotent upserting on composite key (region_id, observation_date)
- Strict provenance metadata recording (distinguishes real observed, calibrated prototype, and missing data)
"""
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from ..db.models import Region, DailyPrecipitation

logger = logging.getLogger("jalrakshak.pipeline.precipitation")


class PrecipitationValidationError(ValueError):
    """Raised when rainfall observation fails physical or schema validation."""
    pass


class PrecipitationIngestionService:
    """
    Ingests, validates, and manages daily precipitation observations.
    """

    @classmethod
    def validate_observation(
        cls,
        rainfall_val: Any,
    ) -> Tuple[Optional[float], str]:
        """
        Validates a single rainfall observation and returns (clean_value, quality_status).
        Rules:
        - NULL / NaN -> (None, 'missing')
        - < 0.0 -> raises PrecipitationValidationError (negative rainfall is invalid)
        - == 0.0 -> (0.0, 'zero_precipitation')
        - > 0.0 and <= 500.0 -> (clean_val, 'observed')
        - > 500.0 -> (clean_val, 'provisional_extreme') for review
        """
        if rainfall_val is None or pd.isna(rainfall_val):
            return None, "missing"

        try:
            val = float(rainfall_val)
        except (ValueError, TypeError):
            raise PrecipitationValidationError(f"Invalid non-numeric rainfall measurement: '{rainfall_val}'")

        if val < 0.0:
            raise PrecipitationValidationError(f"Negative rainfall value {val} mm is physically invalid and rejected.")

        if val == 0.0:
            return 0.0, "zero_precipitation"
        elif val > 500.0:
            logger.warning(f"Extreme precipitation observation detected: {val} mm/day. Flagged as provisional_extreme.")
            return round(val, 2), "provisional_extreme"
        else:
            return round(val, 2), "observed"

    @classmethod
    def ingest_records(
        cls,
        db: Session,
        region_id: str,
        records: List[Dict[str, Any]],
        default_source: str = "chirps_daily",
        is_demo_data: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingests a list of daily records into the daily_precipitation table.
        Each record must contain 'date' and 'rainfall_mm'.
        """
        region = db.query(Region).filter_by(id=region_id).first()
        if not region:
            raise PrecipitationValidationError(f"Cannot ingest rainfall: Region '{region_id}' not found.")

        stats = {
            "region_id": region_id,
            "total_processed": len(records),
            "inserted": 0,
            "updated": 0,
            "provisional_extreme": 0,
            "missing_stored": 0,
            "rejected_negative": 0,
        }

        for r in records:
            # Parse date
            d_val = r.get("date") or r.get("observation_date")
            if isinstance(d_val, str):
                obs_date = datetime.strptime(d_val.split("T")[0], "%Y-%m-%d").date()
            elif isinstance(d_val, (date, datetime)):
                obs_date = d_val if isinstance(d_val, date) else d_val.date()
            else:
                continue

            # Validate rainfall amount
            try:
                clean_mm, quality_status = cls.validate_observation(r.get("rainfall_mm"))
            except PrecipitationValidationError as e:
                logger.error(f"Rejected invalid observation on {obs_date} for {region_id}: {e}")
                stats["rejected_negative"] += 1
                continue

            if quality_status == "provisional_extreme":
                stats["provisional_extreme"] += 1
            elif quality_status == "missing":
                stats["missing_stored"] += 1

            source = r.get("source", default_source)
            meta = dict(r.get("metadata") or {})
            meta.update({
                "is_demo_data": is_demo_data,
                "units": "mm",
                "ingested_via": "PrecipitationIngestionService",
            })

            # Upsert into database
            existing = db.query(DailyPrecipitation).filter_by(
                region_id=region_id,
                observation_date=obs_date,
            ).first()

            if not existing:
                new_row = DailyPrecipitation(
                    region_id=region_id,
                    observation_date=obs_date,
                    rainfall_mm=clean_mm,
                    data_source=source,
                    quality_status=quality_status,
                    observation_metadata=meta,
                )
                db.add(new_row)
                stats["inserted"] += 1
            else:
                existing.rainfall_mm = clean_mm
                existing.quality_status = quality_status
                existing.data_source = source
                existing.observation_metadata = meta
                stats["updated"] += 1

        db.commit()
        logger.info(f"Precipitation ingestion completed for {region_id}: {stats}")
        return stats

    @classmethod
    def ingest_csv_file(
        cls,
        db: Session,
        csv_path: Path,
        region_id: str,
        default_source: str = "chirps_daily",
        is_demo_data: bool = False,
    ) -> Dict[str, Any]:
        """
        Parses and ingests a daily precipitation CSV file.
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"Rainfall CSV not found at {csv_path}")

        df = pd.read_csv(csv_path)
        records = df.to_dict(orient="records")
        return cls.ingest_records(
            db=db,
            region_id=region_id,
            records=records,
            default_source=default_source,
            is_demo_data=is_demo_data,
        )

    @classmethod
    def query_series(
        cls,
        db: Session,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries timeseries records for a region within an optional date range.
        Returns list of dictionary representations sorted chronologically.
        """
        query = db.query(DailyPrecipitation).filter(DailyPrecipitation.region_id == region_id)
        if start_date:
            query = query.filter(DailyPrecipitation.observation_date >= start_date)
        if end_date:
            query = query.filter(DailyPrecipitation.observation_date <= end_date)

        rows = query.order_by(DailyPrecipitation.observation_date.asc()).all()
        return [r.to_dict() for r in rows]
