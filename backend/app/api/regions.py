"""
FastAPI Endpoints for Multi-Region Foundation
Routes:
- GET /api/v1/regions
- GET /api/v1/regions/{region_id}
- GET /api/v1/regions/{region_id}/hazards
- GET /api/v1/regions/{region_id}/children
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.session import get_db, is_db_connected
from ..services.region_service import RegionService
from ..schemas.regions import (
    RegionSummary,
    RegionDetailResponse,
    RegionHazardsResponse,
)

logger = logging.getLogger("jalrakshak.api.regions")
router = APIRouter(prefix="/regions", tags=["Regions"])


def get_optional_db():
    """
    Safely retrieves a database session if connected, or None if the database is offline.
    This guarantees zero downtime during maintenance or migration windows.
    """
    if not is_db_connected():
        yield None
        return

    for db in get_db():
        yield db


@router.get("", response_model=List[RegionSummary])
def list_regions(
    region_type: Optional[str] = Query(None, description="Filter by type: country, state, district, subdistrict"),
    parent_id: Optional[str] = Query(None, description="Filter by parent region identifier"),
    state: Optional[str] = Query(None, description="Filter by state code (e.g. UP, BR)"),
    hazard_type: Optional[str] = Query(None, description="Filter by supported hazard code (e.g. flood, drought)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Optional[Session] = Depends(get_optional_db),
) -> List[RegionSummary]:
    """
    Returns geographical regions filtered by administrative level, parent, state, or hazard type.
    """
    return RegionService.list_regions(
        db=db,
        region_type=region_type,
        parent_id=parent_id,
        state=state,
        hazard_type=hazard_type,
        is_active=is_active,
    )


@router.get("/{region_id}", response_model=RegionDetailResponse)
def get_region(
    region_id: str,
    db: Optional[Session] = Depends(get_optional_db),
) -> RegionDetailResponse:
    """
    Retrieves full details, metadata, and supported hazards for a specific region ID or code.
    """
    region = RegionService.get_region_by_identifier(region_id, db=db)
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{region_id}' not found in the geographical registry.",
        )
    return region


@router.get("/{region_id}/hazards", response_model=RegionHazardsResponse)
def get_region_hazards(
    region_id: str,
    db: Optional[Session] = Depends(get_optional_db),
) -> RegionHazardsResponse:
    """
    Retrieves configured hazard models and operational statuses for a given region.
    """
    hazards = RegionService.get_region_hazards(region_id, db=db)
    if not hazards:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{region_id}' not found.",
        )
    return hazards


@router.get("/{region_id}/children", response_model=List[RegionSummary])
def get_region_children(
    region_id: str,
    db: Optional[Session] = Depends(get_optional_db),
) -> List[RegionSummary]:
    """
    Retrieves all direct child regions (e.g. districts belonging to a state, or subdistricts of a district).
    """
    children = RegionService.get_child_regions(region_id, db=db)
    if children is None:
        raise HTTPException(
            status_code=404,
            detail=f"Parent region '{region_id}' not found.",
        )
    return children
