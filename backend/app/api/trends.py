from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import pandas as pd
from datetime import datetime

from ..pipeline.ingestion import DataIngestionService
from ..schemas.trends import RainfallTrendsResponse, RainfallSeriesPoint
from ..engine.indicators import count_wet_days

router = APIRouter(prefix="/trends", tags=["Rainfall Trends"])
ingestion_service = DataIngestionService()

@router.get("/rainfall", response_model=RainfallTrendsResponse)
def get_rainfall_trends(
    location: str = Query("gorakhpur", description="District identifier (gorakhpur or mahoba)"),
    range: str = Query("30", description="Time window days: 7, 30, 90, or 365"),
    aggregation: str = Query("daily", description="Time aggregation: daily, weekly, monthly"),
    mode: str = Query("demo", description="Data mode: 'demo' or 'verified'")
) -> RainfallTrendsResponse:
    try:
        district_info = ingestion_service.get_district_info(location)
        df = ingestion_service.load_daily_rainfall(location, mode=mode)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    df["date"] = pd.to_datetime(df["date"])

    # Determine slice by range
    days_map = {"7": 7, "30": 30, "90": 90, "365": 365}
    n_days = days_map.get(range, 30)

    # Slice recent N days
    sub_df = df.sort_values(by="date").tail(n_days).copy()

    # Pre-calculated monthly historical baselines (mm)
    baseline_lookup = {
        "gorakhpur": {1: 18, 2: 14, 3: 12, 4: 9, 5: 28, 6: 145, 7: 290, 8: 250, 9: 180, 10: 40, 11: 6, 12: 5},
        "mahoba": {1: 12, 2: 10, 3: 8, 4: 5, 5: 14, 6: 85, 7: 260, 8: 240, 9: 140, 10: 32, 11: 10, 12: 6},
    }
    district_baselines = baseline_lookup.get(location.lower(), baseline_lookup["gorakhpur"])

    series_points: List[RainfallSeriesPoint] = []

    if aggregation == "monthly" or range == "365":
        # Group by month
        sub_df["month_label"] = sub_df["date"].dt.strftime("%b")
        sub_df["month_num"] = sub_df["date"].dt.month
        monthly_grp = sub_df.groupby("month_num")["rainfall_mm"].sum().reset_index()

        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }

        for m_num in sorted(monthly_grp["month_num"].unique()):
            raw_obs = monthly_grp[monthly_grp["month_num"] == m_num]["rainfall_mm"].values[0]
            hist = float(district_baselines.get(m_num, 20.0))
            if pd.isna(raw_obs):
                series_points.append(
                    RainfallSeriesPoint(
                        date=month_names.get(m_num, str(m_num)),
                        observed_rainfall_mm=None,
                        historical_avg_mm=hist,
                        anomaly_percentage=None,
                        is_zero_measured=False,
                        is_missing=True,
                        data_quality="missing",
                    )
                )
            else:
                obs = float(raw_obs)
                diff = round(((obs - hist) / hist) * 100.0, 1) if hist > 0 else 0.0
                is_zero = obs == 0.0
                series_points.append(
                    RainfallSeriesPoint(
                        date=month_names.get(m_num, str(m_num)),
                        observed_rainfall_mm=round(obs, 1),
                        historical_avg_mm=hist,
                        anomaly_percentage=diff,
                        is_zero_measured=is_zero,
                        is_missing=False,
                        data_quality="zero_precipitation" if is_zero else "observed",
                    )
                )
    elif aggregation == "weekly":
        # Resample by 7 days
        weekly = sub_df.set_index("date")["rainfall_mm"].resample("W").sum().reset_index()
        for idx, row in weekly.iterrows():
            raw_obs = row["rainfall_mm"]
            month_num = row["date"].month
            daily_mean = district_baselines.get(month_num, 30.0) / 30.0
            hist = round(daily_mean * 7.0, 1)
            if pd.isna(raw_obs):
                series_points.append(
                    RainfallSeriesPoint(
                        date=row["date"].strftime("%b %d"),
                        observed_rainfall_mm=None,
                        historical_avg_mm=hist,
                        is_zero_measured=False,
                        is_missing=True,
                        data_quality="missing",
                    )
                )
            else:
                obs = float(raw_obs)
                is_zero = obs == 0.0
                series_points.append(
                    RainfallSeriesPoint(
                        date=row["date"].strftime("%b %d"),
                        observed_rainfall_mm=round(obs, 1),
                        historical_avg_mm=hist,
                        is_zero_measured=is_zero,
                        is_missing=False,
                        data_quality="zero_precipitation" if is_zero else "observed",
                    )
                )
    else:
        # Daily
        for idx, row in sub_df.iterrows():
            raw_obs = row["rainfall_mm"]
            m_num = row["date"].month
            daily_hist = round(district_baselines.get(m_num, 30.0) / 30.0, 1)
            if pd.isna(raw_obs):
                series_points.append(
                    RainfallSeriesPoint(
                        date=row["date"].strftime("%b %d"),
                        observed_rainfall_mm=None,
                        historical_avg_mm=daily_hist,
                        is_zero_measured=False,
                        is_missing=True,
                        data_quality="missing",
                    )
                )
            else:
                obs = float(raw_obs)
                is_zero = obs == 0.0
                series_points.append(
                    RainfallSeriesPoint(
                        date=row["date"].strftime("%b %d"),
                        observed_rainfall_mm=round(obs, 1),
                        historical_avg_mm=daily_hist,
                        is_zero_measured=is_zero,
                        is_missing=False,
                        data_quality="zero_precipitation" if is_zero else "observed",
                    )
                )

    valid_sub = sub_df["rainfall_mm"].dropna()
    baseline_sum = sum(p.historical_avg_mm for p in series_points)

    if valid_sub.empty:
        total_rain = None
        wet_days = None
        max_daily_val = None
        max_daily_dt = None
        departure_pct = None
        data_coverage_pct = 0.0
        is_data_avail = False
    else:
        total_rain = round(float(valid_sub.sum()), 1)
        wet_days = count_wet_days(sub_df, threshold_mm=2.5)
        max_idx = valid_sub.idxmax()
        max_daily_val = float(valid_sub.loc[max_idx])
        max_daily_dt = sub_df.loc[max_idx, "date"].strftime("%Y-%m-%d")
        departure_pct = (
            round(((total_rain - baseline_sum) / baseline_sum) * 100.0, 1)
            if baseline_sum > 0
            else 0.0
        )
        data_coverage_pct = round((len(valid_sub) / len(sub_df)) * 100.0, 1) if not sub_df.empty else 0.0
        is_data_avail = True

    is_demo = (mode == "demo")
    data_mode = "DEMONSTRATION" if is_demo else "CACHED_VERIFIED"

    return RainfallTrendsResponse(
        location_id=district_info["id"],
        location_name=district_info["name"],
        aggregation=aggregation,
        time_period=f"{n_days} days",
        total_rainfall_mm=total_rain,
        historical_baseline_avg_mm=round(baseline_sum, 1),
        wet_days_count=wet_days,
        max_daily_rainfall_mm=round(max_daily_val, 1) if max_daily_val is not None else None,
        max_daily_date=max_daily_dt,
        departure_percentage=departure_pct,
        data_coverage_pct=data_coverage_pct,
        is_data_available=is_data_avail,
        data_mode=data_mode,
        is_demo_data=is_demo,
        sources=["CHIRPS Daily Station Blended v2.0", "NASA GPM IMERG Late Run"],
        series=series_points,
    )
