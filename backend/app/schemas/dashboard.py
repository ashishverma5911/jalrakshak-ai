from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .common import LocationReference, SourceMetadata, RiskIndicator

class QuickMetricCard(BaseModel):
    title: str
    location: str
    value: float
    units: str
    delta_percentage: float
    is_positive_delta: bool
    hazard_type: str
    context_note: str

class AlertNotice(BaseModel):
    id: str
    title: str
    location: str
    severity: str
    description: str
    issued_at: str
    is_official_warning: bool = False
    source_agency: str

class DashboardOverviewResponse(BaseModel):
    title: str = "JalRakshak Environmental Intelligence"
    timestamp: str
    data_freshness_status: str
    is_demo_data: bool = True
    disclaimer: str
    pilot_locations: List[LocationReference]
    metric_cards: List[QuickMetricCard]
    recent_alerts: List[AlertNotice]
    active_sources: List[SourceMetadata]
