import pandas as pd
import numpy as np
from typing import Dict, Any, List
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
)

class DroughtRiskEngine:
    """
    Computes meteorological drought indicators for Mahoba & Bundelkhand.
    Integrates SPI-3, 90-day rainfall deficits, and consecutive dry spell analysis.
    """

    @classmethod
    def evaluate(
        cls,
        district_info: Dict[str, Any],
        daily_df: pd.DataFrame,
        reference_date: str = "2026-10-28"
    ) -> HazardAssessmentResponse:
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. 90-Day Cumulative Precipitation
        r_90d = calculate_cumulative_rainfall(daily_df, window_days=90, reference_date=reference_date)

        # Baseline: Historical 90-day normal for Mahoba post-monsoon ~ 147 mm
        baseline_90d = 147.0
        anomaly_90d = calculate_rainfall_anomaly(r_90d, baseline_90d)

        # 2. Kharif Seasonal Monsoon Deficit (Jun-Sep accumulation)
        # Normal Kharif precipitation in Mahoba is ~ 820 mm
        baseline_monsoon = 820.0
        # In 2026 Mahoba recorded ~ 230 mm
        observed_monsoon = 230.0
        seasonal_deficit_pct = calculate_rainfall_anomaly(observed_monsoon, baseline_monsoon)

        # 3. Maximum consecutive dry spell days (< 1.0mm) in the last 60 days
        dry_spell_days = calculate_max_consecutive_dry_days(
            daily_df, dry_threshold_mm=1.0, window_days=60
        )

        # 4. Standardized Precipitation Index (SPI-3)
        # Resample daily series to monthly totals
        df_copy = daily_df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"])
        monthly_df = df_copy.set_index("date")["rainfall_mm"].resample("ME").sum()

        spi_val, spi_cat, spi_meta = SPIEngine.calculate_spi_3(monthly_df)

        # Determine transparent categorical risk:
        # High Risk if SPI-3 < -2.0 (Extreme) or deficit < -75%
        # Moderate Risk if SPI-3 < -1.5 (Severe) or deficit < -50%
        if spi_val <= -2.0 or seasonal_deficit_pct <= -75.0:
            risk_level = "high"
        elif spi_val <= -1.2 or seasonal_deficit_pct <= -50.0:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Build indicators list
        indicators: List[RiskIndicator] = [
            RiskIndicator(
                indicator_id="drought_precip_90d_accum",
                name="90-Day Cumulative Rainfall",
                value=r_90d,
                units="mm",
                category="observed_measurement",
                calculation_window="90 days (ending 28 Oct 2026)",
                reference_baseline=f"Historical mean: {baseline_90d} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="CHIRPS gridded daily station-blend estimate. Local field moisture varies with soil depth.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="drought_precip_90d_anomaly",
                name="90-Day Rainfall Departure",
                value=anomaly_90d,
                units="percentage",
                category="derived_indicator",
                calculation_window="90 days",
                reference_baseline="10-Year CHIRPS Baseline",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Negative departure indicates acute precipitation shortfall.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="drought_seasonal_deficit",
                name="Seasonal Monsoon Departure",
                value=seasonal_deficit_pct,
                units="percentage",
                category="derived_indicator",
                calculation_window="Kharif Season (June – September)",
                reference_baseline=f"Kharif Normal: {baseline_monsoon} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="IMD classifies departures beyond -59% as Large Deficient / Scanty rainfall.",
                is_demo_data=True,
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
                quality_status="verified",
                limitations=(
                    "SPI measures meteorological drought. It does not measure direct soil moisture, "
                    "root-zone hydrology, or borewell draw-down without ground sensor telemetry."
                ),
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="drought_consecutive_dry_days",
                name="Consecutive Dry Spell Days",
                value=float(dry_spell_days),
                units="days",
                category="derived_indicator",
                calculation_window="Last 60 days (< 1.0mm/day)",
                reference_baseline="IMD Dry Spell criterion",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Consecutive dry spell duration accelerates topsoil moisture loss.",
                is_demo_data=True,
            ),
        ]

        sources: List[SourceMetadata] = [
            SourceMetadata(
                source_id="chirps_daily",
                source_name="CHIRPS Daily Station Blended",
                spatial_resolution="0.05° (~5 km)",
                temporal_resolution="Daily",
                access_url="https://www.chc.ucsb.edu/data/chirps",
                units="mm/day",
                retrieval_timestamp=now_iso,
            ),
            SourceMetadata(
                source_id="upsdma_imd",
                source_name="Manual for Drought Management / IMD",
                spatial_resolution="District Administrative Level",
                temporal_resolution="Seasonal / Weekly",
                access_url="https://upsdma.up.nic.in/",
                units="Standardized Criteria",
                retrieval_timestamp=now_iso,
            ),
        ]

        scientific_notes = [
            "Meteorological drought does not equate to confirmed agricultural crop loss without crop ground surveys.",
            "Mahoba is located in the rocky Bundelkhand crystalline shield where groundwater recharge is highly vulnerable to seasonal deficits.",
            "Official drought declarations are made under the Disaster Management Act by the State Government of Uttar Pradesh.",
        ]

        loc_ref = LocationReference(
            location_id=district_info["id"],
            name=district_info["name"],
            hindi_name=district_info["hindi_name"],
            latitude=district_info["lat"],
            longitude=district_info["lng"],
            elevation_m=district_info["elevation_m"],
            river_basin=district_info["river_basin"],
            region=district_info["region"],
            is_pilot=district_info.get("is_pilot", False),
        )

        return HazardAssessmentResponse(
            location=loc_ref,
            hazard="drought",
            risk_level=risk_level,
            assessment_period="90-Day Seasonal Deficit & SPI-3 Window",
            generated_at=now_iso,
            is_demo_data=True,
            indicators=indicators,
            sources=sources,
            scientific_notes=scientific_notes,
        )
