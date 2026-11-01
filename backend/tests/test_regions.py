"""
Unit & Integration Tests for Multi-Region Foundation V1
Covers all 13 required test cases:
1. Listing all active regions.
2. Retrieving a region by ID.
3. Retrieving child regions of a state.
4. Retrieving supported hazards for a region.
5. Filtering regions by state and region type.
6. Returning 404 for an unknown region.
7. Verifying that a hazard is not presented as available if it is not supported.
8. Verifying that duplicate region codes are rejected by the database constraint.
9. Verifying that the seed script is idempotent and does not create duplicate records.
10. Verifying that existing Gorakhpur flood behavior remains functional.
11. Verifying that existing Mahoba drought behavior remains functional.
12. Verifying that requesting data for a region without datasets produces an explicit unavailable-data response.
13. Verifying that a new district never inherits another district's risk values.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.api.regions import get_optional_db
from app.db.models import Region, HazardType, RegionHazard, RegionBoundary
from app.db.seeds.seed_regions import seed_database


# Set up test database fixture (isolated in-memory SQLite with StaticPool)
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
    
    # Seed the database
    seed_database(session)
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_optional_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_db] = override_get_optional_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_optional_db, None)


# 1. Listing all active regions
def test_list_all_active_regions(client):
    response = client.get("/api/v1/regions?is_active=true")
    assert response.status_code == 200
    regions = response.json()
    assert isinstance(regions, list)
    assert len(regions) >= 10
    for reg in regions:
        assert reg["is_active"] is True
        assert "id" in reg
        assert "code" in reg
        assert "name" in reg
        assert "region_type" in reg


# 2. Retrieving a region by ID
def test_retrieve_region_by_id(client):
    # Gorakhpur
    response_gor = client.get("/api/v1/regions/district-gorakhpur")
    assert response_gor.status_code == 200
    gor = response_gor.json()
    assert gor["id"] == "district-gorakhpur"
    assert gor["name"] == "Gorakhpur"
    assert gor["code"] == "IN-UP-GOR"
    assert gor["region_type"] == "district"
    assert gor["state_code"] == "UP"
    assert any(h["code"] == "flood" and h["status"] == "pilot" for h in gor["supported_hazards"])

    # Mahoba
    response_mah = client.get("/api/v1/regions/district-mahoba")
    assert response_mah.status_code == 200
    mah = response_mah.json()
    assert mah["id"] == "district-mahoba"
    assert mah["name"] == "Mahoba"
    assert mah["code"] == "IN-UP-MAH"
    assert any(h["code"] == "drought" and h["status"] == "pilot" for h in mah["supported_hazards"])


# 3. Retrieving child regions of a state
def test_retrieve_child_regions_of_state(client):
    response = client.get("/api/v1/regions/state-uttar-pradesh/children")
    assert response.status_code == 200
    children = response.json()
    assert isinstance(children, list)
    assert len(children) >= 9
    child_ids = [r["id"] for r in children]
    assert "district-gorakhpur" in child_ids
    assert "district-mahoba" in child_ids
    assert "district-lucknow" in child_ids
    assert "district-varanasi" in child_ids
    for r in children:
        assert r["parent_id"] == "state-uttar-pradesh"
        assert r["region_type"] == "district"


# 4. Retrieving supported hazards for a region
def test_retrieve_supported_hazards_for_region(client):
    # Gorakhpur has flood enabled as pilot
    resp_gor = client.get("/api/v1/regions/district-gorakhpur/hazards")
    assert resp_gor.status_code == 200
    gor_hazards = resp_gor.json()["hazards"]
    assert len(gor_hazards) >= 1
    flood_item = next((h for h in gor_hazards if h["hazard_code"] == "flood"), None)
    assert flood_item is not None
    assert flood_item["is_enabled"] is True
    assert flood_item["configuration"].get("status") == "pilot"

    # Mahoba has drought enabled as pilot
    resp_mah = client.get("/api/v1/regions/district-mahoba/hazards")
    assert resp_mah.status_code == 200
    mah_hazards = resp_mah.json()["hazards"]
    assert len(mah_hazards) >= 1
    drought_item = next((h for h in mah_hazards if h["hazard_code"] == "drought"), None)
    assert drought_item is not None
    assert drought_item["is_enabled"] is True
    assert drought_item["configuration"].get("status") == "pilot"


# 5. Filtering regions by state and region type
def test_filter_regions_by_state_and_region_type(client):
    response = client.get("/api/v1/regions?state=UP&region_type=district")
    assert response.status_code == 200
    districts = response.json()
    assert isinstance(districts, list)
    assert len(districts) >= 9
    for r in districts:
        assert r["state_code"] == "UP"
        assert r["region_type"] == "district"

    # Filter by hazard_type
    resp_flood = client.get("/api/v1/regions?hazard_type=flood")
    assert resp_flood.status_code == 200
    flood_regions = resp_flood.json()
    assert isinstance(flood_regions, list)
    assert len(flood_regions) >= 1
    for r in flood_regions:
        assert any(h["code"] == "flood" and h["is_enabled"] for h in r["supported_hazards"])


# 6. Returning 404 for an unknown region
def test_unknown_region_returns_404(client):
    resp_reg = client.get("/api/v1/regions/district-atlantis-999")
    assert resp_reg.status_code == 404
    assert "not found" in resp_reg.json()["detail"].lower()

    resp_haz = client.get("/api/v1/regions/district-atlantis-999/hazards")
    assert resp_haz.status_code == 404

    resp_ch = client.get("/api/v1/regions/district-atlantis-999/children")
    assert resp_ch.status_code == 404


# 7. Verifying that an unsupported hazard is not presented as available
def test_unsupported_hazard_not_available(client):
    # Lucknow is not configured as a pilot hazard
    resp_luc = client.get("/api/v1/regions/district-lucknow/hazards")
    assert resp_luc.status_code == 200
    luc_hazards = resp_luc.json()["hazards"]
    for h in luc_hazards:
        assert h["is_enabled"] is False
        assert h["configuration"].get("status") == "not_configured"

    # Gorakhpur should not have drought enabled
    resp_gor = client.get("/api/v1/regions/district-gorakhpur/hazards")
    assert resp_gor.status_code == 200
    gor_hazards = resp_gor.json()["hazards"]
    gor_drought = [h for h in gor_hazards if h["hazard_code"] == "drought"]
    if gor_drought:
        assert gor_drought[0]["is_enabled"] is False


# 8. Verifying duplicate region codes are rejected by database constraint
def test_duplicate_region_codes_rejected_by_db_constraint(db_session):
    # IN-UP-GOR already exists from seed
    duplicate_region = Region(
        id="district-gorakhpur-dup",
        code="IN-UP-GOR",  # Duplicate code
        name="Gorakhpur Duplicate",
        region_type="district",
        country_code="IN",
        state_code="UP",
        is_active=True
    )
    db_session.add(duplicate_region)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 9. Verifying seed script is idempotent
def test_seed_script_is_idempotent(db_session):
    initial_regions_count = db_session.query(Region).count()
    initial_hazards_count = db_session.query(HazardType).count()
    initial_rh_count = db_session.query(RegionHazard).count()
    initial_bnd_count = db_session.query(RegionBoundary).count()

    assert initial_regions_count >= 12
    assert initial_hazards_count >= 2

    # Run seed again
    second_run_summary = seed_database(db_session)

    assert second_run_summary["regions_seeded"] == 0
    assert second_run_summary["hazard_types_seeded"] == 0
    assert second_run_summary["region_hazards_seeded"] == 0
    assert second_run_summary["boundaries_seeded"] == 0

    assert db_session.query(Region).count() == initial_regions_count
    assert db_session.query(HazardType).count() == initial_hazards_count
    assert db_session.query(RegionHazard).count() == initial_rh_count
    assert db_session.query(RegionBoundary).count() == initial_bnd_count


# 10. Verifying existing Gorakhpur flood behavior remains functional
def test_existing_gorakhpur_behavior_functional(client):
    response = client.get("/api/v1/risk/flood?location=gorakhpur")
    assert response.status_code == 200
    data = response.json()
    assert data["hazard"] == "flood"
    assert data["location"]["name"] == "Gorakhpur"
    assert "Rapti" in data["location"]["river_basin"]
    assert len(data["indicators"]) > 0
    indicator_names = [i["name"] for i in data["indicators"]]
    assert any("Cumulative" in name for name in indicator_names)


# 11. Verifying existing Mahoba drought behavior remains functional
def test_existing_mahoba_behavior_functional(client):
    response = client.get("/api/v1/risk/drought?location=mahoba")
    assert response.status_code == 200
    data = response.json()
    assert data["hazard"] == "drought"
    assert data["location"]["name"] == "Mahoba"
    assert "Bundelkhand" in data["location"]["region"]
    assert len(data["indicators"]) > 0
    indicator_names = [i["name"] for i in data["indicators"]]
    assert any("SPI" in name or "Standardized Precipitation Index" in name for name in indicator_names)


# 12. Verifying requesting data for unconfigured region produces explicit unavailable response
def test_unconfigured_region_explicit_unavailable_response(client):
    # Lucknow has no daily precipitation CSV data
    resp_flood = client.get("/api/v1/risk/flood?location=lucknow")
    assert resp_flood.status_code == 404
    assert "Daily precipitation series not found" in resp_flood.json()["detail"]

    resp_drought = client.get("/api/v1/risk/drought?location=lucknow")
    assert resp_drought.status_code == 404
    assert "Daily precipitation series not found" in resp_drought.json()["detail"]

    resp_trends = client.get("/api/v1/trends/rainfall?location=lucknow")
    assert resp_trends.status_code == 400
    assert "Daily precipitation series not found" in resp_trends.json()["detail"]


# 13. Verifying a new district never inherits another district's risk values
def test_new_district_never_inherits_another_district_risk(client, db_session):
    # Add a genuinely new unconfigured district to the database
    new_reg = Region(
        id="district-new-test",
        code="IN-UP-NEWTEST",
        name="New Test District",
        region_type="district",
        parent_id="state-uttar-pradesh",
        country_code="IN",
        state_code="UP",
        is_active=True,
        region_metadata={"river_basin": "Test Basin", "focus_type": "not_configured"}
    )
    db_session.add(new_reg)
    db_session.commit()

    # Query the region by ID
    resp = client.get("/api/v1/regions/district-new-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "district-new-test"
    assert data["name"] == "New Test District"
    assert data["code"] == "IN-UP-NEWTEST"

    # Ensure querying risk for this new district does not inherit Gorakhpur's or Mahoba's data
    resp_flood = client.get("/api/v1/risk/flood?location=new-test")
    assert resp_flood.status_code in [400, 404]
    assert "gorakhpur" not in resp_flood.text.lower()

    resp_drought = client.get("/api/v1/risk/drought?location=new-test")
    assert resp_drought.status_code in [400, 404]
    assert "mahoba" not in resp_drought.text.lower()


# 14. Verifying dashboard response with candidate district isolation
def test_dashboard_with_candidate_district(client):
    # Bihar district Patna
    resp = client.get("/api/v1/dashboard?location=patna")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_freshness_status"] == "pending_onboarding"
    assert "Patna" in data["title"]
    assert "zero data bleed" in data["disclaimer"].lower()
    assert len(data["metric_cards"]) == 4
    for card in data["metric_cards"]:
        assert card["location"] == "Patna"
        assert card["value"] is None
        assert card["is_data_available"] is False

    # Uttar Pradesh non-pilot district Lucknow
    resp_luc = client.get("/api/v1/dashboard?location=lucknow")
    assert resp_luc.status_code == 200
    data_luc = resp_luc.json()
    assert data_luc["data_freshness_status"] == "pending_onboarding"
    assert "Lucknow" in data_luc["title"]

