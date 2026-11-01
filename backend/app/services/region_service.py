"""
Region Service Layer for JalRakshak AI
Provides clean database query execution with graceful fixture fallback.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..db.models import Region, HazardType, RegionHazard
from ..schemas.regions import (
    RegionSummary,
    RegionDetailResponse,
    HazardSummary,
    RegionHazardItem,
    RegionHazardsResponse,
)
from ..pipeline.ingestion import DataIngestionService

logger = logging.getLogger("jalrakshak.services.region")
_ingestion = DataIngestionService()


class RegionService:
    """
    Business logic and query layer for multi-region spatial hierarchy.
    """

    @classmethod
    def _map_hazard_summary(cls, rh: RegionHazard) -> HazardSummary:
        cfg = rh.configuration or {}
        code = rh.hazard_type.code if rh.hazard_type else rh.hazard_type_id
        name = rh.hazard_type.name if rh.hazard_type else rh.hazard_type_id.capitalize()
        status = cfg.get("status", "active" if rh.is_enabled else "not_configured")
        return HazardSummary(
            code=code,
            name=name,
            status=status,
            is_enabled=rh.is_enabled,
            configuration=cfg,
        )

    @classmethod
    def _map_region_to_summary(cls, r: Region) -> RegionSummary:
        hazards = [cls._map_hazard_summary(rh) for rh in (r.hazards or [])]
        return RegionSummary(
            id=r.id,
            code=r.code,
            name=r.name,
            region_type=r.region_type,
            parent_id=r.parent_id,
            country_code=r.country_code,
            state_code=r.state_code,
            is_active=r.is_active,
            supported_hazards=hazards,
            metadata=r.region_metadata or {},
        )

    @classmethod
    def _map_region_to_detail(cls, r: Region) -> RegionDetailResponse:
        hazards = [cls._map_hazard_summary(rh) for rh in (r.hazards or [])]
        return RegionDetailResponse(
            id=r.id,
            code=r.code,
            name=r.name,
            region_type=r.region_type,
            parent_id=r.parent_id,
            country_code=r.country_code,
            state_code=r.state_code,
            is_active=r.is_active,
            metadata=r.region_metadata or {},
            supported_hazards=hazards,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )

    @classmethod
    def list_regions(
        cls,
        db: Optional[Session] = None,
        region_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        state: Optional[str] = None,
        hazard_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[RegionSummary]:
        if db is not None:
            try:
                query = db.query(Region).options(
                    joinedload(Region.hazards).joinedload(RegionHazard.hazard_type)
                )

                if region_type:
                    query = query.filter(Region.region_type == region_type.lower())
                if parent_id:
                    query = query.filter(Region.parent_id == parent_id)
                if state:
                    query = query.filter(
                        (Region.state_code == state.upper()) |
                        (Region.code == f"IN-{state.upper()}") |
                        (Region.id == f"state-{state.lower()}")
                    )
                if is_active is not None:
                    query = query.filter(Region.is_active == is_active)

                records = query.all()

                # If hazard_type filter was requested
                if hazard_type:
                    hz_filter = hazard_type.lower()
                    filtered = []
                    for r in records:
                        if any(
                            (rh.hazard_type.code.lower() == hz_filter if rh.hazard_type else rh.hazard_type_id.lower() == hz_filter) and rh.is_enabled
                            for rh in r.hazards
                        ):
                            filtered.append(r)
                    records = filtered

                if records:
                    return [cls._map_region_to_summary(r) for r in records]
            except Exception as e:
                logger.warning(f"Database query error in list_regions: {e}; falling back to fixture")

        # Fallback to local verified metadata fixture
        return cls._fixture_list_regions(
            region_type=region_type,
            parent_id=parent_id,
            state=state,
            hazard_type=hazard_type,
            is_active=is_active,
        )

    @classmethod
    def get_region_by_identifier(
        cls,
        identifier: str,
        db: Optional[Session] = None,
    ) -> Optional[RegionDetailResponse]:
        clean_id = identifier.strip()
        if db is not None:
            try:
                # Support lookup by primary ID, code, or legacy_id stored in metadata
                r = db.query(Region).options(
                    joinedload(Region.hazards).joinedload(RegionHazard.hazard_type)
                ).filter(
                    (Region.id == clean_id) |
                    (func.lower(Region.code) == clean_id.lower()) |
                    (Region.id == f"district-{clean_id.lower()}") |
                    (Region.id == f"state-{clean_id.lower()}")
                ).first()

                if r:
                    return cls._map_region_to_detail(r)
            except Exception as e:
                logger.warning(f"Database query error in get_region_by_identifier: {e}; falling back to fixture")

        # Fallback lookup
        return cls._fixture_get_region(clean_id)

    @classmethod
    def get_region_hazards(
        cls,
        identifier: str,
        db: Optional[Session] = None,
    ) -> Optional[RegionHazardsResponse]:
        region_detail = cls.get_region_by_identifier(identifier, db=db)
        if not region_detail:
            return None

        if db is not None:
            try:
                hazards = db.query(RegionHazard).options(
                    joinedload(RegionHazard.hazard_type)
                ).filter(RegionHazard.region_id == region_detail.id).all()

                items = [
                    RegionHazardItem(
                        id=h.id,
                        region_id=h.region_id,
                        hazard_type_id=h.hazard_type_id,
                        hazard_code=h.hazard_type.code if h.hazard_type else h.hazard_type_id,
                        hazard_name=h.hazard_type.name if h.hazard_type else h.hazard_type_id.capitalize(),
                        is_enabled=h.is_enabled,
                        configuration=h.configuration or {},
                    )
                    for h in hazards
                ]
                return RegionHazardsResponse(
                    region_id=region_detail.id,
                    region_code=region_detail.code,
                    region_name=region_detail.name,
                    hazards=items,
                )
            except Exception as e:
                logger.warning(f"Database error in get_region_hazards: {e}; using fallback")

        # Fallback from detail response
        items = [
            RegionHazardItem(
                id=f"rh-{region_detail.id}-{hs.code}",
                region_id=region_detail.id,
                hazard_type_id=hs.code,
                hazard_code=hs.code,
                hazard_name=hs.name or hs.code.capitalize(),
                is_enabled=hs.is_enabled,
                configuration=hs.configuration or {"status": hs.status},
            )
            for hs in region_detail.supported_hazards
        ]
        return RegionHazardsResponse(
            region_id=region_detail.id,
            region_code=region_detail.code,
            region_name=region_detail.name,
            hazards=items,
        )

    @classmethod
    def get_child_regions(
        cls,
        identifier: str,
        db: Optional[Session] = None,
    ) -> Optional[List[RegionSummary]]:
        parent = cls.get_region_by_identifier(identifier, db=db)
        if not parent:
            return None

        if db is not None:
            try:
                children = db.query(Region).options(
                    joinedload(Region.hazards).joinedload(RegionHazard.hazard_type)
                ).filter(Region.parent_id == parent.id).all()

                if children:
                    return [cls._map_region_to_summary(c) for c in children]
            except Exception as e:
                logger.warning(f"Database error in get_child_regions: {e}; using fallback")

        # Fallback
        return cls._fixture_get_children(parent.id)

    # ==========================================
    # Resilient Fixture Fallback Implementations
    # ==========================================

    @classmethod
    def _fixture_list_regions(
        cls,
        region_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        state: Optional[str] = None,
        hazard_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[RegionSummary]:
        regions: List[RegionSummary] = []

        # India
        india = RegionSummary(
            id="country-india",
            code="IN",
            name="India",
            region_type="country",
            parent_id=None,
            country_code="IN",
            state_code=None,
            is_active=True,
            metadata={"capital": "New Delhi"},
        )
        # UP
        up = RegionSummary(
            id="state-uttar-pradesh",
            code="IN-UP",
            name="Uttar Pradesh",
            region_type="state",
            parent_id="country-india",
            country_code="IN",
            state_code="UP",
            is_active=True,
            metadata={"capital": "Lucknow"},
        )
        # Bihar
        bihar = RegionSummary(
            id="state-bihar",
            code="IN-BR",
            name="Bihar",
            region_type="state",
            parent_id="country-india",
            country_code="IN",
            state_code="BR",
            is_active=True,
            metadata={"capital": "Patna", "status": "prepared_for_onboarding"},
        )

        all_fixtures = [india, up, bihar]

        # Load districts from comprehensive hierarchy registry if available, else metadata
        hierarchy_path = Path(__file__).parent.parent / "db" / "seeds" / "data" / "districts_hierarchy.json"
        if hierarchy_path.exists():
            import json
            with open(hierarchy_path, "r", encoding="utf-8") as f:
                h_districts = json.load(f)

            for d in h_districts:
                did = d["id"]
                code = d["code"]
                lid = d.get("legacy_id", did.replace("district-", ""))
                is_p = d.get("is_pilot", False)
                p_hz = d.get("pilot_hazard")

                hazards = []
                if is_p and p_hz == "flood":
                    hazards.append(HazardSummary(
                        code="flood",
                        name="Flood Hazard Intelligence",
                        status="pilot",
                        is_enabled=True,
                        configuration={"status": "pilot", "sensitivity": "hyper_sensitive"},
                    ))
                    hazards.append(HazardSummary(
                        code="drought",
                        name="Meteorological Drought & Water Scarcity",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))
                elif is_p and p_hz == "drought":
                    hazards.append(HazardSummary(
                        code="drought",
                        name="Meteorological Drought & Water Scarcity",
                        status="pilot",
                        is_enabled=True,
                        configuration={"status": "pilot", "sensitivity": "severe"},
                    ))
                    hazards.append(HazardSummary(
                        code="flood",
                        name="Flood Hazard Intelligence",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))
                else:
                    hazards.append(HazardSummary(
                        code="flood",
                        name="Flood Hazard Intelligence",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))
                    hazards.append(HazardSummary(
                        code="drought",
                        name="Meteorological Drought & Water Scarcity",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))

                all_fixtures.append(RegionSummary(
                    id=did,
                    code=code,
                    name=d["name"],
                    region_type="district",
                    parent_id=d.get("state_id", "state-uttar-pradesh"),
                    country_code=d.get("country_code", "IN"),
                    state_code=d.get("state_code", "UP"),
                    is_active=True,
                    supported_hazards=hazards,
                    metadata={
                        "legacy_id": lid,
                        "hindi_name": d.get("hindi_name"),
                        "lat": d.get("lat"),
                        "lng": d.get("lng"),
                        "elevation_m": d.get("elevation_m"),
                        "river_basin": d.get("river_basin"),
                        "is_pilot": is_p,
                    },
                ))
        else:
            # Fallback to legacy metadata file
            districts = _ingestion.get_districts_metadata()
            for d in districts:
                lid = d["id"].lower()
                did = f"district-{lid}"
                code = f"IN-UP-{lid[:3].upper()}"

                hazards = []
                if lid == "gorakhpur":
                    hazards.append(HazardSummary(
                        code="flood",
                        name="Flood Hazard Intelligence",
                        status="pilot",
                        is_enabled=True,
                        configuration={"status": "pilot", "sensitivity": d.get("flood_sensitivity", "hyper_sensitive")},
                    ))
                elif lid == "mahoba":
                    hazards.append(HazardSummary(
                        code="drought",
                        name="Meteorological Drought & Water Scarcity",
                        status="pilot",
                        is_enabled=True,
                        configuration={"status": "pilot", "sensitivity": d.get("drought_sensitivity", "severe")},
                    ))
                else:
                    hazards.append(HazardSummary(
                        code="flood",
                        name="Flood Hazard Intelligence",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))
                    hazards.append(HazardSummary(
                        code="drought",
                        name="Meteorological Drought & Water Scarcity",
                        status="not_configured",
                        is_enabled=False,
                        configuration={"status": "not_configured"},
                    ))

                all_fixtures.append(RegionSummary(
                    id=did,
                    code=code,
                    name=d["name"],
                    region_type="district",
                    parent_id="state-uttar-pradesh",
                    country_code="IN",
                    state_code="UP",
                    is_active=True,
                    supported_hazards=hazards,
                    metadata={
                        "legacy_id": lid,
                        "hindi_name": d.get("hindi_name"),
                        "lat": d.get("lat"),
                        "lng": d.get("lng"),
                        "elevation_m": d.get("elevation_m"),
                        "river_basin": d.get("river_basin"),
                        "region": d.get("region"),
                        "is_pilot": d.get("is_pilot", False),
                    },
                ))

        # Filter
        res = all_fixtures
        if region_type:
            res = [r for r in res if r.region_type == region_type.lower()]
        if parent_id:
            res = [r for r in res if r.parent_id == parent_id]
        if state:
            s_up = state.upper()
            res = [r for r in res if r.state_code == s_up or r.code == f"IN-{s_up}" or r.id == f"state-{state.lower()}"]
        if is_active is not None:
            res = [r for r in res if r.is_active == is_active]
        if hazard_type:
            hz_clean = hazard_type.lower()
            res = [r for r in res if any(h.code == hz_clean and h.is_enabled for h in r.supported_hazards)]

        return res

    @classmethod
    def _fixture_get_region(cls, identifier: str) -> Optional[RegionDetailResponse]:
        all_r = cls._fixture_list_regions()
        clean = identifier.lower()
        for r in all_r:
            if (
                r.id.lower() == clean or
                r.code.lower() == clean or
                r.id.lower() == f"district-{clean}" or
                r.id.lower() == f"state-{clean}" or
                (r.metadata and r.metadata.get("legacy_id") == clean)
            ):
                return RegionDetailResponse(
                    id=r.id,
                    code=r.code,
                    name=r.name,
                    region_type=r.region_type,
                    parent_id=r.parent_id,
                    country_code=r.country_code,
                    state_code=r.state_code,
                    is_active=r.is_active,
                    metadata=r.metadata or {},
                    supported_hazards=r.supported_hazards,
                )
        return None

    @classmethod
    def _fixture_get_children(cls, parent_id: str) -> List[RegionSummary]:
        all_r = cls._fixture_list_regions()
        return [r for r in all_r if r.parent_id == parent_id]
