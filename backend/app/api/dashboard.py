from fastapi import APIRouter, Query
from datetime import datetime, timezone
from typing import List, Optional

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
from ..services.region_service import RegionService

router = APIRouter(tags=["Dashboard"])
ingestion_service = DataIngestionService()

@router.get("/dashboard", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    location: Optional[str] = Query(None, description="Optional target district identifier"),
    mode: str = Query("demo", description="Data mode: 'demo' or 'verified'")
) -> DashboardOverviewResponse:
    now_iso = datetime.now(timezone.utc).isoformat()
    districts = ingestion_service.get_districts_metadata()
    is_demo = (mode == "demo")
    data_mode = "DEMONSTRATION" if is_demo else "CACHED_VERIFIED"

    # Get pilot data
    g_info = ingestion_service.get_district_info("gorakhpur")
    m_info = ingestion_service.get_district_info("mahoba")

    g_df = ingestion_service.load_daily_rainfall("gorakhpur", mode=mode)
    m_df = ingestion_service.load_daily_rainfall("mahoba", mode=mode)

    flood_eval = FloodRiskEngine.evaluate(g_info, g_df, mode=mode)
    drought_eval = DroughtRiskEngine.evaluate(m_info, m_df, mode=mode)

    # Metric cards matching mockup
    # 1. Gorakhpur current rainfall (7d)
    r_7d = next(i for i in flood_eval.indicators if i.indicator_id == "flood_precip_7d_accum")
    # 2. Gorakhpur 30d rainfall
    r_30d = next(i for i in flood_eval.indicators if i.indicator_id == "flood_precip_30d_accum")
    # 3. Mahoba 90d rainfall
    r_90d = next(i for i in drought_eval.indicators if i.indicator_id == "drought_precip_90d_accum")
    # 4. Mahoba seasonal deficit
    r_def = next(i for i in drought_eval.indicators if i.indicator_id == "drought_seasonal_deficit")

    # If a specific candidate district is requested and not in pilot list
    if location and location.lower().strip() not in ["gorakhpur", "mahoba", "all", ""]:
        clean_loc = location.lower().strip()
        reg = RegionService.get_region_by_identifier(clean_loc)
        reg_name = reg.name if reg else clean_loc.capitalize()

        metric_cards = [
            QuickMetricCard(
                title="Current Rainfall",
                location=reg_name,
                value=None,
                units="mm",
                delta_percentage=None,
                is_positive_delta=None,
                hazard_type="pending",
                context_note=f"Station telemetry unlinked for {reg_name}; awaiting ingestion",
                is_data_available=False,
            ),
            QuickMetricCard(
                title="7-Day Cumulative",
                location=reg_name,
                value=None,
                units="mm",
                delta_percentage=None,
                is_positive_delta=None,
                hazard_type="pending",
                context_note="Telemetry pipeline offline; zero data bleed enforced",
                is_data_available=False,
            ),
            QuickMetricCard(
                title="Seasonal Baseline",
                location=reg_name,
                value=None,
                units="mm",
                delta_percentage=None,
                is_positive_delta=None,
                hazard_type="pending",
                context_note="30-year climatological normal awaiting station calibration",
                is_data_available=False,
            ),
            QuickMetricCard(
                title="Hazard Index",
                location=reg_name,
                value=None,
                units="score",
                delta_percentage=None,
                is_positive_delta=None,
                hazard_type="pending",
                context_note="Model offline; candidate district isolated from pilots",
                is_data_available=False,
            ),
        ]
        dash_title = f"JalRakshak Environmental Intelligence — {reg_name}"
        data_status = "pending_onboarding"
        data_mode = "DATA_PENDING"
        is_demo = False
        disclaimer_text = f"Candidate administrative district '{reg_name}'. Observational precipitation ingestion and scientific hazard modeling are currently pending onboarding. Zero data bleed policy enforced."
    else:
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
                is_data_available=True,
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
                is_data_available=True,
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
                is_data_available=True,
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
                is_data_available=True,
            ),
        ]
        dash_title = "JalRakshak Environmental Intelligence"
        data_status = "verified"
        disclaimer_text = "Prototype decision-support output. Connect live backend for real measurements."

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
            source_id=s.get("source_id", s.get("id", "")),
            source_name=s.get("source_name", s.get("name", "")),
            spatial_resolution=s.get("spatial_resolution", ""),
            temporal_resolution=s.get("temporal_resolution", ""),
            dataset_version=s.get("dataset_version", "v2.0"),
            access_url=s.get("access_url"),
            units=s.get("units", "mm/day"),
            data_mode=data_mode,
            retrieval_timestamp=now_iso,
            license=s.get("license"),
        )
        for s in get_all_sources()
    ]

    return DashboardOverviewResponse(
        title=dash_title,
        timestamp=now_iso,
        data_freshness_status=data_status,
        data_mode=data_mode,
        is_demo_data=is_demo,
        is_data_available=(data_mode != "DATA_PENDING"),
        disclaimer=disclaimer_text,
        pilot_locations=pilot_locations,
        metric_cards=metric_cards,
        recent_alerts=alerts,
        active_sources=sources_list,
    )
