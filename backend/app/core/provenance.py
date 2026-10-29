from typing import Dict, Any, List

DATA_SOURCES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "nasa_gpm_imerg": {
        "id": "nasa_gpm_imerg",
        "name": "NASA GPM IMERG Late Run",
        "full_name": "Integrated Multi-satellitE Retrievals for GPM (Global Precipitation Measurement)",
        "provider": "NASA Earth Science Data Systems / Goddard Space Flight Center",
        "status": "integrated_baseline",
        "spatial_resolution": "0.1° × 0.1° (~10 km at equator)",
        "temporal_resolution": "Half-hourly / Daily aggregated",
        "coverage": "Global (60°N to 60°S)",
        "historical_extent": "2000 – Present",
        "units": "mm/hour, aggregated to mm/day",
        "update_frequency": "12–14 hours latency for Late Run; 3.5 months for Final Run",
        "licensing": "NASA Open Data Policy (Free and open for research and commercial applications)",
        "access_url": "https://gpm.nasa.gov/data/imerg",
        "limitations": (
            "Passive microwave and infrared estimates calibrate well for large regional storms "
            "but may smooth localized convective cloudbursts. Ground validation requires rain gauge network."
        ),
    },
    "chirps_daily": {
        "id": "chirps_daily",
        "name": "CHIRPS Daily Station Blended",
        "full_name": "Climate Hazards Center InfraRed Precipitation with Station Data",
        "provider": "University of California, Santa Barbara (UCSB) / USGS",
        "status": "integrated_baseline",
        "spatial_resolution": "0.05° × 0.05° (~5 km resolution)",
        "temporal_resolution": "Daily gridded series",
        "coverage": "50°S to 50°N across all longitudes",
        "historical_extent": "1981 – Present (40+ year record)",
        "units": "mm/day",
        "update_frequency": "Preliminary runs within 5 days; final validated monthly",
        "licensing": "Creative Commons / Public Domain Open Data",
        "access_url": "https://www.chc.ucsb.edu/data/chirps",
        "limitations": (
            "Interpolation over sparse ground station areas can attenuate extreme peak events. "
            "Optimal for climatological anomaly detection and SPI reference distributions."
        ),
    },
    "srtm_dem": {
        "id": "srtm_dem",
        "name": "NASA SRTM 30m Digital Elevation Model",
        "full_name": "Shuttle Radar Topography Mission Global 1 Arc-Second DEM",
        "provider": "NASA Jet Propulsion Laboratory (JPL) / USGS",
        "status": "integrated_baseline",
        "spatial_resolution": "1 arc-second (~30 meters)",
        "temporal_resolution": "Static baseline topography",
        "coverage": "Global landmass between 60°N and 56°S",
        "historical_extent": "February 2000 mission data (version 3.0 filled voids)",
        "units": "Meters above WGS84 EGM96 Geoid (Mean Sea Level)",
        "update_frequency": "Static elevation benchmark",
        "licensing": "NASA Open Public Domain",
        "access_url": "https://earthexplorer.usgs.gov/",
        "limitations": (
            "Measures canopy or building tops in dense vegetation/urban areas (DSM characteristics). "
            "Does not account for human-built temporary earthen embankments or newly paved drainage."
        ),
    },
    "upsdma_imd": {
        "id": "upsdma_imd",
        "name": "UPSDMA & IMD Official Hazard Bulletins",
        "full_name": "Uttar Pradesh State Disaster Management Authority & India Meteorological Department",
        "provider": "Government of Uttar Pradesh / Ministry of Earth Sciences",
        "status": "authoritative_reference",
        "spatial_resolution": "District and tehsil administrative units",
        "temporal_resolution": "Daily / Hourly during monsoon emergency operations",
        "coverage": "Uttar Pradesh (all 75 districts)",
        "historical_extent": "Annual flood and disaster mock-exercise reports (e.g. 2024 Report)",
        "units": "Categorical alert stages (Green/Yellow/Orange/Red), danger-mark river gauge meters",
        "update_frequency": "Real-time during hazard incidents",
        "licensing": "Government Public Open Access",
        "access_url": "https://upsdma.up.nic.in/",
        "limitations": (
            "Primary authoritative source for official warnings and evacuation orders. "
            "JalRakshak is a decision-support prototype and does not issue or override official warnings."
        ),
    },
}

def get_all_sources() -> List[Dict[str, Any]]:
    return list(DATA_SOURCES_REGISTRY.values())

def get_source_by_id(source_id: str) -> Dict[str, Any]:
    return DATA_SOURCES_REGISTRY.get(source_id, {})
