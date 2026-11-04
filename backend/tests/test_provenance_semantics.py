"""
JalRakshak AI — Phase 3C.2 Provenance Semantics & Temporal Classification Test Suite

Covers:
1. Past UTC hour -> historical_model_estimate.
2. Current UTC hour -> live_model_estimate.
3. Future UTC hour -> forecast.
4. Null precipitation remains missing (None).
5. Past daily NWP aggregates have historical_model_estimate provenance.
6. Mixed historical/forecast daily aggregates have mixed_model_estimate classification.
7. Pure forecast daily aggregates have forecast classification.
8. No new Open-Meteo record is labeled observed_estimate.
9. Live flood indicator category is model_derived.
10. Live drought indicator category is model_derived.
11. Live NWP indicators do not claim GPM or CHIRPS as their data source.
12. Verified-mode source attribution and categories remain intact.
13. Cache fallback and schema defaults use historical_model_estimate.
"""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd

from app.pipeline.adapters.open_meteo_forecast import (
    OpenMeteoForecastAdapter,
    DISTRICT_COORDINATES,
)
from app.schemas.environmental import (
    HourlyEnvironmentalPoint,
    DailyAggregatedPrecipitation,
)
from app.services.environmental_cache import EnvironmentalCacheService
from app.pipeline.ingestion import DataIngestionService
from app.engine.flood_engine import FloodRiskEngine
from app.engine.drought_engine import DroughtRiskEngine


def test_hourly_temporal_classification_boundaries():
    """
    Verify:
    - Past UTC hour -> historical_model_estimate (is_forecast: False)
    - Current UTC hour -> live_model_estimate (is_forecast: False)
    - Future UTC hour -> forecast (is_forecast: True)
    - Null precipitation -> missing
    """
    now_utc = datetime(2026, 11, 4, 14, 35, 22, tzinfo=timezone.utc)
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)
    past_hour = current_hour - timedelta(hours=3)
    future_hour = current_hour + timedelta(hours=3)

    payload = {
        "latitude": 26.76,
        "longitude": 83.37,
        "hourly": {
            "time": [
                past_hour.strftime("%Y-%m-%dT%H:00"),
                current_hour.strftime("%Y-%m-%dT%H:00"),
                future_hour.strftime("%Y-%m-%dT%H:00"),
                (past_hour - timedelta(hours=1)).strftime("%Y-%m-%dT%H:00"),
            ],
            "precipitation": [1.2, 0.0, 3.4, None],
            "temperature_2m": [22.0, 23.5, 21.0, 20.0],
            "relative_humidity_2m": [60.0, 55.0, 70.0, 80.0],
            "wind_speed_10m": [8.0, 10.0, 6.0, 5.0],
            "et0_fao_evapotranspiration": [0.05, 0.1, 0.02, 0.01],
        },
    }

    coords = {"lat": 26.76, "lng": 83.37, "name": "Gorakhpur"}
    parsed = OpenMeteoForecastAdapter.validate_and_parse_hourly(
        payload=payload,
        district_id="district-gorakhpur",
        coords=coords,
        retrieval_time=now_utc,
    )

    records = parsed["records"]
    assert len(records) == 4

    # 1. Past UTC hour
    rec_past = records[0]
    assert rec_past["is_forecast"] is False
    assert rec_past["quality_status"] == "historical_model_estimate"
    assert rec_past["precipitation_mm"] == 1.2

    # 2. Current UTC hour
    rec_current = records[1]
    assert rec_current["is_forecast"] is False
    assert rec_current["quality_status"] == "live_model_estimate"
    assert rec_current["precipitation_mm"] == 0.0

    # 3. Future UTC hour
    rec_future = records[2]
    assert rec_future["is_forecast"] is True
    assert rec_future["quality_status"] == "forecast"
    assert rec_future["precipitation_mm"] == 3.4

    # 4. Null precipitation
    rec_null = records[3]
    assert rec_null["precipitation_mm"] is None
    assert rec_null["quality_status"] == "missing"

    # 5. Strict rejection of legacy observed_estimate
    for r in records:
        assert r["quality_status"] != "observed_estimate"


def test_daily_aggregation_rules_pure_past_mixed_and_future():
    """
    Verify:
    - Pure past daily aggregate -> historical_model_estimate (is_forecast: False)
    - Mixed past/forecast daily aggregate -> mixed_model_estimate (is_forecast: True)
    - Pure forecast daily aggregate -> forecast (is_forecast: True)
    - Insufficient coverage (< 20h) -> missing (rainfall_mm: None)
    """
    ref_dt = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    current_hour = ref_dt.replace(minute=0, second=0, microsecond=0)

    # 1. Day 1: Pure past day (2026-11-03)
    day1_records = [
        {
            "timestamp": f"2026-11-03T{h:02d}:00",
            "dt": datetime(2026, 11, 3, h, 0, tzinfo=timezone.utc),
            "precipitation_mm": 0.5,
            "quality_status": "historical_model_estimate",
            "is_forecast": False,
        }
        for h in range(24)
    ]

    # 2. Day 2: Mixed day (2026-11-04) - 12 hours historical, 1 hour live, 11 hours forecast
    day2_records = []
    for h in range(24):
        dt = datetime(2026, 11, 4, h, 0, tzinfo=timezone.utc)
        if dt < current_hour:
            q = "historical_model_estimate"
            fc = False
        elif dt == current_hour:
            q = "live_model_estimate"
            fc = False
        else:
            q = "forecast"
            fc = True
        day2_records.append({
            "timestamp": f"2026-11-04T{h:02d}:00",
            "dt": dt,
            "precipitation_mm": 1.0,
            "quality_status": q,
            "is_forecast": fc,
        })

    # 3. Day 3: Pure forecast day (2026-11-05)
    day3_records = [
        {
            "timestamp": f"2026-11-05T{h:02d}:00",
            "dt": datetime(2026, 11, 5, h, 0, tzinfo=timezone.utc),
            "precipitation_mm": 2.0,
            "quality_status": "forecast",
            "is_forecast": True,
        }
        for h in range(24)
    ]

    # 4. Day 4: Missing coverage day (2026-11-06) - only 5 hours recorded
    day4_records = [
        {
            "timestamp": f"2026-11-06T{h:02d}:00",
            "dt": datetime(2026, 11, 6, h, 0, tzinfo=timezone.utc),
            "precipitation_mm": 1.0 if h < 5 else None,
            "quality_status": "forecast" if h < 5 else "missing",
            "is_forecast": True,
        }
        for h in range(24)
    ]

    all_records = day1_records + day2_records + day3_records + day4_records
    daily = OpenMeteoForecastAdapter.aggregate_hourly_to_daily(all_records)
    assert len(daily) == 4

    # Day 1: Pure historical day
    assert daily[0]["date"] == "2026-11-03"
    assert daily[0]["rainfall_mm"] == 12.0
    assert daily[0]["quality_status"] == "historical_model_estimate"
    assert daily[0]["is_forecast"] is False

    # Day 2: Mixed day (today)
    assert daily[1]["date"] == "2026-11-04"
    assert daily[1]["rainfall_mm"] == 24.0
    assert daily[1]["quality_status"] == "mixed_model_estimate"
    assert daily[1]["is_forecast"] is True

    # Day 3: Pure forecast day
    assert daily[2]["date"] == "2026-11-05"
    assert daily[2]["rainfall_mm"] == 48.0
    assert daily[2]["quality_status"] == "forecast"
    assert daily[2]["is_forecast"] is True

    # Day 4: Insufficient coverage
    assert daily[3]["date"] == "2026-11-06"
    assert daily[3]["rainfall_mm"] is None
    assert daily[3]["quality_status"] == "missing"
    assert daily[3]["hours_missing"] == 19


def test_hazard_engines_provenance_live_vs_verified():
    """
    Verify:
    - In mode='live': indicators are 'model_derived' and attributed to Open-Meteo.
    - In mode='live': GPM is not claimed as the rainfall source.
    - In mode='verified': indicators remain 'observed_measurement' and attributed to CHIRPS / GPM.
    """
    ingestion = DataIngestionService()
    g_info = ingestion.get_district_info("gorakhpur")
    m_info = ingestion.get_district_info("mahoba")

    daily_df = pd.DataFrame([
        {"date": pd.to_datetime("2026-10-27"), "rainfall_mm": 25.0},
        {"date": pd.to_datetime("2026-10-28"), "rainfall_mm": 15.0},
    ])

    # 1. Flood Engine in Live Mode
    flood_live = FloodRiskEngine.evaluate(g_info, daily_df, reference_date="2026-10-28", mode="live")
    ind_flood_live = {i.indicator_id: i for i in flood_live.indicators}
    src_flood_live = {s.source_id: s for s in flood_live.sources}

    assert ind_flood_live["flood_precip_7d_accum"].category == "model_derived"
    assert ind_flood_live["flood_precip_7d_accum"].quality_status == "provisional"
    assert "Open-Meteo" in ind_flood_live["flood_precip_7d_accum"].dataset_version
    assert ind_flood_live["flood_precip_30d_accum"].category == "model_derived"
    assert ind_flood_live["flood_precip_30d_accum"].quality_status == "provisional"
    assert "open_meteo_forecast" in src_flood_live
    assert "nasa_gpm_imerg" not in src_flood_live  # Does not claim GPM in live mode

    # 2. Drought Engine in Live Mode (short-window returns null / missing)
    drought_live = DroughtRiskEngine.evaluate(m_info, daily_df, reference_date="2026-10-28", mode="live")
    ind_drought_live = {i.indicator_id: i for i in drought_live.indicators}
    src_drought_live = {s.source_id: s for s in drought_live.sources}

    assert ind_drought_live["drought_precip_90d_accum"].category == "model_derived"
    assert ind_drought_live["drought_precip_90d_accum"].quality_status == "missing"
    assert ind_drought_live["drought_precip_90d_accum"].value is None
    assert "Open-Meteo" in ind_drought_live["drought_precip_90d_accum"].dataset_version
    assert "open_meteo_forecast" in src_drought_live

    # 3. Flood Engine in Verified Mode
    flood_verified = FloodRiskEngine.evaluate(g_info, daily_df, reference_date="2026-10-28", mode="verified")
    ind_flood_ver = {i.indicator_id: i for i in flood_verified.indicators}
    src_flood_ver = {s.source_id: s for s in flood_verified.sources}

    assert ind_flood_ver["flood_precip_7d_accum"].category == "observed_measurement"
    assert ind_flood_ver["flood_precip_7d_accum"].quality_status == "verified"
    assert "v07B Late Run" in ind_flood_ver["flood_precip_7d_accum"].dataset_version
    assert ind_flood_ver["flood_precip_30d_accum"].category == "observed_measurement"
    assert ind_flood_ver["flood_precip_30d_accum"].quality_status == "verified"
    assert "nasa_gpm_imerg" in src_flood_ver
    assert "chirps_daily" in src_flood_ver

    # 4. Drought Engine in Verified Mode (with full 90-day verified data)
    verified_df = ingestion.load_daily_rainfall("mahoba", mode="verified")
    drought_verified = DroughtRiskEngine.evaluate(m_info, verified_df, reference_date="2026-10-28", mode="verified")
    ind_drought_ver = {i.indicator_id: i for i in drought_verified.indicators}
    src_drought_ver = {s.source_id: s for s in drought_verified.sources}

    assert ind_drought_ver["drought_precip_90d_accum"].category == "observed_measurement"
    assert ind_drought_ver["drought_precip_90d_accum"].quality_status == "verified"
    assert ind_drought_ver["drought_precip_90d_accum"].value is not None
    assert "CHIRPS" in ind_drought_ver["drought_precip_90d_accum"].dataset_version
    assert "chirps_daily" in src_drought_ver


def test_schema_defaults_and_cache_fallback():
    """
    Verify:
    - HourlyEnvironmentalPoint default quality_status is historical_model_estimate.
    - DailyAggregatedPrecipitation default quality_status is historical_model_estimate.
    - EnvironmentalCacheService fallback assigns historical_model_estimate.
    """
    hourly_default = HourlyEnvironmentalPoint(timestamp="2026-11-04T12:00:00Z")
    assert hourly_default.quality_status == "historical_model_estimate"

    daily_default = DailyAggregatedPrecipitation(date="2026-11-04")
    assert daily_default.quality_status == "historical_model_estimate"

    # Build response from cache with minimal record missing quality_status
    cached_entry = {
        "district_id": "district-gorakhpur",
        "retrieval_timestamp": "2026-11-04T10:00:00+00:00",
        "expires_at": "2026-11-04T13:00:00+00:00",
        "coordinates": {"lat": 26.7606, "lng": 83.3732},
        "hourly_records": [
            {"timestamp": "2026-11-04T09:00:00+00:00", "precipitation_mm": 1.0}
        ],
        "daily_records": [
            {"date": "2026-11-04", "rainfall_mm": 1.0}
        ],
    }

    now_utc = datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc)
    coords = {"lat": 26.7606, "lng": 83.3732}
    resp = EnvironmentalCacheService._build_response_from_cache(
        cached_entry=cached_entry,
        district_id="district-gorakhpur",
        district_name="Gorakhpur",
        coords=coords,
        now_utc=now_utc,
        data_mode="LIVE_MODEL",
        is_cached=True,
        is_stale=False,
    )

    assert resp.hourly_series[0].quality_status == "historical_model_estimate"
    assert resp.daily_precipitation[0].quality_status == "historical_model_estimate"
