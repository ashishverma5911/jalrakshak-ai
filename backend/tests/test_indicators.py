import pytest
import pandas as pd
import numpy as np

from app.engine.indicators import (
    calculate_cumulative_rainfall,
    calculate_rainfall_anomaly,
    count_wet_days,
    calculate_max_consecutive_dry_days,
    calculate_historical_percentile,
)
from app.engine.spi import SPIEngine

def test_calculate_cumulative_rainfall():
    df = pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=10, freq="D"),
        "rainfall_mm": [10.0] * 10,  # 10 mm each day
    })
    # 7-day sum should be 70 mm
    total_7d = calculate_cumulative_rainfall(df, window_days=7)
    assert total_7d == 70.0

    # 3-day sum should be 30 mm
    total_3d = calculate_cumulative_rainfall(df, window_days=3)
    assert total_3d == 30.0

def test_calculate_rainfall_anomaly():
    # Observed 200, Baseline 100 -> +100%
    assert calculate_rainfall_anomaly(200.0, 100.0) == 100.0

    # Observed 50, Baseline 100 -> -50%
    assert calculate_rainfall_anomaly(50.0, 100.0) == -50.0

    # Observed 100, Baseline 100 -> 0%
    assert calculate_rainfall_anomaly(100.0, 100.0) == 0.0

def test_count_wet_days():
    df = pd.DataFrame({
        "rainfall_mm": [1.0, 2.5, 5.0, 0.0, 10.0, 2.4, 3.0]
    })
    # Wet day threshold >= 2.5mm: 2.5, 5.0, 10.0, 3.0 = 4 wet days
    wet = count_wet_days(df, threshold_mm=2.5)
    assert wet == 4

def test_calculate_max_consecutive_dry_days():
    # 0.0, 0.5 (dry), 10.0 (wet), 0.0, 0.0, 0.0 (3 dry), 5.0 (wet), 0.0 (1 dry)
    df = pd.DataFrame({
        "rainfall_mm": [0.0, 0.5, 10.0, 0.0, 0.0, 0.0, 5.0, 0.0]
    })
    max_dry = calculate_max_consecutive_dry_days(df, dry_threshold_mm=1.0)
    assert max_dry == 3

def test_spi_engine_calculation():
    # 36 months of synthetic rainfall
    np.random.seed(42)
    synthetic_monthly = pd.Series(np.random.gamma(shape=2.0, scale=40.0, size=36))

    spi_val, category, meta = SPIEngine.calculate_spi_3(synthetic_monthly)

    # SPI should be finite float typically between -3.5 and +3.5
    assert isinstance(spi_val, float)
    assert -4.0 <= spi_val <= 4.0
    assert category in [
        "Extremely Wet", "Very Wet", "Moderately Wet",
        "Near Normal", "Moderately Dry", "Severely Dry", "Extremely Dry"
    ]
    assert "gamma_shape_alpha" in meta
    assert "gamma_scale_beta" in meta
