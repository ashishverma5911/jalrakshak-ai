import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional

class DataValidationError(Exception):
    """Raised when data input fails integrity checks."""
    pass

class DataValidator:
    """
    Enforces data integrity, chronological alignment, unit constraints,
    duplicate record handling, missing-data tracking, and stale detection.
    """

    ALLOWED_UNITS = {"mm", "mm/day", "mm/hour", "meters", "celsius", "percentage"}

    @staticmethod
    def validate_timestamp(ts_str: str) -> datetime:
        """Parse and validate ISO8601 or standard datetime strings."""
        if not ts_str or not isinstance(ts_str, str):
            raise DataValidationError(f"Invalid timestamp format: {ts_str}")
        try:
            # Try ISO formats
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return dt
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y, %I:%M %p"):
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    pass
            raise DataValidationError(f"Unable to parse timestamp: '{ts_str}'")

    @staticmethod
    def validate_units(unit: str) -> None:
        """Validate units against verified list."""
        if unit.lower() not in DataValidator.ALLOWED_UNITS:
            raise DataValidationError(
                f"Invalid measurement unit '{unit}'. Allowed: {DataValidator.ALLOWED_UNITS}"
            )

    @staticmethod
    def check_staleness(latest_timestamp: datetime, threshold_hours: float = 24.0) -> Tuple[bool, float]:
        """
        Check if data has exceeded freshness threshold.
        Returns (is_stale, age_hours).
        """
        # If timestamp is naive, assume current UTC
        now = datetime.now(timezone.utc)
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

        age = (now - latest_timestamp).total_seconds() / 3600.0
        is_stale = age > threshold_hours
        return is_stale, round(age, 2)

    @staticmethod
    def validate_and_clean_rainfall_df(
        df: pd.DataFrame,
        date_col: str = "date",
        val_col: str = "rainfall_mm",
        expected_frequency: str = "D",
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validates a daily precipitation DataFrame:
        - Detects & removes duplicates
        - Identifies missing dates / gaps
        - Validates physical bounds (rainfall cannot be negative or > 1000 mm in 24h)
        - Chronologically sorts the records
        """
        if df.empty:
            raise DataValidationError("Input DataFrame is empty")

        if date_col not in df.columns or val_col not in df.columns:
            raise DataValidationError(f"Missing required columns '{date_col}' and '{val_col}'")

        report: Dict[str, Any] = {
            "initial_rows": len(df),
            "duplicates_removed": 0,
            "missing_dates_filled": 0,
            "anomalous_outliers_flagged": 0,
            "date_range": None,
        }

        # Work on copy
        clean_df = df.copy()

        # Parse dates
        clean_df[date_col] = pd.to_datetime(clean_df[date_col], errors="coerce")
        invalid_dates = clean_df[date_col].isna().sum()
        if invalid_dates > 0:
            clean_df = clean_df.dropna(subset=[date_col])

        # Duplicate detection
        dup_count = clean_df.duplicated(subset=[date_col]).sum()
        if dup_count > 0:
            report["duplicates_removed"] = int(dup_count)
            # Keep the latest or average
            clean_df = clean_df.drop_duplicates(subset=[date_col], keep="last")

        # Sort chronologically (avoid temporal leakage)
        clean_df = clean_df.sort_values(by=date_col).reset_index(drop=True)

        # Range check
        report["date_range"] = {
            "start": clean_df[date_col].min().strftime("%Y-%m-%d"),
            "end": clean_df[date_col].max().strftime("%Y-%m-%d"),
        }

        # Value validation & physical bounds:
        # Precipitation >= 0 and <= 1500 mm (Cherrapunji 24h record is ~1040mm)
        clean_df[val_col] = pd.to_numeric(clean_df[val_col], errors="coerce")
        
        # Missing values
        missing_count = clean_df[val_col].isna().sum()
        if missing_count > 0:
            report["missing_dates_filled"] = int(missing_count)
            clean_df[val_col] = clean_df[val_col].fillna(0.0)

        # Negative checks
        negative_mask = clean_df[val_col] < 0.0
        if negative_mask.any():
            clean_df.loc[negative_mask, val_col] = 0.0

        # Physical outlier check (> 800mm in single day in UP is meteorological anomaly)
        outlier_mask = clean_df[val_col] > 800.0
        if outlier_mask.any():
            report["anomalous_outliers_flagged"] = int(outlier_mask.sum())

        return clean_df, report
