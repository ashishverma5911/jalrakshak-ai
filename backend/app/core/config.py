import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

PROJECT_NAME = "JalRakshak"
API_V1_PREFIX = "/api/v1"
VERSION = "1.0.0-prototype"

# Configurable CORS origins for development and deployment
_cors_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]

# Reverse Proxy & Trusted Proxy Configuration
# Defaults to strict socket client IP; zero blind trust of arbitrary X-Forwarded-For
TRUSTED_PROXIES = [
    ip.strip()
    for ip in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",")
    if ip.strip()
]
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("true", "1", "yes")

# Stale data threshold in hours
DATA_STALENESS_HOURS = float(os.getenv("DATA_STALENESS_HOURS", "24.0"))


# Scientific Data Source Credentials & Endpoints
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME", "")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD", "")
EARTHDATA_BEARER_TOKEN = os.getenv("EARTHDATA_BEARER_TOKEN", "")
OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY", "")
OPEN_METEO_ARCHIVE_URL = os.getenv("OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
OPEN_METEO_FORECAST_URL = os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
CHIRPS_BASE_URL = os.getenv("CHIRPS_BASE_URL", "https://data.chc.ucsb.edu/products/CHIRPS-2.0")

# Phase 3A: Live Environmental Data Ingestion Settings
# Default is False for strict backward compatibility until enabled
LIVE_DATA_ENABLED = os.getenv("LIVE_DATA_ENABLED", "false").lower() in ("true", "1", "yes")
LIVE_CACHE_TTL_HOURS = float(os.getenv("LIVE_CACHE_TTL_HOURS", "3.0"))
LIVE_STALE_THRESHOLD_HOURS = float(os.getenv("LIVE_STALE_THRESHOLD_HOURS", "24.0"))
LIVE_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LIVE_REQUEST_TIMEOUT_SECONDS", "10.0"))
LIVE_MAX_RETRIES = int(os.getenv("LIVE_MAX_RETRIES", "2"))

# API Ingestion & Upload Security
UPLOAD_API_KEY = os.getenv("UPLOAD_API_KEY", "").strip() or os.getenv("ADMIN_API_KEY", "").strip()
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(DATA_DIR / "uploads"))).resolve()


def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL connection strings to use the psycopg v3 dialect
    (postgresql+psycopg://) supported by SQLAlchemy 2.0 without requiring legacy psycopg2.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# Database Configuration (PostgreSQL / PostGIS with resilient local SQLite demo fallback)
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")

_env_db_url = os.getenv("DATABASE_URL", "").strip()
if _env_db_url:
    DATABASE_URL = normalize_database_url(_env_db_url)
elif DEMO_MODE:
    DATABASE_URL = f"sqlite:///{DATA_DIR}/jalrakshak_demo.db"
else:
    DATABASE_URL = "postgresql+psycopg://jalrakshak_user:jalrakshak_password@localhost:5432/jalrakshak"

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))

# Gemma 4 Hosted Model Settings (Google-Hosted Gemma 4 API)
# Architectural Decision: gemma-4-26b-a4b-it via Google AI Studio / Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMMA_MODEL_NAME = os.getenv("GEMMA_MODEL_NAME", "gemma-4-26b-a4b-it")
GEMMA_API_URL = os.getenv(
    "GEMMA_API_URL",
    "https://generativelanguage.googleapis.com/v1beta/models"
)
GEMMA_TIMEOUT_SECONDS = float(os.getenv("GEMMA_TIMEOUT_SECONDS", "5.0"))
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "1000"))

