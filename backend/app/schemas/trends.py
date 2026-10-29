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
    total_rainfall_mm: float
    historical_baseline_avg_mm: float
    wet_days_count: int
    max_daily_rainfall_mm: float
    max_daily_date: Optional[str] = None
    departure_percentage: float
    data_coverage_pct: float = 100.0
    observation_window: str = "Observational records (1991–2024 reference)"
    disclaimer: str = (
        "Historical observational trends only. "
        "Does not represent or imply a predictive weather forecast."
    )
    is_demo_data: bool = True
    sources: List[str]
    series: List[RainfallSeriesPoint]
