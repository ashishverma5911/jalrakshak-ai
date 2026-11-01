"""
Unit and Integration Tests for Timeseries Database Foundation (Milestone 2 - Phase 1)
Tests DailyPrecipitation model:
- Composite primary key (region_id, observation_date)
- Negative value rejection by database check constraint
- Extreme value (>500mm) acceptance with provisional_extreme status
- Missing date handling (None rainfall with quality_status='missing')
- Foreign key linking to Region
- Time-series range querying
"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.models import Region, DailyPrecipitation
from app.db.seeds.seed_regions import seed_database


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite test session with StaticPool for schema and model testing."""
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


def test_insert_valid_precipitation_record(db_session):
    record = DailyPrecipitation(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 15),
        rainfall_mm=45.5,
        data_source="chirps_daily",
        quality_status="observed",
        observation_metadata={"resolution_deg": 0.05, "source_version": "2.0"}
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.query(DailyPrecipitation).filter_by(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 15)
    ).first()

    assert retrieved is not None
    assert retrieved.rainfall_mm == 45.5
    assert retrieved.quality_status == "observed"
    assert retrieved.region.name == "Gorakhpur"
    assert retrieved.to_dict()["rainfall_mm"] == 45.5


def test_duplicate_primary_key_rejected(db_session):
    rec1 = DailyPrecipitation(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 15),
        rainfall_mm=30.0,
        data_source="chirps_daily",
        quality_status="observed"
    )
    db_session.add(rec1)
    db_session.commit()

    # Attempt duplicate insert with same composite PK (region_id, observation_date)
    rec2 = DailyPrecipitation(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 15),
        rainfall_mm=50.0,
        data_source="nasa_gpm_imerg",
        quality_status="observed"
    )
    db_session.add(rec2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_negative_rainfall_rejected_by_check_constraint(db_session):
    invalid_record = DailyPrecipitation(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 16),
        rainfall_mm=-5.0,  # Negative rainfall is physically impossible
        data_source="chirps_daily",
        quality_status="unverified"
    )
    db_session.add(invalid_record)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_extreme_rainfall_accepted_with_provisional_extreme_status(db_session):
    # Values above 500 mm must be flagged as provisional_extreme for review, not rejected
    extreme_record = DailyPrecipitation(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 17),
        rainfall_mm=562.4,
        data_source="chirps_daily",
        quality_status="provisional_extreme",
        observation_metadata={"notes": "Extreme cloudburst event pending hydrological cross-verification"}
    )
    db_session.add(extreme_record)
    db_session.commit()

    retrieved = db_session.query(DailyPrecipitation).filter_by(
        region_id="district-gorakhpur",
        observation_date=date(2024, 8, 17)
    ).first()

    assert retrieved is not None
    assert retrieved.rainfall_mm == 562.4
    assert retrieved.quality_status == "provisional_extreme"


def test_missing_observation_stored_as_null(db_session):
    missing_record = DailyPrecipitation(
        region_id="district-mahoba",
        observation_date=date(2024, 8, 18),
        rainfall_mm=None,  # Null indicates missing measurement
        data_source="chirps_daily",
        quality_status="missing",
        observation_metadata={"reason": "Satellite sensor orbit gap"}
    )
    db_session.add(missing_record)
    db_session.commit()

    retrieved = db_session.query(DailyPrecipitation).filter_by(
        region_id="district-mahoba",
        observation_date=date(2024, 8, 18)
    ).first()

    assert retrieved is not None
    assert retrieved.rainfall_mm is None
    assert retrieved.quality_status == "missing"


def test_time_series_date_range_query(db_session):
    # Insert multiple sequential days
    observations = [
        DailyPrecipitation(region_id="district-mahoba", observation_date=date(2024, 9, 1), rainfall_mm=0.0, quality_status="zero_precipitation"),
        DailyPrecipitation(region_id="district-mahoba", observation_date=date(2024, 9, 2), rainfall_mm=12.2, quality_status="observed"),
        DailyPrecipitation(region_id="district-mahoba", observation_date=date(2024, 9, 3), rainfall_mm=0.0, quality_status="zero_precipitation"),
        DailyPrecipitation(region_id="district-mahoba", observation_date=date(2024, 9, 4), rainfall_mm=25.8, quality_status="observed"),
    ]
    db_session.add_all(observations)
    db_session.commit()

    # Query range
    results = db_session.query(DailyPrecipitation).filter(
        DailyPrecipitation.region_id == "district-mahoba",
        DailyPrecipitation.observation_date >= date(2024, 9, 2),
        DailyPrecipitation.observation_date <= date(2024, 9, 4)
    ).order_by(DailyPrecipitation.observation_date.asc()).all()

    assert len(results) == 3
    assert [r.rainfall_mm for r in results] == [12.2, 0.0, 25.8]
