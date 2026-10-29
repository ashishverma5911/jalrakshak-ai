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
) -> float:
    """
    Computes total cumulative rainfall (mm) over the last `window_days` preceding `reference_date`.
    """
    if df.empty:
        return 0.0

    df_sorted = df.sort_values(by=date_col).copy()
    if reference_date:
        ref_dt = pd.to_datetime(reference_date)
        df_sorted = df_sorted[df_sorted[date_col] <= ref_dt]

    if df_sorted.empty:
        return 0.0

    recent_slice = df_sorted.tail(window_days)
    return round(float(recent_slice[val_col].sum()), 2)

def calculate_rainfall_anomaly(
    observed_mm: float,
    baseline_mean_mm: float,
) -> float:
    """
    Percentage anomaly relative to historical baseline:
    ((Observed - Baseline) / Baseline) * 100
    """
    if baseline_mean_mm <= 0:
        return 0.0
    return round(((observed_mm - baseline_mean_mm) / baseline_mean_mm) * 100.0, 1)

def count_wet_days(
    df: pd.DataFrame,
    threshold_mm: float = 2.5,
    window_days: Optional[int] = None,
    val_col: str = "rainfall_mm",
) -> int:
    """
    Count of days with rainfall >= threshold_mm (IMD standard defines wet day >= 2.5mm).
    """
    if df.empty:
        return 0
    sub_df = df.tail(window_days) if window_days else df
    return int((sub_df[val_col] >= threshold_mm).sum())

def calculate_max_consecutive_dry_days(
    df: pd.DataFrame,
    dry_threshold_mm: float = 1.0,
    window_days: Optional[int] = None,
    val_col: str = "rainfall_mm",
) -> int:
    """
    Computes maximum consecutive days where daily rainfall is below dry_threshold_mm (< 1.0mm).
    """
    if df.empty:
        return 0

    sub_df = df.tail(window_days) if window_days else df
    is_dry = (sub_df[val_col] < dry_threshold_mm).astype(int).values

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
    target_value: float
) -> float:
    """
    Computes empirical percentile rank (0 to 100) of target_value within the historical series.
    """
    if series.empty:
        return 50.0
    return round(float((series < target_value).mean() * 100.0), 1)
