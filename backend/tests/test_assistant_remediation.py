"""
Phase 1 Critical Audit Defect Remediation Test Suite
Validates the complete remediation of:
1. False-Zero Fallback Corruption (0.0 mm must remain 0.0 mm, missing values must not invent 286.0 mm or 94.2 percentile).
2. District Keyword Hijacking (Hazard keywords like 'flood' or 'drought' must never override explicit user-selected location).
3. Grounding and Data Provenance (No false claims of GPM IMERG operational scoring; strict candidate district isolation).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.assistant_engine import GroundedAssistantEngine

client = TestClient(app)


# ---------------------------------------------------------------------------
# Requirement 1: Gorakhpur with 0.0 mm rainfall: output must remain 0.0 mm
# ---------------------------------------------------------------------------
def test_gorakhpur_zero_rainfall_preserved():
    """Gorakhpur with valid 0.0 mm rainfall must preserve 0.0 mm and not revert to 286.0 mm."""
    grounded_data = {
        "target_location": "gorakhpur",
        "evidence_items": [],
        "indicators_list": [],
        "limitations": [],
        "citations": ["CHIRPS v2.0 Daily"],
        "timestamps": {"retrieval_timestamp": "2026-10-31T00:00:00Z"},
        "is_demo_data": False,
        "data_mode": "CACHED_VERIFIED",
    }
    # Pass explicit 0.0 values (which are falsy in Python bool evaluation)
    grounded_data["evidence_items"] = [
        type("Item", (), {"indicator_id": "flood_precip_7d_accum", "value": 0.0})(),
        type("Item", (), {"indicator_id": "flood_precip_7d_anomaly", "value": -100.0})(),
        type("Item", (), {"indicator_id": "flood_historical_percentile", "value": 0.0})(),
    ]

    answer = GroundedAssistantEngine.synthesize_transparent_grounded_answer(
        query="What is the 7-day rainfall in Gorakhpur?",
        grounded_data=grounded_data
    )

    # Must preserve 0.0 mm
    assert "0.0 mm" in answer, f"Expected '0.0 mm' in answer, got:\n{answer}"
    assert "286.0" not in answer, f"Found corrupted demo constant 286.0 in answer:\n{answer}"
    assert "0.0th percentile" in answer, f"Expected '0.0th percentile' in answer, got:\n{answer}"
    assert "94.2" not in answer, f"Found corrupted demo percentile 94.2 in answer:\n{answer}"


# ---------------------------------------------------------------------------
# Requirement 2: Gorakhpur with missing rainfall: must not invent 286.0 mm
# ---------------------------------------------------------------------------
def test_gorakhpur_missing_rainfall_not_invented():
    """Missing rainfall observations must state 'Data unavailable' and not invent 286.0 mm."""
    grounded_data = {
        "target_location": "gorakhpur",
        "evidence_items": [],  # Completely missing indicators
        "indicators_list": [],
        "limitations": [],
        "citations": ["CHIRPS v2.0 Daily"],
        "timestamps": {"retrieval_timestamp": "2026-10-31T00:00:00Z"},
        "is_demo_data": False,
        "data_mode": "CACHED_VERIFIED",
    }

    answer = GroundedAssistantEngine.synthesize_transparent_grounded_answer(
        query="What is the 7-day rainfall in Gorakhpur?",
        grounded_data=grounded_data
    )

    assert "Data unavailable" in answer, f"Expected 'Data unavailable' in answer, got:\n{answer}"
    assert "286.0" not in answer, f"Found invented 286.0 mm in answer:\n{answer}"
    assert "512.0" not in answer, f"Found invented 512.0 mm in answer:\n{answer}"


# ---------------------------------------------------------------------------
# Requirement 3: Lucknow + 'What is the flood risk?': must not return Gorakhpur data
# ---------------------------------------------------------------------------
def test_lucknow_flood_query_isolation():
    """User-selected location Lucknow with a flood query must never return Gorakhpur data."""
    payload = {
        "query": "What is the flood risk in Lucknow right now?",
        "location": "lucknow"
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must NOT route to Gorakhpur
    assert "Gorakhpur" not in data["answer"], "Found Gorakhpur data in Lucknow query"
    assert "Rapti" not in data["answer"], "Found Rapti river context in Lucknow query"
    assert "77.7m" not in data["answer"], "Found Gorakhpur elevation in Lucknow query"

    # Must be DATA_PENDING for Lucknow
    assert "Lucknow" in data["answer"]
    assert "DATA_PENDING" in data["answer"]
    assert "Zero cross-district data bleed is strictly enforced" in data["answer"]
    assert len(data["evidence_used"]) == 0, f"Evidence leaked to candidate district: {data['evidence_used']}"


# ---------------------------------------------------------------------------
# Requirement 4: Patna + 'What is the drought risk?': must not return Mahoba data
# ---------------------------------------------------------------------------
def test_patna_drought_query_isolation():
    """User-selected location Patna with a drought query must never return Mahoba data."""
    payload = {
        "query": "What is the drought risk and seasonal deficit in Patna?",
        "location": "patna"
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must NOT route to Mahoba
    assert "Mahoba" not in data["answer"], "Found Mahoba data in Patna query"
    assert "Bundelkhand" not in data["answer"], "Found Bundelkhand context in Patna query"
    assert "197.1m" not in data["answer"], "Found Mahoba elevation in Patna query"

    # Must be DATA_PENDING for Patna
    assert "Patna" in data["answer"]
    assert "DATA_PENDING" in data["answer"]
    assert "Zero cross-district data bleed is strictly enforced" in data["answer"]
    assert len(data["evidence_used"]) == 0, f"Evidence leaked to candidate district: {data['evidence_used']}"


# ---------------------------------------------------------------------------
# Requirement 5: Mahoba + drought query: must use Mahoba data only
# ---------------------------------------------------------------------------
def test_mahoba_drought_query_uses_mahoba_data_only():
    """Mahoba queries must use Mahoba indicators and never leak Gorakhpur data."""
    payload = {
        "query": "What is the drought index and deficit?",
        "location": "mahoba"
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "Mahoba" in data["answer"]
    assert "Bundelkhand" in data["answer"]
    assert "Gorakhpur" not in data["answer"]
    assert "Rapti" not in data["answer"]
    assert len(data["evidence_used"]) > 0
    indicator_ids = [e["indicator_id"] for e in data["evidence_used"]]
    assert any("drought" in ind for ind in indicator_ids)
    assert not any("flood" in ind for ind in indicator_ids)


# ---------------------------------------------------------------------------
# Requirement 6: Gorakhpur + flood query: must use Gorakhpur data only
# ---------------------------------------------------------------------------
def test_gorakhpur_flood_query_uses_gorakhpur_data_only():
    """Gorakhpur queries must use Gorakhpur indicators and never leak Mahoba data."""
    payload = {
        "query": "What is the flood risk and recent rainfall?",
        "location": "gorakhpur"
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "Gorakhpur" in data["answer"]
    assert "Rapti" in data["answer"]
    assert "Mahoba" not in data["answer"]
    assert "Bundelkhand" not in data["answer"]
    assert len(data["evidence_used"]) > 0
    indicator_ids = [e["indicator_id"] for e in data["evidence_used"]]
    assert any("flood" in ind for ind in indicator_ids)
    assert not any("drought" in ind for ind in indicator_ids)


# ---------------------------------------------------------------------------
# Requirement 7: Unsupported district: must return DATA_PENDING
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cand_id", ["lucknow", "patna", "gaya", "varanasi"])
def test_unsupported_district_returns_data_pending(cand_id):
    """Unsupported districts must return DATA_PENDING with zero cross-district bleed."""
    payload = {
        "query": f"What is the status of {cand_id}?",
        "location": cand_id
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "DATA_PENDING" in data["answer"]
    assert "Zero cross-district data bleed is strictly enforced" in data["answer"]
    assert cand_id.capitalize() in data["answer"]
    assert len(data["evidence_used"]) == 0
    assert len(data["relevant_indicators"]) == 0


# ---------------------------------------------------------------------------
# Requirement 8: Missing historical percentile: must not invent a percentile
# ---------------------------------------------------------------------------
def test_missing_historical_percentile_not_invented():
    """Missing percentile must state calculation unavailable and not invent 94.2."""
    grounded_data = {
        "target_location": "gorakhpur",
        "evidence_items": [
            type("Item", (), {"indicator_id": "flood_precip_7d_accum", "value": 15.0})(),
            # No flood_historical_percentile in evidence items
        ],
        "indicators_list": [],
        "limitations": [],
        "citations": ["CHIRPS v2.0 Daily"],
        "timestamps": {"retrieval_timestamp": "2026-10-31T00:00:00Z"},
        "is_demo_data": False,
        "data_mode": "CACHED_VERIFIED",
    }

    answer = GroundedAssistantEngine.synthesize_transparent_grounded_answer(
        query="What is the historical percentile in Gorakhpur?",
        grounded_data=grounded_data
    )

    assert "Historical percentile calculation unavailable" in answer
    assert "94.2" not in answer, f"Found invented percentile 94.2 in answer:\n{answer}"


# ---------------------------------------------------------------------------
# Requirement 9: Verify the API and Assistant both enforce district isolation
# ---------------------------------------------------------------------------
def test_api_and_assistant_district_isolation():
    """Both API endpoints and Assistant must enforce strict district isolation."""
    # 1. Dashboard API isolation
    dash_resp = client.get("/api/v1/dashboard?location=lucknow")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["data_mode"] == "DATA_PENDING"
    assert all(card["value"] is None for card in dash_data["metric_cards"])
    assert all(card["is_data_available"] is False for card in dash_data["metric_cards"])
    assert all(card["hazard_type"] == "pending" for card in dash_data["metric_cards"])

    # 2. Direct Risk APIs isolation
    risk_flood_resp = client.get("/api/v1/risk/flood?location=lucknow&mode=verified")
    assert risk_flood_resp.status_code in [400, 404]

    risk_drought_resp = client.get("/api/v1/risk/drought?location=patna&mode=verified")
    assert risk_drought_resp.status_code in [400, 404]

    # 3. Assistant isolation
    assist_resp = client.post("/api/v1/assistant/chat", json={
        "query": "Is there severe flooding in Lucknow right now?",
        "location": "lucknow"
    })
    assert assist_resp.status_code == 200
    assist_data = assist_resp.json()
    assert "DATA_PENDING" in assist_data["answer"]
    assert "Gorakhpur" not in assist_data["answer"]
    assert len(assist_data["evidence_used"]) == 0


# ---------------------------------------------------------------------------
# Data Provenance & Grounding Disclosures
# ---------------------------------------------------------------------------
def test_assistant_provenance_disclosure_accuracy():
    """Provenance disclosure must not falsely claim GPM IMERG is integrated into operational scoring."""
    payload = {
        "query": "What is the data provenance and live measurement status?",
        "location": "gorakhpur"
    }
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    answer = data["answer"]

    assert "DATA TRANSPARENCY & PROVENANCE DISCLOSURE" in answer
    # Must explicitly state GPM IMERG is not integrated into operational scoring
    assert "NASA GPM IMERG satellite feeds are currently not integrated" in answer
    assert "Candidate Districts" in answer
