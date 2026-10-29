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

# Stale data threshold in hours
DATA_STALENESS_HOURS = float(os.getenv("DATA_STALENESS_HOURS", "24.0"))

# Gemma 4 Runtime Adapter Settings
GEMMA_API_URL = os.getenv("GEMMA_API_URL", "http://localhost:11434/api/generate")
GEMMA_MODEL_NAME = os.getenv("GEMMA_MODEL_NAME", "gemma:4")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "")
GEMMA_TIMEOUT_SECONDS = float(os.getenv("GEMMA_TIMEOUT_SECONDS", "3.0"))
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "1000"))

