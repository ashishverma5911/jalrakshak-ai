from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class RainfallSeriesPoint(BaseModel):
    date: str
    observed_rainfall_mm: Optional[float] = None
    historical_avg_mm: float
    anomaly_percentage: Optional[float] = None
    is_zero_measured: bool = False
    is_missing: bool = False
    data_quality: Literal["observed", "zero_precipitation", "missing"] = "observed"

class RainfallTrendsResponse(BaseModel):
    location_id: str
    location_name: str
    aggregation: str
    time_period: str
    total_rainfall_mm: Optional[float] = None
    historical_baseline_avg_mm: Optional[float] = None
    wet_days_count: Optional[int] = None
    max_daily_rainfall_mm: Optional[float] = None
    max_daily_date: Optional[str] = None
    departure_percentage: Optional[float] = None
    data_coverage_pct: float = 100.0
    is_data_available: bool = True
    observation_window: str = "Observational records (1991–2026 reference)"
    disclaimer: str = (
        "Historical observational trends only. "
        "Does not represent or imply a predictive weather forecast."
    )
    data_mode: str = "CACHED_VERIFIED"
    is_demo_data: bool = False
    sources: List[str]
    series: List[RainfallSeriesPoint]
