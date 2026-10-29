import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

from app.pipeline.validation import DataValidator, DataValidationError

def test_validate_timestamp_valid():
    ts1 = "2026-10-28T10:30:00Z"
    dt1 = DataValidator.validate_timestamp(ts1)
    assert dt1.year == 2026
    assert dt1.month == 10
    assert dt1.day == 28

    ts2 = "2026-10-28"
    dt2 = DataValidator.validate_timestamp(ts2)
    assert dt2.year == 2026
    assert dt2.month == 10
    assert dt2.day == 28

def test_validate_timestamp_invalid():
    with pytest.raises(DataValidationError):
        DataValidator.validate_timestamp("not-a-valid-date")

def test_validate_units():
    # Valid units
    DataValidator.validate_units("mm")
    DataValidator.validate_units("mm/day")
    DataValidator.validate_units("meters")

    # Invalid units
    with pytest.raises(DataValidationError):
        DataValidator.validate_units("inches_uncalibrated")

def test_staleness_detection():
    now = datetime.now(timezone.utc)
    # 5 hours old -> not stale
    fresh_time = now - timedelta(hours=5)
    is_stale, age = DataValidator.check_staleness(fresh_time, threshold_hours=24.0)
    assert not is_stale
    assert age < 6.0

    # 30 hours old -> stale
    stale_time = now - timedelta(hours=30)
    is_stale, age = DataValidator.check_staleness(stale_time, threshold_hours=24.0)
    assert is_stale
    assert age >= 30.0

def test_clean_rainfall_df_duplicates_and_missing():
    raw_data = {
        "date": ["2026-10-01", "2026-10-02", "2026-10-02", "2026-10-03", "2026-10-04"],
        "rainfall_mm": [10.0, 25.0, 30.0, None, -5.0],  # Duplicate on Oct 2, missing on Oct 3, negative on Oct 4
    }
    df = pd.DataFrame(raw_data)

    clean_df, report = DataValidator.validate_and_clean_rainfall_df(df)

    # 1 duplicate removed -> 4 rows remaining
    assert len(clean_df) == 4
    assert report["duplicates_removed"] == 1
    # Oct 3 missing filled with 0.0
    assert clean_df.loc[clean_df["date"] == "2026-10-03", "rainfall_mm"].values[0] == 0.0
    # Oct 4 negative clamped to 0.0
    assert clean_df.loc[clean_df["date"] == "2026-10-04", "rainfall_mm"].values[0] == 0.0
    # Duplicate kept last value (30.0)
    assert clean_df.loc[clean_df["date"] == "2026-10-02", "rainfall_mm"].values[0] == 30.0
