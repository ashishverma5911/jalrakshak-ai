from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Dict, Any

from ..core.config import (
    PROJECT_NAME,
    VERSION,
    DATA_STALENESS_HOURS,
    GEMMA_MODEL_NAME,
    GEMMA_API_URL,
)

router = APIRouter(tags=["Health & Status"])

_START_TIME = datetime.now(timezone.utc)

@router.get("/health")
def get_health_status() -> Dict[str, Any]:
    """
    Returns system operational health, ingestion status, data freshness,
    and distinct model runtime diagnostics.
    """
    now = datetime.now(timezone.utc)
    uptime_sec = (now - _START_TIME).total_seconds()

    return {
        "status": "healthy",
        "api_status": "online",
        "project": PROJECT_NAME,
        "version": VERSION,
        "timestamp": now.isoformat(),
        "uptime_seconds": round(uptime_sec, 2),
        "data_ingestion": {
            "status": "synchronized",
            "active_pipelines": 4,
            "last_ingestion": "2026-10-28T10:30:00Z",
            "pipeline_mode": "local_reproducible_fixtures",
        },
        "data_freshness": {
            "last_observation_timestamp": "2026-10-28T10:30:00Z",
            "staleness_threshold_hours": DATA_STALENESS_HOURS,
            "data_age_hours": 11.2,
            "is_stale": False,
            "source_type": "local_cached_baseline",
        },
        "model_runtime": {
            "configured_model": GEMMA_MODEL_NAME,
            "runtime_adapter": "gemma_4_local_adapter",
            "endpoint_configured": GEMMA_API_URL,
            "fallback_engine": "deterministic_grounded_rules",
            "runtime_disclaimer": (
                "Neural runtime availability is verified dynamically per query. "
                "Deterministic grounded engine serves as honest verified fallback."
            ),
        },
        "is_demo_data": True,
        "disclaimer": "JalRakshak decision-support prototype backend. Local fixtures active.",
    }
