"""
Tests for Boundary Ingestion and Spatial Validation Service (Milestone 2 - Step 2)
Verifies:
- Geometry topology validation (Shapely)
- Territorial bounding box validation for India
- Non-fabrication transparency (centroids clearly flagged)
- Ingestion of valid district polygon geometries
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Region, RegionBoundary
from app.db.seeds.seed_regions import seed_database
from app.services.boundary_service import (
    BoundaryIngestionService,
    BoundaryValidationError,
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


def test_validate_geometry_valid_polygon():
    # Valid simplified polygon over Gorakhpur region
    valid_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [83.20, 26.60],
                [83.50, 26.60],
                [83.50, 26.90],
                [83.20, 26.90],
                [83.20, 26.60],
            ]
        ]
    }
    geom, stats = BoundaryIngestionService.validate_geometry(valid_poly)
    assert stats["is_valid"] is True
    assert stats["geom_type"] == "Polygon"
    assert stats["approx_area_deg2"] > 0.0


def test_validate_geometry_rejects_out_of_bounds_coords():
    # Polygon located in Europe / Atlantic (outside India bounds)
    invalid_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [10.0, 50.0],
                [12.0, 50.0],
                [12.0, 52.0],
                [10.0, 52.0],
                [10.0, 50.0],
            ]
        ]
    }
    with pytest.raises(BoundaryValidationError) as exc:
        BoundaryIngestionService.validate_geometry(invalid_poly)
    assert "territorial bounds of India" in str(exc.value)


def test_audit_boundary_status_flags_centroid_transparently(db_session):
    # Gorakhpur starts with centroid-only point geometry
    status = BoundaryIngestionService.audit_boundary_status(db_session, "district-gorakhpur")
    assert status["has_geometry"] is True
    assert status["geometry_mode"] == "centroid_point"
    assert status["is_polygon_integrated"] is False
    assert "Full administrative polygon unintegrated" in status["disclaimer"]


def test_ingest_feature_updates_boundary_to_polygon(db_session):
    valid_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [83.20, 26.60],
                [83.50, 26.60],
                [83.50, 26.90],
                [83.20, 26.90],
                [83.20, 26.60],
            ]
        ]
    }
    result = BoundaryIngestionService.ingest_feature(
        db=db_session,
        region_id="district-gorakhpur",
        geometry=valid_poly,
        source="survey_of_india_geojson_test",
        version="2024.1",
        license_str="GODL-India"
    )
    assert result["status"] == "ingested_verified"

    # Now audit should report vector_polygon
    audit = BoundaryIngestionService.audit_boundary_status(db_session, "district-gorakhpur")
    assert audit["geometry_mode"] == "vector_polygon"
    assert audit["is_polygon_integrated"] is True
    assert "Validated administrative boundary polygon" in audit["disclaimer"]
