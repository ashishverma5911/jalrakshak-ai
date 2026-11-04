"""
Phase 3C.5.1: Risk Attribution & Data Completeness Test Suite

Validates:
1. Operational assessment on 4 November with expired October advisory -> 'pending'.
2. Historical replay on 28 October -> historical 'high', explicitly identified as replay.
3. Historical replay never reports is_currently_active=True on 4 November.
4. generated_at always represents actual server execution time in UTC.
5. Missing 90-day indicators plus expired advisory -> 'pending', never 'low'.
6. Sufficient required meteorological evidence establishing normal conditions -> 'low'.
7. Valid active Orange advisory -> 'high'.
8. Valid independent dry-spell threshold (>= 25 days) -> 'moderate', even with short cache.
9. Verified CHIRPS mode retains valid classification ('moderate') and 'complete' coverage.
10. Candidate districts remain 'pending'.
11. Advisory validity boundaries across all 6 dates: 30 Sep, 1 Oct, 28 Oct, 31 Oct, 1 Nov, 4 Nov.
12. Flood engine functionality preserved intact.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch

from app.pipeline.ingestion import DataIngestionService
from app.pipeline.official_alerts import OfficialAlertsPipeline
from app.engine.drought_engine import DroughtRiskEngine
from app.engine.flood_engine import FloodRiskEngine
from app.schemas.common import OfficialAdvisoryReference, HazardAssessmentResponse


@pytest.fixture
def ingestion_service():
    return DataIngestionService()


# ---------------------------------------------------------------------------
# 1. Official Advisory Boundary & Validity Testing (All 6 Dates)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "assessment_date,expected_valid,expected_status,expected_alert_level",
    [
        ("2026-09-30T23:59:59Z", False, "pending_effective", "None"),
        ("2026-10-01T00:00:00Z", True, "historical_active", "Orange"),
        ("2026-10-28T12:00:00Z", True, "historical_active", "Orange"),
        ("2026-10-31T23:59:59Z", True, "historical_active", "Orange"),
        ("2026-11-01T00:00:00Z", False, "historical_expired", "None"),
        ("2026-11-04T14:00:00Z", False, "expired", "None"),
    ],
)
def test_mahoba_advisory_validity_boundaries(
    assessment_date, expected_valid, expected_status, expected_alert_level
):
    """
    Test exact boundary transitions for Mahoba UPSDMA Orange Advisory
    (valid_from: 2026-10-01T00:00:00Z, valid_to: 2026-10-31T23:59:59Z).
    """
    result = OfficialAlertsPipeline.validate_district_advisory(
        "district-mahoba", assessment_timestamp=assessment_date
    )

    assert result["region_id"] == "district-mahoba"
    assert result["bulletin_id"] == "UPSDMA-BDK-2026-OCT-MHB-03"
    assert result["is_valid"] is expected_valid
    assert result["status"] == expected_status
    assert result["alert_level"] == expected_alert_level
    assert result["bulletin_alert_level"] == "Orange"
    assert result["verification_status"] == "manually_verified"
    # On 4 November 2026, the October bulletin is strictly not active in real time
    assert result["is_currently_active"] is False


def test_advisory_unverified_status_rejected():
    """An advisory in registry not marked manually_verified must fail validation."""
    fake_registry = {
        "district-test": {
            "region_id": "district-test",
            "authority": "Test Authority",
            "bulletin_id": "TEST-01",
            "alert_level": "Red",
            "valid_from": "2026-10-01T00:00:00Z",
            "valid_to": "2026-10-31T23:59:59Z",
            "status": "data_pending",
            "advisory_text": "Unverified draft alert",
        }
    }
    with patch.dict(OfficialAlertsPipeline._VERIFIED_ADVISORIES, fake_registry, clear=False):
        result = OfficialAlertsPipeline.validate_district_advisory(
            "district-test", assessment_timestamp="2026-10-15T12:00:00Z"
        )
        assert result["is_valid"] is False
        assert result["alert_level"] == "None"
        assert result["status"] == "unverified"
        assert result["verification_status"] == "data_pending"
        assert result["is_currently_active"] is False


def test_advisory_missing_metadata_rejected():
    """An advisory missing valid_from or valid_to must fail validation."""
    fake_registry = {
        "district-test-nometadata": {
            "region_id": "district-test-nometadata",
            "authority": "Test Authority",
            "bulletin_id": "TEST-NO-METADATA",
            "alert_level": "Red",
            "valid_from": None,
            "valid_to": None,
            "status": "manually_verified",
            "advisory_text": "Alert without timestamps",
        }
    }
    with patch.dict(OfficialAlertsPipeline._VERIFIED_ADVISORIES, fake_registry, clear=False):
        result = OfficialAlertsPipeline.validate_district_advisory(
            "district-test-nometadata", assessment_timestamp="2026-10-15T12:00:00Z"
        )
        assert result["is_valid"] is False
        assert result["alert_level"] == "None"
        assert result["status"] == "metadata_missing"
        assert result["is_currently_active"] is False


def test_candidate_district_advisory_unlinked():
    """Candidate district without registered advisories returns unlinked data_pending."""
    result = OfficialAlertsPipeline.validate_district_advisory(
        "district-gaya", assessment_timestamp="2026-10-28T12:00:00Z"
    )
    assert result["is_valid"] is False
    assert result["alert_level"] == "None"
    assert result["status"] == "data_pending"
    assert result["verification_status"] == "data_pending"
    assert result["bulletin_id"] is None
    assert result["is_currently_active"] is False


# ---------------------------------------------------------------------------
# 2. Phase 3C.5.1 Core Requirements: Operational vs Historical Replay
# ---------------------------------------------------------------------------
def test_operational_nov4_expired_advisory_is_pending_never_low(ingestion_service):
    """
    Requirement 1 & 5:
    Operational assessment on 4 November with expired October advisory and short NWP cache:
    - Must evaluate to 'pending' (insufficient evidence), NEVER 'low'.
    - is_historical_replay is False.
    - official_advisory.is_currently_active is False.
    - generated_at matches current server execution timestamp.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [0.0] * 8})

    eval_nov4 = DroughtRiskEngine.evaluate(
        m_info,
        df_8d,
        reference_date="2026-10-28",
        mode="live",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )

    assert eval_nov4.risk_level == "pending", f"Expected 'pending' for insufficient data, got {eval_nov4.risk_level}"
    assert eval_nov4.is_historical_replay is False
    assert eval_nov4.official_advisory.is_valid is False
    assert eval_nov4.official_advisory.is_currently_active is False
    assert eval_nov4.official_advisory.alert_level == "None"
    assert eval_nov4.official_advisory.status == "expired"
    assert eval_nov4.data_completeness == "partial"
    assert eval_nov4.is_data_available is False
    assert "insufficient meteorological coverage" in eval_nov4.primary_risk_driver.lower()
    assert eval_nov4.generated_at[:10] == datetime.now(timezone.utc).isoformat()[:10]


def test_historical_replay_oct28_is_marked_replay(ingestion_service):
    """
    Requirement 2, 3 & 4:
    Historical replay on 28 October:
    - Returns high risk driven by Orange alert historically.
    - is_historical_replay is True.
    - official_advisory.is_currently_active is strictly False (today is 4 Nov).
    - official_advisory.status is 'historical_active', NEVER 'active'.
    - primary_risk_driver is prefixed with [Historical Replay: 2026-10-28].
    - generated_at remains actual server execution timestamp (NOT 2026-10-28).
    - Backdated assessment never masquerades as current active warning.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [0.0] * 8})

    eval_replay = DroughtRiskEngine.evaluate(
        m_info,
        df_8d,
        reference_date="2026-10-28",
        mode="live",
        assessment_timestamp="2026-10-28T12:00:00Z",
    )

    assert eval_replay.risk_level == "high"
    assert eval_replay.is_historical_replay is True
    assert eval_replay.assessment_timestamp == "2026-10-28T12:00:00+00:00"
    # generated_at must represent today's execution time, NOT 28 Oct
    assert eval_replay.generated_at[:10] == datetime.now(timezone.utc).isoformat()[:10]
    assert eval_replay.official_advisory.is_valid is True
    assert eval_replay.official_advisory.is_currently_active is False
    assert eval_replay.official_advisory.status == "historical_active"
    assert "[Historical Replay: 2026-10-28]" in eval_replay.primary_risk_driver
    assert "HISTORICAL REPLAY" in eval_replay.disclaimer


def test_historical_replay_never_reports_currently_active(ingestion_service):
    """Requirement 3: Replay with 28 Oct timestamp cannot report is_currently_active=True."""
    m_info = ingestion_service.get_district_info("mahoba")
    dates_8d = pd.date_range(end="2026-10-28", periods=8, freq="D")
    df_8d = pd.DataFrame({"date": dates_8d, "rainfall_mm": [0.0] * 8})

    eval_replay = DroughtRiskEngine.evaluate(
        m_info,
        df_8d,
        reference_date="2026-10-28",
        mode="live",
        assessment_timestamp="2026-10-28T12:00:00Z",
    )
    assert eval_replay.official_advisory.is_currently_active is False


# ---------------------------------------------------------------------------
# 3. Decision Logic & Scientific Defensibility
# ---------------------------------------------------------------------------
def test_sufficient_normal_meteorological_evidence_is_low(ingestion_service):
    """
    Requirement 6:
    When meteorological evidence is genuinely complete and demonstrates normal conditions:
    - seasonal deficit > -35%
    - SPI-3 > -1.2
    - dry spell < 25 days
    - risk_level evaluates to 'low'
    - data_completeness is 'complete'
    - is_data_available is True
    """
    m_info = ingestion_service.get_district_info("mahoba")

    # Generate synthetic multi-year series calibrated to Mahoba's normal climatology
    dates_multi = pd.date_range(start="2020-01-01", end="2026-10-28", freq="D")
    rainfall = []
    for d in dates_multi:
        if d.month == 6:
            rainfall.append(2.7)
        elif d.month in [7, 8]:
            rainfall.append(9.0)
        elif d.month == 9:
            rainfall.append(6.0)
        elif d.month == 10:
            rainfall.append(1.0)
        else:
            rainfall.append(0.5)

    df_adequate = pd.DataFrame({"date": dates_multi, "rainfall_mm": rainfall})

    eval_normal = DroughtRiskEngine.evaluate(
        m_info,
        df_adequate,
        reference_date="2026-10-28",
        mode="verified",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )

    ind_map = {ind.indicator_id: ind for ind in eval_normal.indicators}
    assert ind_map["drought_precip_90d_accum"].value is not None
    assert ind_map["drought_seasonal_deficit"].value is not None
    assert ind_map["drought_spi_3"].value is not None

    # Normal conditions with complete data produce genuine 'low' risk
    assert eval_normal.risk_level == "low"
    assert eval_normal.data_completeness == "complete"
    assert eval_normal.is_data_available is True
    assert "Normal antecedent precipitation" in eval_normal.primary_risk_driver


def test_independent_dry_spell_threshold_is_moderate(ingestion_service):
    """
    Requirement 8:
    Preserve independently valid dry_spell_days >= 25 as a moderate-risk contributor
    even when long-term indicators (90d, seasonal deficit, SPI-3) are incomplete.
    """
    m_info = ingestion_service.get_district_info("mahoba")

    # 30-day window with 28 consecutive dry days (< 1.0 mm/day)
    dates_30d = pd.date_range(end="2026-10-28", periods=30, freq="D")
    df_dry = pd.DataFrame({"date": dates_30d, "rainfall_mm": [0.0] * 30})

    eval_dry = DroughtRiskEngine.evaluate(
        m_info,
        df_dry,
        reference_date="2026-10-28",
        mode="live",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )

    ind_map = {ind.indicator_id: ind for ind in eval_dry.indicators}
    # 90d is None (< 90 days)
    assert ind_map["drought_precip_90d_accum"].value is None
    # dry spell is 30 days (>= 25)
    assert ind_map["drought_consecutive_dry_days"].value == 30.0

    # Must recognize valid independent moderate-risk signal
    assert eval_dry.risk_level == "moderate"
    assert eval_dry.data_completeness == "partial"
    assert eval_dry.is_data_available is False
    assert "Agricultural dry spell: 30 consecutive dry days" in eval_dry.primary_risk_driver


def test_verified_chirps_historical_retains_classification(ingestion_service):
    """
    Requirement 9:
    Verified CHIRPS multi-year data:
    - Operationally on 4 Nov (advisory expired): classifies as 'moderate'
      driven purely by CHIRPS physical data (Kharif deficit ~ -50.1% and SPI-3 ~ -1.82).
    - Historically on 28 Oct (advisory active): classifies as 'high'
      driven by the active UPSDMA Orange advisory with is_historical_replay=True.
    """
    m_info = ingestion_service.get_district_info("mahoba")
    verified_df = ingestion_service.load_daily_rainfall("mahoba", mode="verified")

    # Operational evaluation on 4 Nov 2026 (Orange advisory expired)
    eval_operational = DroughtRiskEngine.evaluate(
        m_info,
        verified_df,
        reference_date="2026-10-28",
        mode="verified",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )
    assert eval_operational.risk_level == "moderate"
    assert eval_operational.data_completeness == "complete"
    assert eval_operational.is_data_available is True
    assert eval_operational.is_historical_replay is False
    assert eval_operational.official_advisory.is_valid is False
    assert eval_operational.assessment_period == "90-Day Seasonal Deficit & SPI-3 Window"

    # Historical replay evaluation on 28 Oct 2026 (Orange advisory active)
    eval_hist = DroughtRiskEngine.evaluate(
        m_info,
        verified_df,
        reference_date="2026-10-28",
        mode="verified",
        assessment_timestamp="2026-10-28T12:00:00Z",
    )
    assert eval_hist.risk_level == "high"
    assert eval_hist.data_completeness == "complete"
    assert eval_hist.is_data_available is True
    assert eval_hist.is_historical_replay is True
    assert eval_hist.official_advisory.is_valid is True
    assert eval_hist.official_advisory.alert_level == "Orange"
    assert "[Historical Replay: 2026-10-28]" in eval_hist.primary_risk_driver


def test_candidate_districts_remain_pending():
    """
    Requirement 10:
    Candidate uncalibrated district (e.g. Gaya) remains 'pending' with 'pending' completeness.
    """
    gaya_info = {
        "id": "district-gaya",
        "name": "Gaya",
        "hindi_name": "गया",
        "lat": 24.7955,
        "lng": 85.0002,
        "elevation_m": 111.0,
        "river_basin": "Falgu",
        "region": "South Bihar",
        "is_pilot": False,
    }
    empty_df = pd.DataFrame(columns=["date", "rainfall_mm"])

    eval_candidate = DroughtRiskEngine.evaluate(
        gaya_info,
        empty_df,
        reference_date="2026-10-28",
        mode="live",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )

    assert eval_candidate.risk_level == "pending"
    assert eval_candidate.data_completeness == "pending"
    assert eval_candidate.is_data_available is False
    assert eval_candidate.assessment_period == "Data Ingestion Pending"
    assert eval_candidate.primary_risk_driver == "Candidate district: observational telemetry unlinked"
    assert eval_candidate.official_advisory.is_valid is False
    assert eval_candidate.official_advisory.is_currently_active is False


def test_flood_engine_gorakhpur_preservation(ingestion_service):
    """
    Requirement 12:
    Gorakhpur flood engine functionality preserved:
    - Evaluates 7-day and 30-day indicators correctly.
    - Gorakhpur Yellow alert on 4 November is expired (valid until 29 Oct).
    - Returns data_completeness == 'complete', is_data_available == True.
    """
    g_info = ingestion_service.get_district_info("gorakhpur")
    df = ingestion_service.load_daily_rainfall("gorakhpur", mode="demo")

    eval_flood = FloodRiskEngine.evaluate(
        g_info,
        df,
        reference_date="2026-10-28",
        mode="demo",
        assessment_timestamp="2026-11-04T14:00:00Z",
    )

    assert eval_flood.hazard == "flood"
    assert eval_flood.data_completeness == "complete"
    assert eval_flood.is_data_available is True
    assert eval_flood.official_advisory is not None
    assert eval_flood.official_advisory.is_valid is False
    assert eval_flood.official_advisory.is_currently_active is False
    assert eval_flood.official_advisory.alert_level == "None"
    assert eval_flood.primary_risk_driver is not None
    assert eval_flood.generated_at[:10] == datetime.now(timezone.utc).isoformat()[:10]
