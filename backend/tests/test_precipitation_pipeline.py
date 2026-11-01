"""
Tests for Precipitation Ingestion & Scientific Validation Pipeline (Milestone 2 - Step 5)
Verifies:
- Scientific rainfall validation (rejection of negatives, extreme value review flagging)
- Missing day representation (None / 'missing')
- Idempotent batch upserting
- CSV ingestion of pilot series
"""
import pytest
from datetime import date
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import DATA_DIR
from app.db.base import Base
from app.db.models import Region, DailyPrecipitation
from app.db.seeds.seed_regions import seed_database
from app.pipeline.precipitation_pipeline import (
    PrecipitationIngestionService,
    PrecipitationValidationError,
)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_validate_observation_rules():
    # Negative value rejected
    with pytest.raises(PrecipitationValidationError):
        PrecipitationIngestionService.validate_observation(-1.5)

    # Missing / NaN
    val_none, status_none = PrecipitationIngestionService.validate_observation(None)
    assert val_none is None
    assert status_none == "missing"

    # Zero measured rain
    val_zero, status_zero = PrecipitationIngestionService.validate_observation(0.0)
    assert val_zero == 0.0
    assert status_zero == "zero_precipitation"

    # Normal observed rain
    val_norm, status_norm = PrecipitationIngestionService.validate_observation(24.5)
    assert val_norm == 24.5
    assert status_norm == "observed"

    # Extreme cloudburst rain (> 500 mm) flagged for scientific review
    val_ext, status_ext = PrecipitationIngestionService.validate_observation(540.2)
    assert val_ext == 540.2
    assert status_ext == "provisional_extreme"


def test_ingest_records_idempotent_and_safe(db_session):
    records = [
        {"date": "2024-07-01", "rainfall_mm": 10.0, "source": "chirps_daily"},
        {"date": "2024-07-02", "rainfall_mm": -4.0, "source": "chirps_daily"},  # Should be rejected
        {"date": "2024-07-03", "rainfall_mm": 520.0, "source": "chirps_daily"}, # Provisional extreme
        {"date": "2024-07-04", "rainfall_mm": None, "source": "chirps_daily"},  # Missing
        {"date": "2024-07-05", "rainfall_mm": 0.0, "source": "chirps_daily"},   # Zero rain
    ]

    res1 = PrecipitationIngestionService.ingest_records(
        db=db_session,
        region_id="district-gorakhpur",
        records=records,
        is_demo_data=True
    )

    assert res1["inserted"] == 4  # 4 valid dates
    assert res1["rejected_negative"] == 1
    assert res1["provisional_extreme"] == 1
    assert res1["missing_stored"] == 1

    # Verify query
    series = PrecipitationIngestionService.query_series(
        db=db_session,
        region_id="district-gorakhpur",
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 5)
    )
    assert len(series) == 4
    dates = [s["observation_date"] for s in series]
    assert "2024-07-02" not in dates  # Negative was rejected

    # Idempotent re-run
    res2 = PrecipitationIngestionService.ingest_records(
        db=db_session,
        region_id="district-gorakhpur",
        records=records,
        is_demo_data=True
    )
    assert res2["inserted"] == 0
    assert res2["updated"] == 4
    assert res2["rejected_negative"] == 1


def test_ingest_sample_from_csv(db_session):
    csv_path = DATA_DIR / "mahoba_chirps_daily.csv"
    assert csv_path.exists()

    # Ingest CSV file
    stats = PrecipitationIngestionService.ingest_csv_file(
        db=db_session,
        csv_path=csv_path,
        region_id="district-mahoba",
        default_source="chirps_daily",
        is_demo_data=True
    )
    assert stats["inserted"] > 4000
    assert stats["rejected_negative"] == 0

    # Query latest days
    latest = PrecipitationIngestionService.query_series(
        db=db_session,
        region_id="district-mahoba",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 28)
    )
    assert len(latest) == 9
    for row in latest:
        assert row["region_id"] == "district-mahoba"
        assert row["rainfall_mm"] == 0.0
        assert row["quality_status"] == "zero_precipitation"
