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
CHIRPS_BASE_URL = os.getenv("CHIRPS_BASE_URL", "https://data.chc.ucsb.edu/products/CHIRPS-2.0")

# API Ingestion & Upload Security
UPLOAD_API_KEY = os.getenv("UPLOAD_API_KEY", "").strip() or os.getenv("ADMIN_API_KEY", "").strip()

# Database Configuration (PostgreSQL / PostGIS with resilient local dev fallback)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://jalrakshak_user:jalrakshak_password@localhost:5432/jalrakshak"
)
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

