from fastapi import APIRouter
from datetime import datetime, timezone
from typing import List

from ..pipeline.ingestion import DataIngestionService
from ..engine.flood_engine import FloodRiskEngine
from ..engine.drought_engine import DroughtRiskEngine
from ..schemas.dashboard import (
    DashboardOverviewResponse,
    QuickMetricCard,
    AlertNotice,
)
from ..schemas.common import LocationReference, SourceMetadata
from ..core.provenance import get_all_sources

router = APIRouter(tags=["Dashboard"])
ingestion_service = DataIngestionService()

@router.get("/dashboard", response_model=DashboardOverviewResponse)
def get_dashboard_overview() -> DashboardOverviewResponse:
    now_iso = datetime.now(timezone.utc).isoformat()
    districts = ingestion_service.get_districts_metadata()

    # Get pilot data
    g_info = ingestion_service.get_district_info("gorakhpur")
    m_info = ingestion_service.get_district_info("mahoba")

    g_df = ingestion_service.load_daily_rainfall("gorakhpur")
    m_df = ingestion_service.load_daily_rainfall("mahoba")

    flood_eval = FloodRiskEngine.evaluate(g_info, g_df)
    drought_eval = DroughtRiskEngine.evaluate(m_info, m_df)

    # Metric cards matching mockup
    # 1. Gorakhpur current rainfall (7d)
    r_7d = next(i for i in flood_eval.indicators if i.indicator_id == "flood_precip_7d_accum")
    # 2. Gorakhpur 30d rainfall
    r_30d = next(i for i in flood_eval.indicators if i.indicator_id == "flood_precip_30d_accum")
    # 3. Mahoba 90d rainfall
    r_90d = next(i for i in drought_eval.indicators if i.indicator_id == "drought_precip_90d_accum")
    # 4. Mahoba seasonal deficit
    r_def = next(i for i in drought_eval.indicators if i.indicator_id == "drought_seasonal_deficit")

    metric_cards = [
        QuickMetricCard(
            title="Current Rainfall",
            location="Gorakhpur",
            value=r_7d.value,
            units="mm",
            delta_percentage=65.0,
            is_positive_delta=True,
            hazard_type="flood",
            context_note="7-day cumulative rainfall exceeding normal",
        ),
        QuickMetricCard(
            title="7-Day Rainfall",
            location="Gorakhpur",
            value=r_30d.value,
            units="mm",
            delta_percentage=48.0,
            is_positive_delta=True,
            hazard_type="flood",
            context_note="30-day cumulative precipitation volume",
        ),
        QuickMetricCard(
            title="90-Day Rainfall",
            location="Mahoba",
            value=r_90d.value,
            units="mm",
            delta_percentage=-58.0,
            is_positive_delta=False,
            hazard_type="drought",
            context_note="90-day rainfall anomaly below historical median",
        ),
        QuickMetricCard(
            title="Seasonal Deficit",
            location="Mahoba",
            value=r_def.value,
            units="percentage",
            delta_percentage=r_def.value,
            is_positive_delta=False,
            hazard_type="drought",
            context_note="Severe monsoon deficit in Bundelkhand plateau",
        ),
    ]

    pilot_locations = [
        LocationReference(
            location_id=d["id"],
            name=d["name"],
            hindi_name=d["hindi_name"],
            latitude=d["lat"],
            longitude=d["lng"],
            elevation_m=d["elevation_m"],
            river_basin=d["river_basin"],
            region=d["region"],
            is_pilot=d["is_pilot"],
        )
        for d in districts
        if d["is_pilot"]
    ]

    alerts = [
        AlertNotice(
            id="alt-01",
            title="High Rainfall Alert",
            location="Gorakhpur",
            severity="high",
            description="Recent 7-day rainfall significantly above historical average. Low-lying Rapti basin tracts sensitive.",
            issued_at="28 Oct 2026, 10:30 AM",
            is_official_warning=False,
            source_agency="JalRakshak Engine / GPM Data",
        ),
        AlertNotice(
            id="alt-02",
            title="Drought Watch",
            location="Mahoba",
            severity="moderate",
            description="Precipitation deficit -72% below historical average for the season. Extended dry spells observed.",
            issued_at="28 Oct 2026, 10:30 AM",
            is_official_warning=False,
            source_agency="JalRakshak Engine / CHIRPS Data",
        ),
    ]

    sources_list = [
        SourceMetadata(
            source_id=s["id"],
            source_name=s["name"],
            spatial_resolution=s["spatial_resolution"],
            temporal_resolution=s["temporal_resolution"],
            access_url=s["access_url"],
            units=s["units"],
            retrieval_timestamp=now_iso,
        )
        for s in get_all_sources()
    ]

    return DashboardOverviewResponse(
        title="JalRakshak Environmental Intelligence",
        timestamp=now_iso,
        data_freshness_status="verified",
        is_demo_data=True,
        disclaimer="Prototype decision-support output. Connect live backend for real measurements.",
        pilot_locations=pilot_locations,
        metric_cards=metric_cards,
        recent_alerts=alerts,
        active_sources=sources_list,
    )
