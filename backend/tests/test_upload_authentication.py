"""
JalRakshak AI — Test Suite: Upload Authentication and Authorization Security (DEF-01)

Verifies:
1. Rejection of requests without credentials (401 Unauthorized) across all upload endpoints.
2. Rejection of requests with invalid credentials (401 Unauthorized).
3. Rejection of requests with malformed credentials (401 Unauthorized).
4. Safe behavior when server key is unconfigured (500 Configuration Error).
5. Unauthorized upload attempts NEVER modify stored datasets, spool files, or the registry.
6. Unauthorized cleanup attempts NEVER trigger deletion of quarantined files.
7. Authorized operations succeed via both 'X-API-Key' and 'Authorization: Bearer <token>'.
8. Constant-time comparison resilience via secrets.compare_digest.
"""

import io
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import verify_api_key, get_configured_upload_api_key
from app.core.rate_limiter import upload_limiter, cleanup_limiter
from app.services.upload_service import ScientificUploadService
from app.services.storage_service import LocalStorageBackend, StorageTier, StorageDurability

client = TestClient(app)

TEST_AUTH_KEY = "test-secret-key-jalrakshak-987654"


@pytest.fixture(autouse=True)
def setup_upload_test_env(tmp_path, monkeypatch):
    """
    Isolates registry and storage directories to tmp_path and configures test secret.
    """
    upload_limiter.reset()
    cleanup_limiter.reset()

    test_reg = tmp_path / "upload_registry.json"
    test_quarantine = tmp_path / "quarantine"
    test_verified = tmp_path / "verified"
    test_spool = tmp_path / "spool"

    test_quarantine.mkdir(parents=True, exist_ok=True)
    test_verified.mkdir(parents=True, exist_ok=True)
    test_spool.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.services.upload_service.REGISTRY_FILE", test_reg)
    monkeypatch.setattr("app.services.upload_service.QUARANTINE_DIR", test_quarantine)
    monkeypatch.setattr("app.services.upload_service.VERIFIED_DIR", test_verified)
    monkeypatch.setattr("app.services.upload_service.SPOOL_DIR", test_spool)
    monkeypatch.setattr("app.api.uploads.SPOOL_DIR", test_spool)

    # Set configured secret in environment
    monkeypatch.setenv("UPLOAD_API_KEY", TEST_AUTH_KEY)

    return {
        "reg": test_reg,
        "quarantine": test_quarantine,
        "verified": test_verified,
        "spool": test_spool,
    }


# =============================================================================
# 1. Unauthenticated Requests (Missing Credentials)
# =============================================================================

def test_upload_endpoint_requires_auth_when_missing():
    """Verify POST /api/v1/uploads/scientific-dataset rejects requests without credentials."""
    csv_bytes = b"date,rainfall_mm\n2024-08-10,12.5\n"
    files = {"file": ("unauth.csv", io.BytesIO(csv_bytes), "text/csv")}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files)
    assert response.status_code == 401
    assert "Missing API authentication credentials" in response.json()["detail"]
    assert "Bearer" in response.headers.get("www-authenticate", "")


def test_history_endpoint_requires_auth_when_missing():
    """Verify GET /api/v1/uploads/history rejects requests without credentials."""
    response = client.get("/api/v1/uploads/history")
    assert response.status_code == 401
    assert "Missing API authentication credentials" in response.json()["detail"]


def test_cleanup_endpoint_requires_auth_when_missing():
    """Verify POST /api/v1/uploads/cleanup rejects requests without credentials."""
    response = client.post("/api/v1/uploads/cleanup")
    assert response.status_code == 401
    assert "Missing API authentication credentials" in response.json()["detail"]


# =============================================================================
# 2. Invalid Credentials
# =============================================================================

def test_upload_endpoint_rejects_invalid_api_key():
    """Verify POST /api/v1/uploads/scientific-dataset rejects invalid X-API-Key."""
    csv_bytes = b"date,rainfall_mm\n2024-08-10,12.5\n"
    files = {"file": ("unauth.csv", io.BytesIO(csv_bytes), "text/csv")}
    headers = {"X-API-Key": "completely-wrong-key-value"}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API credentials."


def test_history_endpoint_rejects_invalid_bearer_token():
    """Verify GET /api/v1/uploads/history rejects invalid Bearer token."""
    headers = {"Authorization": "Bearer fake-token-xyz"}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API credentials."


def test_cleanup_endpoint_rejects_invalid_key():
    """Verify POST /api/v1/uploads/cleanup rejects invalid X-API-Key."""
    headers = {"X-API-Key": "invalid-cleanup-token"}
    response = client.post("/api/v1/uploads/cleanup", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API credentials."


# =============================================================================
# 3. Malformed Credentials
# =============================================================================

def test_rejects_malformed_authorization_basic():
    """Verify requests with Basic auth scheme instead of Bearer are rejected as malformed."""
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 401
    assert "Malformed Authorization header" in response.json()["detail"]


def test_rejects_malformed_authorization_bearer_empty():
    """Verify requests with empty Bearer token are rejected as malformed."""
    headers = {"Authorization": "Bearer "}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 401
    assert "Malformed Authorization header" in response.json()["detail"]


def test_rejects_malformed_empty_api_key():
    """Verify requests with empty X-API-Key are rejected as malformed."""
    headers = {"X-API-Key": "   "}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 401
    assert "Malformed X-API-Key header" in response.json()["detail"]


# =============================================================================
# 4. Server-Side Key Configuration Safeguards
# =============================================================================

def test_server_unconfigured_key_raises_configuration_error(monkeypatch):
    """Verify that if UPLOAD_API_KEY is not set on the server, requests return HTTP 500 error."""
    monkeypatch.setenv("UPLOAD_API_KEY", "")
    monkeypatch.setenv("ADMIN_API_KEY", "")
    monkeypatch.setattr("app.core.auth.UPLOAD_API_KEY", "")

    headers = {"X-API-Key": "some-key-provided-by-client"}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]


# =============================================================================
# 5. Data Integrity: Unauthorized Requests Cause Zero Side Effects
# =============================================================================

def test_unauthorized_upload_leaves_storage_and_registry_unmodified(setup_upload_test_env):
    """Verify that an unauthorized upload attempt creates NO files and modifies NO registry entries."""
    paths = setup_upload_test_env
    initial_registry = ScientificUploadService.load_registry()
    initial_count = len(initial_registry)

    csv_bytes = b"date,rainfall_mm\n2024-08-10,50.0\n"
    files = {"file": ("unauthorized_leak.csv", io.BytesIO(csv_bytes), "text/csv")}
    headers = {"X-API-Key": "bad-key"}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files, headers=headers)
    assert response.status_code == 401

    # Verify no spool file remains
    assert len(list(paths["spool"].glob("*"))) == 0
    # Verify no file written to quarantine
    assert len(list(paths["quarantine"].glob("*"))) == 0
    # Verify no file written to verified
    assert len(list(paths["verified"].glob("*"))) == 0
    # Verify registry was NOT modified
    after_registry = ScientificUploadService.load_registry()
    assert len(after_registry) == initial_count


def test_unauthorized_cleanup_does_not_purge_quarantine(setup_upload_test_env):
    """Verify that an unauthorized cleanup request does NOT purge expired quarantine files."""
    paths = setup_upload_test_env
    q_file = paths["quarantine"] / "expired_dataset.tmp"
    q_file.write_text("old_data")

    # Set file timestamp to 48 hours ago
    past_time = time.time() - (48 * 3600)
    import os
    os.utime(q_file, (past_time, past_time))

    assert q_file.exists()

    # Attempt unauthorized cleanup
    headers = {"X-API-Key": "bad-key"}
    response = client.post("/api/v1/uploads/cleanup", headers=headers)
    assert response.status_code == 401

    # Verify expired file is STILL intact
    assert q_file.exists()


# =============================================================================
# 6. Authorized Operations
# =============================================================================

def test_authorized_upload_via_api_key_header(setup_upload_test_env):
    """Verify POST /api/v1/uploads/scientific-dataset succeeds with valid X-API-Key."""
    csv_bytes = b"date,rainfall_mm\n2024-08-10,35.0\n2024-08-11,0.0\n"
    files = {"file": ("valid_auth_series.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {"target_region_id": "district-gorakhpur"}
    headers = {"X-API-Key": TEST_AUTH_KEY}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "VALIDATED"
    assert res_json["upload_id"].startswith("up_")


def test_authorized_upload_via_bearer_token(setup_upload_test_env):
    """Verify POST /api/v1/uploads/scientific-dataset succeeds with valid Authorization: Bearer token."""
    csv_bytes = b"date,rainfall_mm\n2024-08-12,20.0\n2024-08-13,15.0\n"
    files = {"file": ("bearer_auth_series.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {"target_region_id": "district-gorakhpur"}
    headers = {"Authorization": f"Bearer {TEST_AUTH_KEY}"}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files, data=data, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "VALIDATED"


def test_authorized_history_access(setup_upload_test_env):
    """Verify GET /api/v1/uploads/history returns registry items with valid Bearer token."""
    headers = {"Authorization": f"Bearer {TEST_AUTH_KEY}"}
    response = client.get("/api/v1/uploads/history", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_authorized_cleanup_purges_quarantine(setup_upload_test_env):
    """Verify POST /api/v1/uploads/cleanup purges expired files when authorized."""
    paths = setup_upload_test_env
    q_file = paths["quarantine"] / "expired_dataset.tmp"
    q_file.write_text("old_data")

    # Set timestamp to 48 hours ago
    past_time = time.time() - (48 * 3600)
    import os
    os.utime(q_file, (past_time, past_time))

    assert q_file.exists()

    headers = {"X-API-Key": TEST_AUTH_KEY}
    response = client.post("/api/v1/uploads/cleanup?max_age_hours=24.0", headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["deleted_files_count"] >= 1
    assert not q_file.exists()


# =============================================================================
# 7. Constant-Time Secret Verification Unit Tests
# =============================================================================

def test_verify_api_key_constant_time():
    """Verify unit-level behavior of verify_api_key."""
    assert verify_api_key("secret123", "secret123") is True
    assert verify_api_key("secret123", "wrong") is False
    assert verify_api_key("", "secret123") is False
    assert verify_api_key("secret123", "") is False
    assert verify_api_key("", "") is False


# =============================================================================
# 8. Rate Limiting Tests (Milestone 7 Remediation)
# =============================================================================

def test_cleanup_rate_limiting_enforced():
    """Verify POST /api/v1/uploads/cleanup triggers HTTP 429 when exceeding 3 requests per minute."""
    cleanup_limiter.reset()
    headers = {"X-API-Key": TEST_AUTH_KEY}

    # First 3 requests succeed
    for _ in range(3):
        res = client.post("/api/v1/uploads/cleanup", headers=headers)
        assert res.status_code == 200

    # 4th request must be rejected with 429 Too Many Requests
    res4 = client.post("/api/v1/uploads/cleanup", headers=headers)
    assert res4.status_code == 429
    assert "Rate limit exceeded" in res4.json()["detail"]
    assert "Retry-After" in res4.headers


def test_upload_rate_limiting_enforced():
    """Verify POST /api/v1/uploads/scientific-dataset triggers HTTP 429 when exceeding 10 requests per minute."""
    upload_limiter.reset()
    headers = {"X-API-Key": TEST_AUTH_KEY}
    csv_bytes = b"date,rainfall_mm\n2024-08-10,10.0\n"

    # Make 10 requests
    for i in range(10):
        files = {"file": (f"test_{i}.csv", io.BytesIO(csv_bytes), "text/csv")}
        res = client.post("/api/v1/uploads/scientific-dataset", files=files, headers=headers)
        assert res.status_code == 200

    # 11th request triggers 429
    files = {"file": ("test_overflow.csv", io.BytesIO(csv_bytes), "text/csv")}
    res11 = client.post("/api/v1/uploads/scientific-dataset", files=files, headers=headers)
    assert res11.status_code == 429
    assert "Rate limit exceeded" in res11.json()["detail"]


# =============================================================================
# 9. Storage Service Abstraction Tests (Milestone 7 Remediation)
# =============================================================================

def test_storage_service_abstraction_and_stats(tmp_path):
    """Verify LocalStorageBackend tier segregation and storage stats."""
    backend = LocalStorageBackend(root_dir=tmp_path / "custom_storage")
    stats = backend.get_storage_stats()
    assert stats["durability"] == StorageDurability.EPHEMERAL_LOCAL.value
    assert stats["total_storage_bytes"] == 0

    # Store payload in verified tier
    p = backend.store(StorageTier.VERIFIED_DATASET, "valid.csv", b"sample data")
    assert p.exists()
    assert backend.retrieve(StorageTier.VERIFIED_DATASET, "valid.csv") == b"sample data"

    updated_stats = backend.get_storage_stats()
    assert updated_stats["total_storage_bytes"] == len(b"sample data")
    assert updated_stats["tier_file_counts"]["verified"] == 1


def test_storage_service_path_traversal_blocked(tmp_path):
    """Verify LocalStorageBackend rejects path traversal escape attempts."""
    backend = LocalStorageBackend(root_dir=tmp_path / "custom_storage")
    with pytest.raises(ValueError, match="Path traversal detected"):
        backend.store(StorageTier.QUARANTINE, "../../evil.sh", b"malicious")
