import pytest
import pandas as pd
from datetime import datetime

from app.pipeline.ingestion import DataIngestionService
from app.engine.flood_engine import FloodRiskEngine
from app.engine.drought_engine import DroughtRiskEngine

@pytest.fixture
def ingestion_service():
    return DataIngestionService()

def test_flood_engine_gorakhpur(ingestion_service):
    district_info = ingestion_service.get_district_info("gorakhpur")
    df = ingestion_service.load_daily_rainfall("gorakhpur")

    result = FloodRiskEngine.evaluate(district_info, df)

    assert result.hazard == "flood"
    assert result.location.location_id == "gorakhpur"
    assert result.location.name == "Gorakhpur"
    assert result.risk_level in ["high", "moderate", "low"]
    assert result.is_demo_data is True

    # Check indicator names and units
    indicator_ids = [ind.indicator_id for ind in result.indicators]
    assert "flood_precip_7d_accum" in indicator_ids
    assert "flood_precip_7d_anomaly" in indicator_ids
    assert "flood_precip_30d_accum" in indicator_ids
    assert "flood_historical_percentile" in indicator_ids

    # Scientific notes must emphasize no direct inundation claim
    notes_text = " ".join(result.scientific_notes)
    assert "inundation" in notes_text.lower()
    assert "cwc" in notes_text.lower() or "upsdma" in notes_text.lower()

def test_drought_engine_mahoba(ingestion_service):
    district_info = ingestion_service.get_district_info("mahoba")
    df = ingestion_service.load_daily_rainfall("mahoba")

    result = DroughtRiskEngine.evaluate(district_info, df)

    assert result.hazard == "drought"
    assert result.location.location_id == "mahoba"
    assert result.location.name == "Mahoba"
    assert result.risk_level in ["high", "moderate", "low"]
    assert result.is_demo_data is True

    indicator_ids = [ind.indicator_id for ind in result.indicators]
    assert "drought_precip_90d_accum" in indicator_ids
    assert "drought_seasonal_deficit" in indicator_ids
    assert "drought_spi_3" in indicator_ids
    assert "drought_consecutive_dry_days" in indicator_ids

    # Ensure limitation notes exist
    notes_text = " ".join(result.scientific_notes)
    assert "crop" in notes_text.lower() or "groundwater" in notes_text.lower()
