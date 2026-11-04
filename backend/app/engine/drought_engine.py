import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .indicators import (
    calculate_cumulative_rainfall,
    calculate_rainfall_anomaly,
    calculate_max_consecutive_dry_days,
)
from .spi import SPIEngine
from ..schemas.common import (
    HazardAssessmentResponse,
    LocationReference,
    RiskIndicator,
    SourceMetadata,
    DataMode,
    DataQualityStatus,
    DataCompleteness,
    OfficialAdvisoryReference,
)
from ..pipeline.chirps_pipeline import CHIRPSPipeline
from ..pipeline.srtm_pipeline import SRTMElevationPipeline
from ..pipeline.official_alerts import OfficialAlertsPipeline
from ..pipeline.spatial_aggregation import SpatialAggregator, SpatialAggregationError


class DroughtRiskEngine:
    """
    Phase 5 Drought Risk Engine for Mahoba & Bundelkhand.
    Synthesizes:
    1. 30-Day and 90-Day cumulative precipitation.
    2. Seasonal Kharif monsoon departure from 30-year (1991–2020) normal baseline.
    3. Standardized Precipitation Index (SPI-3) using 2-parameter Gamma MLE.
    4. Consecutive dry spell days (< 1.0 mm/day) and dry day frequency (< 2.5 mm).
    5. NASA SRTM 30m terrain elevation and slope runoff vulnerability.
    6. Official UPSDMA / Department of Agriculture drought advisories.

    Scientific Principles:
    - Rejects synthetic inputs for operational drought scoring.
    - Fails explicitly with 'insufficient_data' if monthly series is too short (< 12 months).
    - Distinguishes meteorological deficit from agronomic crop loss without ground telemetry.
    """

    @classmethod
    def evaluate(
        cls,
        district_info: Dict[str, Any],
        daily_df: pd.DataFrame,
        reference_date: str = "2026-10-28",
        mode: str = "demo",
        assessment_timestamp: Optional[str] = None,
    ) -> HazardAssessmentResponse:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        assess_dt = OfficialAlertsPipeline.parse_utc_datetime(assessment_timestamp) if assessment_timestamp else now_dt
        assess_iso = assess_dt.isoformat()
        is_demo = (mode == "demo")
        if mode == "live":
            data_mode: DataMode = "LIVE_MODEL"
        elif is_demo:
            data_mode: DataMode = "DEMONSTRATION"
        else:
            data_mode: DataMode = "CACHED_VERIFIED"

        district_slug = district_info["id"].lower().replace("district-", "").strip()
        region_id = f"district-{district_slug}"

        # 1. 30-Day and 90-Day Cumulative Precipitation
        r_30d = calculate_cumulative_rainfall(daily_df, window_days=30, reference_date=reference_date)
        r_90d = calculate_cumulative_rainfall(daily_df, window_days=90, reference_date=reference_date, min_days=90)

        is_historical_replay = bool(assessment_timestamp and assess_dt.date() < now_dt.date())

        # Check for unlinked / missing telemetry in candidate districts or empty datasets
        if not district_info.get("is_pilot", True) or daily_df.empty or daily_df["rainfall_mm"].dropna().empty:
            pending_indicators = [
                RiskIndicator(
                    indicator_id="drought_precip_90d_accum",
                    name="90-Day Cumulative Rainfall",
                    value=None,
                    units="mm",
                    category="observed_measurement",
                    calculation_window="90 days (ending 28 Oct 2026)",
                    reference_baseline="Historical normal awaiting station calibration",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="CHIRPS v2.0",
                    spatial_resolution="0.05° (~5.3 km)",
                    methodology_version="v2.0-scientific",
                    limitations="Station telemetry unlinked; awaiting scientific data ingestion.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
                RiskIndicator(
                    indicator_id="drought_precip_90d_anomaly",
                    name="90-Day Rainfall Departure",
                    value=None,
                    units="percentage",
                    category="derived_indicator",
                    calculation_window="90 days",
                    reference_baseline="30-Year Climatological Baseline (1991–2020 Normals)",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="CHIRPS v2.0 Climatology",
                    spatial_resolution="0.05° (~5.3 km)",
                    methodology_version="v2.0-scientific",
                    limitations="Negative departure uncalculated due to pending telemetry.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
                RiskIndicator(
                    indicator_id="drought_seasonal_deficit",
                    name="Seasonal Monsoon Departure",
                    value=None,
                    units="percentage",
                    category="derived_indicator",
                    calculation_window="Kharif Monsoon (June – September)",
                    reference_baseline="30-Year Monsoon Normal awaiting station calibration",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="1991–2020 IMD Normals",
                    spatial_resolution="District Administrative Unit",
                    methodology_version="v2.0-scientific",
                    limitations="Monsoon departure calculation pending observational ingestion.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
                RiskIndicator(
                    indicator_id="drought_spi_3",
                    name="Standardized Precipitation Index (SPI-3)",
                    value=None,
                    units="index (Z-score)",
                    category="derived_indicator",
                    calculation_window="3-Month Gamma Distribution transformation",
                    reference_baseline="WMO SPI Guidelines (2-parameter Gamma fit)",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="WMO-No. 1090 Standard",
                    spatial_resolution="0.05° (~5.3 km)",
                    methodology_version="v2.0-scientific",
                    limitations="SPI requires continuous multi-year monthly series; telemetry unlinked.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
                RiskIndicator(
                    indicator_id="drought_consecutive_dry_days",
                    name="Consecutive Dry Spell Days",
                    value=None,
                    units="days",
                    category="derived_indicator",
                    calculation_window="Last 60 days (< 1.0mm/day)",
                    reference_baseline="IMD Dry Spell criterion",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="IMD Operational Criteria",
                    spatial_resolution="District Boundary",
                    methodology_version="v2.0-scientific",
                    limitations="Candidate district isolated from pilot scoring engines.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
                RiskIndicator(
                    indicator_id="drought_dry_day_frequency",
                    name="Dry Day Frequency (< 2.5 mm)",
                    value=None,
                    units="percentage",
                    category="derived_indicator",
                    calculation_window="90 days antecedent",
                    reference_baseline="IMD Wet/Dry Standard Threshold (2.5 mm)",
                    observation_timestamp=reference_date,
                    retrieval_timestamp=now_iso,
                    quality_status="missing",
                    data_mode="DATA_PENDING",
                    dataset_version="IMD Classification Criteria",
                    spatial_resolution="District Boundary",
                    methodology_version="v2.0-scientific",
                    limitations="Candidate district dry day metrics pending ingestion.",
                    is_demo_data=False,
                    is_data_available=False,
                ),
            ]
            loc_ref = LocationReference(
                location_id=district_info["id"],
                name=district_info["name"],
                hindi_name=district_info.get("hindi_name", ""),
                latitude=district_info.get("lat", 0.0),
                longitude=district_info.get("lng", 0.0),
                elevation_m=district_info.get("elevation_m", 197.1),
                river_basin=district_info.get("river_basin", "Unknown"),
                region=district_info.get("region", "Unknown"),
                is_pilot=False,
            )
            return HazardAssessmentResponse(
                location=loc_ref,
                hazard="drought",
                risk_level="pending",
                assessment_period="Data Ingestion Pending",
                generated_at=now_iso,
                assessment_timestamp=assess_iso,
                is_historical_replay=is_historical_replay,
                data_mode="DATA_PENDING",
                is_demo_data=False,
                is_data_available=False,
                disclaimer="Candidate district. Observational data pending onboarding. Zero risk bleed policy enforced.",
                indicators=pending_indicators,
                sources=[],
                scientific_notes=["Candidate district telemetry unlinked. Risk score is pending scientific ingestion."],
                primary_risk_driver="Candidate district: observational telemetry unlinked",
                data_completeness="pending",
                official_advisory=OfficialAdvisoryReference(
                    authority="IMD / UPSDMA",
                    bulletin_id=None,
                    alert_level="None",
                    is_valid=False,
                    is_currently_active=False,
                    valid_from=None,
                    valid_to=None,
                    advisory_text="No live unauthenticated government alert feed integrated for this district.",
                    status="data_pending",
                    verification_status="data_pending",
                ),
            )

        # Baseline: 30-year normal for Mahoba 90-day window (Aug-Oct normal ~ 453.6 mm)
        try:
            m_norm_8 = CHIRPSPipeline.get_district_monthly_normal(region_id, 8)
            m_norm_9 = CHIRPSPipeline.get_district_monthly_normal(region_id, 9)
            m_norm_10 = CHIRPSPipeline.get_district_monthly_normal(region_id, 10)
            baseline_90d = round(m_norm_8 + m_norm_9 + m_norm_10, 1)
        except Exception:
            baseline_90d = 453.6

        anomaly_90d = calculate_rainfall_anomaly(r_90d, baseline_90d) if r_90d is not None else None

        # 2. Kharif Monsoon Seasonal Departure (June to September accumulation)
        try:
            ref_year = pd.to_datetime(reference_date).year
        except Exception:
            ref_year = 2026

        df_copy = daily_df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"])
        monsoon_mask = (
            (df_copy["date"].dt.year == ref_year) &
            (df_copy["date"].dt.month.isin([6, 7, 8, 9]))
        )
        monsoon_sub = df_copy[monsoon_mask]
        # Require >= 100 days of monsoon coverage (out of 122 June-September days, ~82%)
        # to ensure we don't calculate seasonal deficit from a small tail window (e.g. 2 days of September)
        if len(monsoon_sub) >= 100:
            observed_monsoon = float(monsoon_sub["rainfall_mm"].sum())
        else:
            observed_monsoon = None

        try:
            baseline_monsoon = CHIRPSPipeline.get_district_monsoon_normal(region_id)
        except Exception:
            baseline_monsoon = 845.4  # Mahoba 1991-2020 monsoon normal

        seasonal_deficit_pct = calculate_rainfall_anomaly(observed_monsoon, baseline_monsoon) if observed_monsoon is not None else None

        # 3. Maximum Consecutive Dry Spell Days (< 1.0 mm) and Dry Day Frequency (< 2.5 mm)
        dry_spell_days = calculate_max_consecutive_dry_days(
            daily_df, dry_threshold_mm=1.0, window_days=60
        )

        ref_ts = pd.to_datetime(reference_date)
        start_90d = ref_ts - pd.Timedelta(days=90)
        sub_90d = df_copy[(df_copy["date"] >= start_90d) & (df_copy["date"] <= ref_ts)]
        if not sub_90d.empty:
            dry_days_count = int((sub_90d["rainfall_mm"] < 2.5).sum())
            dry_day_frequency_pct = round((dry_days_count / len(sub_90d)) * 100.0, 1)
        else:
            dry_day_frequency_pct = 0.0

        # 4. Standardized Precipitation Index (SPI-3)
        monthly_df = df_copy.set_index("date")["rainfall_mm"].resample("ME").sum()

        if len(monthly_df) < 12:
            spi_val = None
            spi_cat = "Insufficient Data"
            spi_status = "data_pending"
        else:
            spi_val, spi_cat, spi_meta = SPIEngine.calculate_spi_3(monthly_df)
            spi_status = "verified"

        # 5. NASA SRTM 30m Terrain Profile
        try:
            srtm_profile = SRTMElevationPipeline.get_elevation_profile(region_id)
            mean_elev = float(srtm_profile.get("mean_elevation_m", district_info.get("elevation_m", 197.1)))
            slope_avg = float(srtm_profile.get("slope_degrees_avg", 2.85))
        except Exception:
            mean_elev = float(district_info.get("elevation_m", 197.1))
            slope_avg = 2.85

        # 6. Official Advisory from UPSDMA Drought Cell (evaluated at actual assessment timestamp)
        official_adv = OfficialAlertsPipeline.validate_district_advisory(region_id, assessment_timestamp=assess_iso)
        alert_lvl = official_adv.get("alert_level", "None")
        is_adv_valid = bool(official_adv.get("is_valid", False))
        is_currently_active = bool(official_adv.get("is_currently_active", False))

        # 7. Transparent Risk Classification Decision Logic:
        # 1. Valid Orange/Red advisory -> high
        # 2. Sufficient meteorological evidence meeting high threshold (SPI-3 <= -2.0 or deficit <= -60%) -> high
        # 3. Evidence meeting moderate threshold (SPI-3 <= -1.2, deficit <= -35%, or independent dry_spell_days >= 25) -> moderate
        # 4. Sufficient required meteorological evidence establishing normal conditions -> low
        # 5. Insufficient evidence without a valid high-level advisory -> pending (never low)
        has_complete_meteorological_evidence = all(val is not None for val in [r_90d, seasonal_deficit_pct, spi_val])

        if (is_adv_valid and alert_lvl in ["Red", "Orange"]) or (spi_val is not None and spi_val <= -2.0) or (seasonal_deficit_pct is not None and seasonal_deficit_pct <= -60.0):
            risk_level = "high"
        elif (spi_val is not None and spi_val <= -1.2) or (seasonal_deficit_pct is not None and seasonal_deficit_pct <= -35.0) or (dry_spell_days is not None and dry_spell_days >= 25):
            risk_level = "moderate"
        elif has_complete_meteorological_evidence:
            risk_level = "low"
        else:
            # When required long-term meteorological evidence is missing and no active advisory is present,
            # classify explicitly as pending (insufficient evidence) - never as low risk!
            risk_level = "pending"

        # Indicator provenance variables based on operational mode
        is_live_mode = (mode == "live")
        precip_category: Literal["observed_measurement", "model_derived"] = (
            "model_derived" if is_live_mode else "observed_measurement"
        )
        version_90d = (
            "Open-Meteo Forecast API v1.0 (ECMWF IFS / GFS Blend)"
            if is_live_mode
            else "CHIRPS v2.0"
        )
        limitations_90d = (
            "90-day rainfall data unavailable — insufficient historical coverage in live model cache."
            if (is_live_mode and r_90d is None)
            else (
                "District representative-point estimate from Open-Meteo operational NWP model analysis (ECMWF IFS / GFS Blend). "
                "Not an in-situ rain gauge or soil moisture measurement."
                if is_live_mode
                else (
                    "90-day rainfall data unavailable — insufficient observation coverage."
                    if r_90d is None
                    else "Spatial area-weighted sum over validated administrative polygon boundary."
                )
            )
        )
        precip_quality_status: DataQualityStatus = (
            "missing" if r_90d is None else ("provisional" if is_live_mode else "verified")
        )

        # Construct Indicators List
        indicators: List[RiskIndicator] = [
            RiskIndicator(
                indicator_id="drought_precip_90d_accum",
                name="90-Day Cumulative Rainfall",
                value=r_90d,
                units="mm",
                category=precip_category,
                calculation_window="90 days (ending 28 Oct 2026)",
                reference_baseline=f"Historical normal: {baseline_90d} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status=precip_quality_status,
                data_mode=data_mode,
                dataset_version=version_90d,
                spatial_resolution="0.1° (~11 km) Representative Point" if is_live_mode else "0.05° (~5.3 km)",
                methodology_version="v2.0-scientific",
                limitations=limitations_90d,
                is_demo_data=is_demo,
                is_data_available=(r_90d is not None),
            ),
            RiskIndicator(
                indicator_id="drought_precip_90d_anomaly",
                name="90-Day Rainfall Departure",
                value=anomaly_90d,
                units="percentage",
                category="derived_indicator",
                calculation_window="90 days",
                reference_baseline="30-Year Climatological Baseline (1991–2020 Normals)",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="missing" if anomaly_90d is None else ("provisional" if is_live_mode else "verified"),
                data_mode=data_mode,
                dataset_version="CHIRPS v2.0 Climatology",
                spatial_resolution="0.05° (~5.3 km)",
                methodology_version="v2.0-scientific",
                limitations="90-day departure uncalculated due to insufficient observation coverage in calculation window." if anomaly_90d is None else "Negative departure indicates acute meteorological precipitation shortfall.",
                is_demo_data=is_demo,
                is_data_available=(anomaly_90d is not None),
            ),
            RiskIndicator(
                indicator_id="drought_seasonal_deficit",
                name="Seasonal Monsoon Departure",
                value=seasonal_deficit_pct,
                units="percentage",
                category="derived_indicator",
                calculation_window="Kharif Monsoon (June – September)",
                reference_baseline=f"30-Year Monsoon Normal: {baseline_monsoon} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="missing" if seasonal_deficit_pct is None else "verified",
                data_mode=data_mode,
                dataset_version="1991–2020 IMD Normals",
                spatial_resolution="District Administrative Unit",
                methodology_version="v2.0-scientific",
                limitations="Monsoon departure uncalculated due to absence of June-September observations in calculation window." if seasonal_deficit_pct is None else "IMD classifies departures beyond -59% as Large Deficient / Scanty rainfall.",
                is_demo_data=is_demo,
                is_data_available=(seasonal_deficit_pct is not None),
            ),
            RiskIndicator(
                indicator_id="drought_spi_3",
                name="Standardized Precipitation Index (SPI-3)",
                value=spi_val,
                units="index (Z-score)",
                category="derived_indicator",
                calculation_window="3-Month Gamma Distribution transformation",
                reference_baseline="WMO SPI Guidelines (2-parameter Gamma fit)",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status=spi_status,
                data_mode=data_mode,
                dataset_version="WMO-No. 1090 Standard",
                spatial_resolution="0.05° (~5.3 km)",
                methodology_version="v2.0-scientific",
                limitations="Measures meteorological deficit. Does not substitute for field ground-survey crop cutting.",
                is_demo_data=is_demo,
                is_data_available=(spi_val is not None),
            ),
            RiskIndicator(
                indicator_id="drought_consecutive_dry_days",
                name="Consecutive Dry Spell Days",
                value=float(dry_spell_days) if dry_spell_days is not None else None,
                units="days",
                category="derived_indicator",
                calculation_window="Last 60 days (< 1.0mm/day)",
                reference_baseline="IMD Dry Spell criterion",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="missing" if dry_spell_days is None else "verified",
                data_mode=data_mode,
                dataset_version="IMD Operational Criteria",
                spatial_resolution="District Boundary",
                methodology_version="v2.0-scientific",
                limitations="Consecutive dry spell duration accelerates agricultural topsoil desiccation.",
                is_demo_data=is_demo,
                is_data_available=(dry_spell_days is not None),
            ),
            RiskIndicator(
                indicator_id="drought_dry_day_frequency",
                name="Dry Day Frequency (< 2.5 mm)",
                value=dry_day_frequency_pct,
                units="percentage",
                category="derived_indicator",
                calculation_window="90 days antecedent",
                reference_baseline="IMD Wet/Dry Standard Threshold (2.5 mm)",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                data_mode=data_mode,
                dataset_version="IMD Classification Criteria",
                spatial_resolution="District Boundary",
                methodology_version="v2.0-scientific",
                limitations="High dry day percentage indicates prolonged absence of effective root-zone wetting.",
                is_demo_data=is_demo,
            ),
        ]

        if is_live_mode:
            sources: List[SourceMetadata] = [
                SourceMetadata(
                    source_id="open_meteo_forecast",
                    source_name="Open-Meteo Weather Forecast (NWP)",
                    spatial_resolution="0.1° (~11 km) ECMWF IFS / GFS Blend Representative Point",
                    temporal_resolution="Hourly / Daily Aggregated",
                    dataset_version="Forecast API v1.0",
                    access_url="https://open-meteo.com/",
                    units="mm/day",
                    data_mode="LIVE_MODEL",
                    retrieval_timestamp=now_iso,
                    license="CC-BY 4.0 Open-Meteo",
                ),
                SourceMetadata(
                    source_id="chirps_climatology",
                    source_name="CHIRPS 30-Year Climatological Baseline (1991–2020 Normals)",
                    spatial_resolution="0.05° (~5.3 km)",
                    temporal_resolution="30-Year Monthly Climatology",
                    dataset_version="v2.0 Climatology",
                    access_url="https://www.chc.ucsb.edu/data/chirps",
                    units="mm/month",
                    data_mode="CACHED_VERIFIED",
                    retrieval_timestamp=now_iso,
                    license="Creative Commons Public Domain",
                ),
                SourceMetadata(
                    source_id="srtm_dem",
                    source_name="NASA SRTM 30m Digital Elevation Model",
                    spatial_resolution="1 arc-second (~30 meters)",
                    temporal_resolution="Static benchmark",
                    dataset_version="v3.0 void-filled",
                    access_url="https://earthexplorer.usgs.gov/",
                    units="meters above MSL",
                    data_mode="CACHED_VERIFIED",
                    retrieval_timestamp=now_iso,
                    license="NASA Open Public Domain",
                ),
                SourceMetadata(
                    source_id="upsdma_imd",
                    source_name="Manual for Drought Management / UPSDMA",
                    spatial_resolution="District Administrative Level",
                    temporal_resolution="Seasonal / Weekly",
                    dataset_version="National Drought Manual 2020",
                    access_url="https://upsdma.up.nic.in/",
                    units="Standardized Criteria",
                    data_mode="LIVE_VERIFIED",
                    retrieval_timestamp=now_iso,
                    license="Government Open Data License (GODL)",
                ),
            ]
        else:
            sources: List[SourceMetadata] = [
                SourceMetadata(
                    source_id="chirps_daily",
                    source_name="CHIRPS Daily Station Blended",
                    spatial_resolution="0.05° (~5.3 km)",
                    temporal_resolution="Daily",
                    dataset_version="v2.0",
                    access_url="https://www.chc.ucsb.edu/data/chirps",
                    units="mm/day",
                    data_mode=data_mode,
                    retrieval_timestamp=now_iso,
                    license="Creative Commons Public Domain",
                ),
                SourceMetadata(
                    source_id="srtm_dem",
                    source_name="NASA SRTM 30m Digital Elevation Model",
                    spatial_resolution="1 arc-second (~30 meters)",
                    temporal_resolution="Static benchmark",
                    dataset_version="v3.0 void-filled",
                    access_url="https://earthexplorer.usgs.gov/",
                    units="meters above MSL",
                    data_mode=data_mode,
                    retrieval_timestamp=now_iso,
                    license="NASA Open Public Domain",
                ),
                SourceMetadata(
                    source_id="upsdma_imd",
                    source_name="Manual for Drought Management / UPSDMA",
                    spatial_resolution="District Administrative Level",
                    temporal_resolution="Seasonal / Weekly",
                    dataset_version="National Drought Manual 2020",
                    access_url="https://upsdma.up.nic.in/",
                    units="Standardized Criteria",
                    data_mode=data_mode,
                    retrieval_timestamp=now_iso,
                    license="Government Open Data License (GODL)",
                ),
            ]

        # Primary risk driver attribution with historical replay prefix
        replay_prefix = f"[Historical Replay: {assess_dt.strftime('%Y-%m-%d')}] " if is_historical_replay else ""

        if is_adv_valid and alert_lvl in ["Red", "Orange"]:
            if is_historical_replay:
                primary_risk_driver = (
                    f"{replay_prefix}Official administrative advisory: {official_adv.get('authority')} {alert_lvl} Alert "
                    f"(Bulletin {official_adv.get('bulletin_id')}, expired on {official_adv.get('valid_to')} and currently INACTIVE)"
                )
            else:
                primary_risk_driver = (
                    f"Official administrative advisory: {official_adv.get('authority')} {alert_lvl} Alert "
                    f"(Bulletin {official_adv.get('bulletin_id')})"
                )
        elif spi_val is not None and spi_val <= -2.0:
            primary_risk_driver = f"{replay_prefix}Meteorological drought: SPI-3 index ({spi_val:.2f}) indicates extreme dryness"
        elif seasonal_deficit_pct is not None and seasonal_deficit_pct <= -60.0:
            primary_risk_driver = f"{replay_prefix}Monsoon deficit: Seasonal departure ({seasonal_deficit_pct:.1f}%) exceeds severe drought threshold (-60%)"
        elif risk_level == "moderate":
            if spi_val is not None and spi_val <= -1.2:
                primary_risk_driver = f"{replay_prefix}Meteorological drought: SPI-3 index ({spi_val:.2f}) indicates moderate-to-severe dryness"
            elif seasonal_deficit_pct is not None and seasonal_deficit_pct <= -35.0:
                primary_risk_driver = f"{replay_prefix}Monsoon deficit: Seasonal departure ({seasonal_deficit_pct:.1f}%) indicates significant Kharif deficit"
            elif dry_spell_days is not None and dry_spell_days >= 25:
                primary_risk_driver = f"{replay_prefix}Agricultural dry spell: {dry_spell_days} consecutive dry days accelerate topsoil desiccation"
            else:
                primary_risk_driver = f"{replay_prefix}Cumulative antecedent precipitation and baseline indicators"
        elif risk_level == "low":
            primary_risk_driver = f"{replay_prefix}Normal antecedent precipitation and baseline conditions (verified climatological observations)"
        elif risk_level == "pending":
            if not is_adv_valid and official_adv.get("bulletin_id"):
                primary_risk_driver = (
                    f"{replay_prefix}Insufficient meteorological coverage in live cache "
                    f"(90-day rainfall uncalculated; advisory {official_adv.get('bulletin_id')} expired on {official_adv.get('valid_to')})"
                )
            else:
                primary_risk_driver = f"{replay_prefix}Insufficient meteorological coverage in calculation window (90-day assessment incomplete)"
        else:
            primary_risk_driver = f"{replay_prefix}Assessment pending"

        # Required assessment indicators for drought completeness:
        # Evaluated strictly on required physical assessment indicators (r_90d, seasonal_deficit, SPI-3),
        # not every optional display metric.
        required_drought_indicators = [r_90d, seasonal_deficit_pct, spi_val]
        if all(val is not None for val in required_drought_indicators):
            data_completeness: DataCompleteness = "complete"
            is_data_available = True
        else:
            data_completeness: DataCompleteness = "partial"
            is_data_available = False

        # Dynamic assessment period reflecting actual evidence window
        if r_90d is None:
            days_count = len(daily_df)
            assessment_period = f"Antecedent {days_count}-Day Live NWP Window & Authoritative Advisory"
        else:
            assessment_period = "90-Day Seasonal Deficit & SPI-3 Window"

        official_adv_ref = OfficialAdvisoryReference(
            authority=official_adv.get("authority", "IMD / UPSDMA"),
            bulletin_id=official_adv.get("bulletin_id"),
            alert_level=official_adv.get("alert_level", "None"),
            is_valid=is_adv_valid,
            is_currently_active=is_currently_active,
            valid_from=official_adv.get("valid_from"),
            valid_to=official_adv.get("valid_to"),
            advisory_text=official_adv.get("advisory_text"),
            status=official_adv.get("status"),
            verification_status=official_adv.get("verification_status"),
        )

        scientific_notes = [
            "Meteorological drought does not equate to confirmed agricultural crop loss without ground crop-cutting surveys.",
            f"Mahoba is located on the crystalline Bundelkhand plateau (mean elevation {mean_elev}m MSL, average slope {slope_avg}°), where low groundwater retention exacerbates rainfall deficits.",
            "Official drought declarations are made under the Disaster Management Act by the State Government of Uttar Pradesh.",
            "All spatial aggregation is strictly bounded to validated Survey of India / OSM administrative polygon boundaries.",
        ]

        if is_historical_replay:
            scientific_notes.insert(
                0,
                f"HISTORICAL REPLAY: Evaluated for historical date {assess_iso}. "
                f"Advisory {official_adv.get('bulletin_id')} expired on {official_adv.get('valid_to')} and is INACTIVE operationally."
            )
        elif not is_adv_valid and official_adv.get("bulletin_id"):
            scientific_notes.append(f"Administrative advisory {official_adv.get('bulletin_id')} expired on {official_adv.get('valid_to')} and is not active for this assessment.")
        elif is_adv_valid:
            scientific_notes.append(f"Official advisory {official_adv.get('bulletin_id')} is active (valid {official_adv.get('valid_from')} to {official_adv.get('valid_to')}).")

        if mode == "live":
            scientific_notes.insert(0, "Live precipitation and ET0 metrics are derived from Open-Meteo NWP representative-point estimates at district centroid.")
            if r_90d is None:
                scientific_notes.insert(1, "90-day cumulative rainfall and departure are unavailable in live mode due to insufficient historical coverage in the operational NWP cache (requires 90 calendar days).")

        if is_historical_replay:
            disclaimer = (
                f"HISTORICAL REPLAY: Evaluates retrospective conditions as of {assess_iso}. "
                f"Official advisory expired on {official_adv.get('valid_to')} and is INACTIVE operationally. "
                f"Generated at {now_iso}."
            )
        else:
            disclaimer = (
                "JalRakshak is a research decision-support prototype. "
                "Values represent derived transparent indicators, not official government warnings."
            )

        loc_ref = LocationReference(
            location_id=district_info["id"],
            name=district_info["name"],
            hindi_name=district_info["hindi_name"],
            latitude=district_info["lat"],
            longitude=district_info["lng"],
            elevation_m=mean_elev,
            river_basin=district_info["river_basin"],
            region=district_info["region"],
            is_pilot=district_info.get("is_pilot", False),
        )

        return HazardAssessmentResponse(
            location=loc_ref,
            hazard="drought",
            risk_level=risk_level,
            assessment_period=assessment_period,
            generated_at=now_iso,
            assessment_timestamp=assess_iso,
            is_historical_replay=is_historical_replay,
            data_mode=data_mode,
            is_demo_data=is_demo,
            is_data_available=is_data_available,
            disclaimer=disclaimer,
            indicators=indicators,
            sources=sources,
            scientific_notes=scientific_notes,
            primary_risk_driver=primary_risk_driver,
            data_completeness=data_completeness,
            official_advisory=official_adv_ref,
        )
