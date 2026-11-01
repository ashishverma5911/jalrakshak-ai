import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

def calculate_cumulative_rainfall(
    df: pd.DataFrame,
    window_days: int,
    reference_date: Optional[str] = None,
    date_col: str = "date",
    val_col: str = "rainfall_mm",
) -> Optional[float]:
    """
    Computes total cumulative rainfall (mm) over the last `window_days` preceding `reference_date`.
    Preserves genuine observed zero rainfall as 0.0.
    Returns None if dataset is empty or all observations in window are missing/null.
    Excludes missing values from the summation.
    """
    if df.empty:
        return None

    df_sorted = df.sort_values(by=date_col).copy()
    if reference_date:
        ref_dt = pd.to_datetime(reference_date)
        df_sorted = df_sorted[df_sorted[date_col] <= ref_dt]

    if df_sorted.empty:
        return None

    recent_slice = df_sorted.tail(window_days)
    valid_slice = recent_slice[val_col].dropna()
    if valid_slice.empty:
        return None

    return round(float(valid_slice.sum()), 2)

def calculate_rainfall_anomaly(
    observed_mm: Optional[float],
    baseline_mean_mm: float,
) -> Optional[float]:
    """
    Percentage anomaly relative to historical baseline:
    ((Observed - Baseline) / Baseline) * 100
    Returns None if observed_mm is None or baseline <= 0.
    Preserves genuine observed zero rainfall (0.0) -> -100.0%.
    """
    if observed_mm is None or baseline_mean_mm <= 0:
        return None
    return round(((observed_mm - baseline_mean_mm) / baseline_mean_mm) * 100.0, 1)

def count_wet_days(
    df: pd.DataFrame,
    threshold_mm: float = 2.5,
    window_days: Optional[int] = None,
    val_col: str = "rainfall_mm",
) -> Optional[int]:
    """
    Count of days with rainfall >= threshold_mm (IMD standard defines wet day >= 2.5mm).
    Returns None if dataset has no valid observations in window.
    Excludes missing values.
    """
    if df.empty:
        return None
    sub_df = df.tail(window_days) if window_days else df
    valid_vals = sub_df[val_col].dropna()
    if valid_vals.empty:
        return None
    return int((valid_vals >= threshold_mm).sum())

def calculate_max_consecutive_dry_days(
    df: pd.DataFrame,
    dry_threshold_mm: float = 1.0,
    window_days: Optional[int] = None,
    val_col: str = "rainfall_mm",
) -> Optional[int]:
    """
    Computes maximum consecutive days where daily rainfall is below dry_threshold_mm (< 1.0mm).
    Returns None if dataset has no valid observations.
    Excludes missing values.
    """
    if df.empty:
        return None

    sub_df = df.tail(window_days) if window_days else df
    valid_vals = sub_df[val_col].dropna()
    if valid_vals.empty:
        return None

    is_dry = (valid_vals < dry_threshold_mm).astype(int).values

    max_dry = 0
    current_dry = 0
    for val in is_dry:
        if val == 1:
            current_dry += 1
            if current_dry > max_dry:
                max_dry = current_dry
        else:
            current_dry = 0
    return int(max_dry)

def calculate_historical_percentile(
    series: pd.Series,
    target_value: Optional[float]
) -> Optional[float]:
    """
    Computes empirical percentile rank (0 to 100) of target_value within the historical series.
    Returns None if target_value is None or series has no valid observations.
    """
    if target_value is None:
        return None
    valid_series = series.dropna()
    if valid_series.empty:
        return None
    return round(float((valid_series < target_value).mean() * 100.0), 1)
