"""
Idempotent Seeding Service for JalRakshak AI Multi-Region Hierarchy
Registers:
- Initial Hazard Types: Flood, Drought
- Country: India
- States: Uttar Pradesh (Active), Bihar (Supported / Prepared)
- Districts: All 9 districts from districts_metadata.json (Gorakhpur and Mahoba as pilots, 7 unconfigured)
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ...core.config import DATA_DIR
from ..models import Region, HazardType, RegionHazard, RegionBoundary

logger = logging.getLogger("jalrakshak.seed")


def seed_database(db: Session, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Executes idempotent seeding of regions, hazard types, and hazard bindings.
    Safe to execute multiple times without duplicating or corrupting data.
    """
    base_data_dir = data_dir or DATA_DIR
    stats = {
        "hazard_types_seeded": 0,
        "regions_seeded": 0,
        "region_hazards_seeded": 0,
        "boundaries_seeded": 0,
    }

    # ==========================================
    # 1. Seed Core Hazard Types
    # ==========================================
    core_hazards = [
        {
            "id": "flood",
            "code": "flood",
            "name": "Flood Hazard Intelligence",
            "description": "Monsoon heavy rainfall accumulation, catchment water loading, and alluvial drainage vulnerability assessment.",
            "is_active": True,
        },
        {
            "id": "drought",
            "code": "drought",
            "name": "Meteorological Drought & Water Scarcity",
            "description": "Standardized Precipitation Index (SPI-3), Kharif seasonal deficit, and consecutive dry-spell persistence.",
            "is_active": True,
        },
    ]

    for hz in core_hazards:
        existing = db.query(HazardType).filter(
            (HazardType.id == hz["id"]) | (HazardType.code == hz["code"])
        ).first()
        if not existing:
            new_hz = HazardType(
                id=hz["id"],
                code=hz["code"],
                name=hz["name"],
                description=hz["description"],
                is_active=hz["is_active"],
            )
            db.add(new_hz)
            stats["hazard_types_seeded"] += 1
        else:
            existing.name = hz["name"]
            existing.description = hz["description"]
            existing.is_active = hz["is_active"]
    db.flush()

    # ==========================================
    # 2. Seed Country: India
    # ==========================================
    india_id = "country-india"
    india = db.query(Region).filter((Region.id == india_id) | (Region.code == "IN")).first()
    if not india:
        india = Region(
            id=india_id,
            code="IN",
            name="India",
            region_type="country",
            parent_id=None,
            country_code="IN",
            state_code=None,
            is_active=True,
            region_metadata={
                "capital": "New Delhi",
                "iso_alpha2": "IN",
                "iso_alpha3": "IND",
                "description": "Republic of India",
            },
        )
        db.add(india)
        stats["regions_seeded"] += 1
    db.flush()

    # ==========================================
    # 3. Seed States: Uttar Pradesh & Bihar
    # ==========================================
    states = [
        {
            "id": "state-uttar-pradesh",
            "code": "IN-UP",
            "name": "Uttar Pradesh",
            "country_code": "IN",
            "state_code": "UP",
            "is_active": True,
            "metadata": {
                "capital": "Lucknow",
                "region": "Northern India",
                "status": "active_pilot_state",
            },
        },
        {
            "id": "state-bihar",
            "code": "IN-BR",
            "name": "Bihar",
            "country_code": "IN",
            "state_code": "BR",
            "is_active": True,
            "metadata": {
                "capital": "Patna",
                "region": "Eastern India",
                "status": "prepared_for_onboarding",
                "note": "Supported state prepared in database schema without fabricated datasets",
            },
        },
    ]

    for st in states:
        existing_st = db.query(Region).filter(
            (Region.id == st["id"]) | (Region.code == st["code"])
        ).first()
        if not existing_st:
            new_st = Region(
                id=st["id"],
                code=st["code"],
                name=st["name"],
                region_type="state",
                parent_id=india_id,
                country_code=st["country_code"],
                state_code=st["state_code"],
                is_active=st["is_active"],
                region_metadata=st["metadata"],
            )
            db.add(new_st)
            stats["regions_seeded"] += 1
    db.flush()

    # ==========================================
    # 4. Seed Districts (75 UP + 38 Bihar from districts_hierarchy.json)
    # ==========================================
    hierarchy_path = Path(__file__).parent / "data" / "districts_hierarchy.json"
    districts_data = []

    if hierarchy_path.exists():
        with open(hierarchy_path, "r", encoding="utf-8") as f:
            districts_data = json.load(f)
    else:
        meta_path = base_data_dir / "districts_metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                districts_data = json.load(f)
        else:
            logger.warning(f"Neither districts_hierarchy.json nor districts_metadata.json found; skipping district seed")
            db.commit()
            return stats

    for d in districts_data:
        legacy_id = d.get("legacy_id", d.get("id", "")).lower()
        if legacy_id.startswith("district-"):
            legacy_id = legacy_id[len("district-"):]
        district_id = d.get("id") if d.get("id", "").startswith("district-") else f"district-{legacy_id}"
        code = d.get("code") or f"IN-UP-{legacy_id[:3].upper()}"
        parent_id = d.get("state_id", "state-uttar-pradesh")
        state_code = d.get("state_code", "UP")
        country_code = d.get("country_code", "IN")
        is_pilot = d.get("is_pilot", False)
        pilot_hazard = d.get("pilot_hazard")

        meta_payload = {
            "legacy_id": legacy_id,
            "hindi_name": d.get("hindi_name"),
            "lat": d.get("lat"),
            "lng": d.get("lng"),
            "elevation_m": d.get("elevation_m"),
            "river_basin": d.get("river_basin"),
            "region": d.get("region", "Northern India"),
            "is_pilot": is_pilot,
        }
        if "flood_sensitivity" in d:
            meta_payload["flood_sensitivity"] = d["flood_sensitivity"]
        if "drought_sensitivity" in d:
            meta_payload["drought_sensitivity"] = d["drought_sensitivity"]

        district_record = db.query(Region).filter(
            (Region.id == district_id) | (Region.code == code)
        ).first()

        if not district_record:
            district_record = Region(
                id=district_id,
                code=code,
                name=d["name"],
                region_type="district",
                parent_id=parent_id,
                country_code=country_code,
                state_code=state_code,
                is_active=True,
                region_metadata=meta_payload,
            )
            db.add(district_record)
            stats["regions_seeded"] += 1
        else:
            # Preserve existing ID, update metadata non-destructively
            existing_meta = dict(district_record.region_metadata or {})
            existing_meta.update(meta_payload)
            district_record.region_metadata = existing_meta
            district_record.name = d["name"]
            district_record.parent_id = parent_id
            district_record.state_code = state_code
        db.flush()

        # ==========================================
        # 5. Configure Hazard Associations
        # ==========================================
        # Gorakhpur: Flood pilot
        # Mahoba: Drought pilot
        # All others: Not configured
        hazard_configs = []

        if legacy_id == "gorakhpur" or (is_pilot and pilot_hazard == "flood"):
            hazard_configs.append({
                "hazard_type_id": "flood",
                "is_enabled": True,
                "config": {
                    "status": "pilot",
                    "is_pilot": True,
                    "sensitivity": d.get("flood_sensitivity", "hyper_sensitive"),
                    "basin": d.get("river_basin"),
                    "active_model": "rainfall_accumulation_v1",
                },
            })
            hazard_configs.append({
                "hazard_type_id": "drought",
                "is_enabled": False,
                "config": {
                    "status": "not_configured",
                    "reason": "Flood pilot focus location",
                },
            })
        elif legacy_id == "mahoba" or (is_pilot and pilot_hazard == "drought"):
            hazard_configs.append({
                "hazard_type_id": "drought",
                "is_enabled": True,
                "config": {
                    "status": "pilot",
                    "is_pilot": True,
                    "sensitivity": d.get("drought_sensitivity", "severe"),
                    "basin": d.get("river_basin"),
                    "active_model": "spi_3_gamma_v1",
                },
            })
            hazard_configs.append({
                "hazard_type_id": "flood",
                "is_enabled": False,
                "config": {
                    "status": "not_configured",
                    "reason": "Drought pilot focus location",
                },
            })
        else:
            hazard_configs.append({
                "hazard_type_id": "flood",
                "is_enabled": False,
                "config": {
                    "status": "not_configured",
                    "sensitivity": d.get("flood_sensitivity", "moderate"),
                },
            })
            hazard_configs.append({
                "hazard_type_id": "drought",
                "is_enabled": False,
                "config": {
                    "status": "not_configured",
                    "sensitivity": d.get("drought_sensitivity", "low"),
                },
            })

        for hc in hazard_configs:
            link_id = f"rh-{district_record.id}-{hc['hazard_type_id']}"
            existing_link = db.query(RegionHazard).filter(
                (RegionHazard.region_id == district_record.id) &
                (RegionHazard.hazard_type_id == hc["hazard_type_id"])
            ).first()

            if not existing_link:
                new_link = RegionHazard(
                    id=link_id,
                    region_id=district_record.id,
                    hazard_type_id=hc["hazard_type_id"],
                    is_enabled=hc["is_enabled"],
                    configuration=hc["config"],
                )
                db.add(new_link)
                stats["region_hazards_seeded"] += 1
            else:
                existing_link.is_enabled = hc["is_enabled"]
                existing_link.configuration = hc["config"]

        # ==========================================
        # 6. Seed Point Geometry Fallback
        # ==========================================
        if d.get("lat") and d.get("lng"):
            b_id = f"boundary-{district_record.id}"
            existing_b = db.query(RegionBoundary).filter(
                RegionBoundary.region_id == district_record.id
            ).first()
            wkt_centroid = f"POINT({d['lng']} {d['lat']})"
            boundary_source = d.get("boundary_source", "survey_of_india_centroid")
            boundary_version = d.get("boundary_version", "1.0")

            if not existing_b:
                new_b = RegionBoundary(
                    id=b_id,
                    region_id=district_record.id,
                    geometry=wkt_centroid,
                    boundary_source=boundary_source,
                    boundary_version=boundary_version,
                )
                db.add(new_b)
                stats["boundaries_seeded"] += 1

    db.commit()
    logger.info(f"Database seeded successfully: {stats}")
    return stats
