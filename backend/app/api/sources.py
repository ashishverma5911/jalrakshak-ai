from fastapi import APIRouter
from typing import List, Dict, Any

from ..core.provenance import get_all_sources, get_source_by_id

router = APIRouter(tags=["Data Sources & Transparency"])

@router.get("/sources")
def list_data_sources() -> List[Dict[str, Any]]:
    """
    Returns full metadata for all investigated and integrated environmental datasets.
    """
    return get_all_sources()

@router.get("/sources/{source_id}")
def get_source_detail(source_id: str) -> Dict[str, Any]:
    source = get_source_by_id(source_id)
    if not source:
        return {"error": f"Source '{source_id}' not found in registry"}
    return source
