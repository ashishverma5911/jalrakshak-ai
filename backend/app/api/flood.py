from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..pipeline.ingestion import DataIngestionService
from ..engine.flood_engine import FloodRiskEngine
from ..schemas.common import HazardAssessmentResponse
from ..pipeline.validation import DataValidationError
from ..pipeline.spatial_aggregation import SpatialAggregationError

router = APIRouter(prefix="/risk", tags=["Risk Indicators"])
ingestion_service = DataIngestionService()

@router.get("/flood", response_model=HazardAssessmentResponse)
def get_flood_risk(
    location: str = Query("gorakhpur", description="Target district identifier (e.g. gorakhpur)"),
    reference_date: str = Query("2026-10-28", description="Evaluation anchor date (YYYY-MM-DD)"),
    mode: str = Query("demo", description="Data mode: 'demo' (prototype fixtures) or 'verified' (genuine observations)")
) -> HazardAssessmentResponse:
    """
    Computes flood-related meteorological accumulation and terrain indicators for the specified district.
    """
    try:
        district_info = ingestion_service.get_district_info(location)
        daily_df = ingestion_service.load_daily_rainfall(location, mode=mode)
    except (DataValidationError, SpatialAggregationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return FloodRiskEngine.evaluate(district_info, daily_df, reference_date=reference_date, mode=mode)
