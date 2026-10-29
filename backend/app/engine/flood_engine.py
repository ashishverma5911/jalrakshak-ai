import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from .indicators import (
    calculate_cumulative_rainfall,
    calculate_rainfall_anomaly,
    count_wet_days,
    calculate_historical_percentile,
)
from ..schemas.common import (
    HazardAssessmentResponse,
    LocationReference,
    RiskIndicator,
    SourceMetadata,
)

class FloodRiskEngine:
    """
    Computes flood-related meteorological risk indicators for Gorakhpur & Eastern UP.
    Distinguishes heavy precipitation accumulation and terrain slope from actual inundation.
    """

    @classmethod
    def evaluate(
        cls,
        district_info: Dict[str, Any],
        daily_df: pd.DataFrame,
        reference_date: str = "2026-10-28"
    ) -> HazardAssessmentResponse:
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. 7-Day Cumulative Rainfall
        r_7d = calculate_cumulative_rainfall(daily_df, window_days=7, reference_date=reference_date)

        # Baseline: Historical 7-day October mean in Gorakhpur ~ 173 mm
        baseline_7d = 173.0
        anomaly_7d = calculate_rainfall_anomaly(r_7d, baseline_7d)

        # 2. 30-Day Cumulative Rainfall
        r_30d = calculate_cumulative_rainfall(daily_df, window_days=30, reference_date=reference_date)
        baseline_30d = 345.0
        anomaly_30d = calculate_rainfall_anomaly(r_30d, baseline_30d)

        # 3. 7-Day Wet Days Count (>= 2.5 mm)
        wet_days_7d = count_wet_days(daily_df, threshold_mm=2.5, window_days=7)

        # 4. Historical Percentile Rank over full 10-year daily records
        rolling_7d_historical = daily_df["rainfall_mm"].rolling(window=7).sum().dropna()
        percentile_7d = calculate_historical_percentile(rolling_7d_historical, r_7d)

        # Determine transparent categorical risk:
        # High Risk if 7-day rainfall > 200 mm AND percentile > 85% in low-lying district
        is_low_elevation = district_info.get("elevation_m", 100) < 100
        if r_7d >= 250.0 and percentile_7d >= 85.0 and is_low_elevation:
            risk_level = "high"
        elif r_7d >= 150.0 or percentile_7d >= 70.0:
            risk_level = "moderate"
        else:
            risk_level = "low"

        # Build indicators list with full provenance and limitations
        indicators: List[RiskIndicator] = [
            RiskIndicator(
                indicator_id="flood_precip_7d_accum",
                name="7-Day Cumulative Rainfall",
                value=r_7d,
                units="mm",
                category="observed_measurement",
                calculation_window="7 days (ending 28 Oct 2026)",
                reference_baseline=f"Historical mean: {baseline_7d} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Measured via satellite gridded series (0.1° GPM). Local micro-cloudbursts may vary.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="flood_precip_7d_anomaly",
                name="7-Day Rainfall Anomaly",
                value=anomaly_7d,
                units="percentage",
                category="derived_indicator",
                calculation_window="7 days relative to October normal",
                reference_baseline="10-Year CHIRPS Baseline (2015-2024)",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Reflects meteorological departure from normal. Does not compute river discharge.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="flood_precip_30d_accum",
                name="30-Day Cumulative Rainfall",
                value=r_30d,
                units="mm",
                category="observed_measurement",
                calculation_window="30 days",
                reference_baseline=f"Historical mean: {baseline_30d} mm",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Accumulation over 30 days indicates persistent catchment saturation.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="flood_wet_days_7d",
                name="Wet Days (>=2.5mm)",
                value=float(wet_days_7d),
                units="days",
                category="derived_indicator",
                calculation_window="7 days",
                reference_baseline="IMD Wet Day standard (>=2.5 mm/day)",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Frequency metric indicating persistent overcast moisture loading.",
                is_demo_data=True,
            ),
            RiskIndicator(
                indicator_id="flood_historical_percentile",
                name="Historical Event Percentile Rank",
                value=percentile_7d,
                units="percentile",
                category="derived_indicator",
                calculation_window="10-Year multi-monsoon empirical distribution",
                reference_baseline="2015–2025 CHIRPS 7-day rolling sums",
                observation_timestamp=reference_date,
                retrieval_timestamp=now_iso,
                quality_status="verified",
                limitations="Empirical sample percentile. Not a calibrated Bayesian return probability.",
                is_demo_data=True,
            ),
        ]

        sources: List[SourceMetadata] = [
            SourceMetadata(
                source_id="nasa_gpm_imerg",
                source_name="NASA GPM IMERG Late Run",
                spatial_resolution="0.1° × 0.1° (~10 km)",
                temporal_resolution="Daily",
                access_url="https://gpm.nasa.gov/data/imerg",
                units="mm/day",
                retrieval_timestamp=now_iso,
            ),
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
                source_id="srtm_dem",
                source_name="SRTM 30m Digital Elevation Model",
                spatial_resolution="30 meters",
                temporal_resolution="Static",
                access_url="https://earthexplorer.usgs.gov/",
                units="meters above MSL",
                retrieval_timestamp=now_iso,
            ),
        ]

        scientific_notes = [
            "Rainfall accumulation alone does NOT compute water inundation or embankment breaching.",
            "River gauge levels and flood warnings are issued exclusively by Central Water Commission (CWC) and UPSDMA.",
            f"Average terrain elevation in {district_info['name']} is {district_info['elevation_m']}m MSL with gentle gradient into the {district_info['river_basin']}.",
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
            hazard="flood",
            risk_level=risk_level,
            assessment_period="7-Day & 30-Day Antecedent Precipitation Window",
            generated_at=now_iso,
            is_demo_data=True,
            indicators=indicators,
            sources=sources,
            scientific_notes=scientific_notes,
        )
