import pytest
import pandas as pd
import numpy as np

from app.pipeline.ingestion import DataIngestionService
from app.engine.indicators import calculate_cumulative_rainfall, calculate_rainfall_anomaly
from app.engine.drought_engine import DroughtRiskEngine


@pytest.fixture
def ingestion_service():
    return DataIngestionService()


def test_indicators_function_calendar_window_validation():
    """
    Unit tests for calculate_cumulative_rainfall:
    - Empty DataFrame returns None.
    - String dates are converted cleanly without TypeError.
    - Slices with fewer than min_days valid calendar days return None.
    - Slices with missing days (NaN) are NOT treated as zero rainfall.
    - Slices with full min_days return the correct sum.
    - Without min_days (backward compatibility), functions as tail-slice.
    """
    # 1. Empty DataFrame
    empty_df = pd.DataFrame(columns=["date", "rainfall_mm"])
    assert calculate_cumulative_rainfall(empty_df, 90, min_days=90) is None

    # 2. String dates conversion
    str_df = pd.DataFrame([
        {"date": "2026-10-27", "rainfall_mm": 10.0},
        {"date": "2026-10-28", "rainfall_mm": 5.0},
    ])
    assert calculate_cumulative_rainfall(str_df, 2, reference_date="2026-10-28", min_days=2) == 15.0

    # 3. 8 days with min_days=90 -> returns None
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [2.0] * 8})
    assert calculate_cumulative_rainfall(df_8d, 90, reference_date="2026-10-28", min_days=90) is None

    # 4. 89 days with min_days=90 -> returns None
    dates_89d = pd.date_range(end="2026-10-28", periods=89, freq="D")
    df_89d = pd.DataFrame({"date": dates_89d, "rainfall_mm": [2.0] * 89})
    assert calculate_cumulative_rainfall(df_89d, 90, reference_date="2026-10-28", min_days=90) is None

    # 5. 90 calendar days with 5 missing (NaN) days -> returns None (missing days NOT treated as 0)
    dates_90d = pd.date_range(end="2026-10-28", periods=90, freq="D")
    vals = [2.0] * 85 + [np.nan] * 5
    df_missing_vals = pd.DataFrame({"date": dates_90d, "rainfall_mm": vals})
    assert calculate_cumulative_rainfall(df_missing_vals, 90, reference_date="2026-10-28", min_days=90) is None

    # 6. 90 valid days with min_days=90 -> returns sum
    df_valid_90 = pd.DataFrame({"date": dates_90d, "rainfall_mm": [2.0] * 90})
    assert calculate_cumulative_rainfall(df_valid_90, 90, reference_date="2026-10-28", min_days=90) == 180.0

    # 7. Backward compatibility without min_days
    assert calculate_cumulative_rainfall(df_8d, 90) == 16.0


def test_live_mode_short_window_returns_null_and_missing_status(ingestion_service):
    """
    Requirement 1, 2, 3:
    In live mode with typical 8-day cache (7 past days + current day):
    - Do not expose short-window sum as 90-day accumulation.
    - Returns null for 90-day accumulation and 90-day anomaly.
    - Explicit quality_status is 'missing'.
    - category is preserved as 'model_derived'.
    - Attribution is preserved as Open-Meteo Forecast API.
    - Does not trigger false severe drought risk.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [0.0] * 8})

    result = DroughtRiskEngine.evaluate(m_info, df_8d, reference_date="2026-10-28", mode="live")

    assert result.data_mode == "LIVE_MODEL"
    assert result.is_demo_data is False
    assert result.hazard == "drought"
    assert result.location.location_id == "mahoba"

    ind_map = {ind.indicator_id: ind for ind in result.indicators}

    # 90-day accumulation must be null and missing
    r90 = ind_map["drought_precip_90d_accum"]
    assert r90.value is None, f"Expected None for 90d accum with 8 days of data, got {r90.value}"
    assert r90.quality_status == "missing"
    assert r90.category == "model_derived"
    assert r90.is_data_available is False
    assert "insufficient historical coverage" in r90.limitations
    assert "Open-Meteo" in r90.dataset_version

    # 90-day anomaly must be null and missing
    anom90 = ind_map["drought_precip_90d_anomaly"]
    assert anom90.value is None, f"Expected None for 90d anomaly with 8 days of data, got {anom90.value}"
    assert anom90.quality_status == "missing"
    assert anom90.is_data_available is False
    assert "uncalculated due to insufficient observation coverage" in anom90.limitations

    # Seasonal deficit must be null and missing (no Kharif monsoon data in October 8d window)
    s_def = ind_map["drought_seasonal_deficit"]
    assert s_def.value is None
    assert s_def.quality_status == "missing"
    assert s_def.is_data_available is False

    # Risk level without official alert escalation must NOT be high due to missing data
    from unittest.mock import patch
    with patch("app.engine.drought_engine.OfficialAlertsPipeline.get_district_official_alert", return_value={"alert_level": "Green"}):
        result_green = DroughtRiskEngine.evaluate(m_info, df_8d, reference_date="2026-10-28", mode="live")
        assert result_green.risk_level == "low", f"Expected 'low' risk with Green advisory and missing data, got {result_green.risk_level}"


def test_regression_audited_false_100_percent_anomaly_prevented(ingestion_service):
    """
    Regression test reproducing the audited defect:
    An 8-day live window of 0.0 mm rainfall previously produced:
    - 90-day accumulation = 0.0 mm
    - 90-day anomaly = ((0.0 - 453.6) / 453.6) * 100 = -100.0%
    - Triggered severe high drought risk erroneously.

    Verify that with the safety fix:
    - Accumulation is None (NOT 0.0 mm).
    - Anomaly is None (NOT -100.0%).
    - Quality status is 'missing'.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [0.0] * 8})

    result = DroughtRiskEngine.evaluate(m_info, df_8d, reference_date="2026-10-28", mode="live")
    ind_map = {ind.indicator_id: ind for ind in result.indicators}

    # Verify false -100.0% anomaly is prevented
    assert ind_map["drought_precip_90d_accum"].value is not None or ind_map["drought_precip_90d_accum"].value is None
    assert ind_map["drought_precip_90d_accum"].value is None, "Must NOT sum incomplete window as 0.0"
    assert ind_map["drought_precip_90d_anomaly"].value is None, "Must NOT calculate -100.0% anomaly from 8 days of zero rainfall"
    assert ind_map["drought_precip_90d_anomaly"].value != -100.0


def test_missing_days_not_treated_as_zero_rainfall(ingestion_service):
    """
    Requirement 9: Missing days must not be treated as zero rainfall.
    A 90-day calculation window with 75 observations and 15 missing days
    must fail coverage check and return None for accumulation and anomaly.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_90d = pd.date_range(end="2026-10-28", periods=90, freq="D")
    # 75 days with 5.0mm, 15 days missing (NaN)
    rainfall_series = [5.0] * 75 + [np.nan] * 15
    df_sparse = pd.DataFrame({"date": dates_90d, "rainfall_mm": rainfall_series})

    result = DroughtRiskEngine.evaluate(m_info, df_sparse, reference_date="2026-10-28", mode="live")
    ind_map = {ind.indicator_id: ind for ind in result.indicators}

    assert ind_map["drought_precip_90d_accum"].value is None
    assert ind_map["drought_precip_90d_accum"].quality_status == "missing"
    assert ind_map["drought_precip_90d_anomaly"].value is None
    assert ind_map["drought_precip_90d_anomaly"].quality_status == "missing"


def test_live_mode_90_valid_days_calculates_metric(ingestion_service):
    """
    Requirement 4 & 9:
    If 90 valid calendar days ARE present in live mode:
    - Calculates the 90-day accumulation.
    - Category is model_derived.
    - Quality status is provisional.
    - Correct Open-Meteo attribution.
    - Calculates the 90-day anomaly against climatological baseline.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_90d = pd.date_range(end="2026-10-28", periods=90, freq="D")
    df_90d = pd.DataFrame({"date": dates_90d, "rainfall_mm": [2.0] * 90})

    result = DroughtRiskEngine.evaluate(m_info, df_90d, reference_date="2026-10-28", mode="live")
    ind_map = {ind.indicator_id: ind for ind in result.indicators}

    r90 = ind_map["drought_precip_90d_accum"]
    assert r90.value == 180.0
    assert r90.category == "model_derived"
    assert r90.quality_status == "provisional"
    assert r90.is_data_available is True
    assert "Open-Meteo" in r90.dataset_version

    anom90 = ind_map["drought_precip_90d_anomaly"]
    assert anom90.value is not None
    # 180 mm vs ~453.6 mm baseline = ~ -60.3%
    assert anom90.value == pytest.approx(-60.3, abs=0.5)
    assert anom90.quality_status == "provisional"
    assert anom90.is_data_available is True


def test_verified_mode_retains_valid_behavior(ingestion_service):
    """
    Requirement 5 & 9:
    In verified mode with genuine CHIRPS data:
    - Retains existing valid calculation.
    - Accumulation is calculated (719.7 mm).
    - Category is observed_measurement.
    - Quality status is verified.
    - Attribution is CHIRPS v2.0.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    verified_df = ingestion_service.load_daily_rainfall("mahoba", mode="verified")

    result = DroughtRiskEngine.evaluate(m_info, verified_df, reference_date="2026-10-28", mode="verified")
    assert result.data_mode == "CACHED_VERIFIED"
    assert result.is_demo_data is False

    ind_map = {ind.indicator_id: ind for ind in result.indicators}

    r90 = ind_map["drought_precip_90d_accum"]
    assert r90.value == 719.7
    assert r90.category == "observed_measurement"
    assert r90.quality_status == "verified"
    assert r90.is_data_available is True
    assert "CHIRPS" in r90.dataset_version

    anom90 = ind_map["drought_precip_90d_anomaly"]
    assert anom90.value is not None
    assert anom90.quality_status == "verified"
    assert anom90.is_data_available is True

    # Kharif monsoon seasonal departure should also be calculated in verified mode
    s_def = ind_map["drought_seasonal_deficit"]
    assert s_def.value is not None
    assert s_def.quality_status == "verified"
    assert s_def.is_data_available is True
