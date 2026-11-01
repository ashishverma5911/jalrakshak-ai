"""
Tests for Complete Bihar and Uttar Pradesh Administrative Hierarchy (Milestone 2 - Step 3)
Verifies:
- 75 Districts in Uttar Pradesh
- 38 Districts in Bihar
- Parent-child linking (Country -> State -> District)
- Non-pilot districts have no active hazard models
- Querying risk for Bihar districts produces explicit unavailable response
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.api.regions import get_optional_db
from app.db.seeds.seed_regions import seed_database


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


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_optional_db, None)


def test_bihar_state_children_returns_38_districts(client):
    resp = client.get("/api/v1/regions/state-bihar/children")
    assert resp.status_code == 200
    districts = resp.json()
    assert len(districts) == 38
    codes = [d["code"] for d in districts]
    assert "IN-BR-PAT" in codes  # Patna
    assert "IN-BR-GAY" in codes  # Gaya
    assert "IN-BR-BHA" in codes  # Bhagalpur
    for d in districts:
        assert d["parent_id"] == "state-bihar"
        assert d["state_code"] == "BR"
        assert d["country_code"] == "IN"
        assert d["region_type"] == "district"


def test_uttar_pradesh_state_children_returns_75_districts(client):
    resp = client.get("/api/v1/regions/state-uttar-pradesh/children")
    assert resp.status_code == 200
    districts = resp.json()
    assert len(districts) == 75
    codes = [d["code"] for d in districts]
    assert "IN-UP-GOR" in codes  # Gorakhpur
    assert "IN-UP-MAH" in codes  # Mahoba
    assert "IN-UP-LUC" in codes  # Lucknow
    assert "IN-UP-VAR" in codes  # Varanasi
    for d in districts:
        assert d["parent_id"] == "state-uttar-pradesh"
        assert d["state_code"] == "UP"
        assert d["country_code"] == "IN"


def test_state_filter_query_params(client):
    # Filter by state=BR
    resp_br = client.get("/api/v1/regions?state=BR&region_type=district")
    assert resp_br.status_code == 200
    assert len(resp_br.json()) == 38

    # Filter by state=UP
    resp_up = client.get("/api/v1/regions?state=UP&region_type=district")
    assert resp_up.status_code == 200
    assert len(resp_up.json()) == 75


def test_bihar_districts_have_no_active_hazard_models(client):
    # Patna
    resp_pat = client.get("/api/v1/regions/district-patna/hazards")
    assert resp_pat.status_code == 200
    hazards = resp_pat.json()["hazards"]
    assert len(hazards) == 2
    for h in hazards:
        assert h["is_enabled"] is False
        assert h["configuration"].get("status") == "not_configured"


def test_bihar_district_risk_query_returns_explicit_unavailable(client):
    # Patna has no pilot hazard or daily rainfall CSV
    resp_flood = client.get("/api/v1/risk/flood?location=patna")
    assert resp_flood.status_code in [400, 404]
    assert "gorakhpur" not in resp_flood.text.lower()

    resp_drought = client.get("/api/v1/risk/drought?location=patna")
    assert resp_drought.status_code in [400, 404]
    assert "mahoba" not in resp_drought.text.lower()
