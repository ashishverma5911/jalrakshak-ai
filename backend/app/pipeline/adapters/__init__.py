"""
Scientific Source Adapters Package for JalRakshak AI
"""

from .base import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterResponse,
    ObservationRecord,
    SourceConnectionStatus,
    DatasetType,
    QualityStatus,
    PrecipitationUnit,
    AdapterError,
    AdapterConnectionError,
    AdapterAuthenticationError,
    AdapterPayloadError,
    AdapterUnitError,
    DistrictIsolationError,
)
from .chirps import CHIRPSAdapter
from .gpm_imerg import GPMIMERGAdapter
from .open_meteo import OpenMeteoAdapter
from .open_meteo_forecast import OpenMeteoForecastAdapter
from .srtm import SRTMAdapter
from .registry import ScientificSourceRegistry

__all__ = [
    "ScientificSourceAdapter",
    "AdapterMetadata",
    "AdapterResponse",
    "ObservationRecord",
    "SourceConnectionStatus",
    "DatasetType",
    "QualityStatus",
    "PrecipitationUnit",
    "AdapterError",
    "AdapterConnectionError",
    "AdapterAuthenticationError",
    "AdapterPayloadError",
    "AdapterUnitError",
    "DistrictIsolationError",
    "CHIRPSAdapter",
    "GPMIMERGAdapter",
    "OpenMeteoAdapter",
    "OpenMeteoForecastAdapter",
    "SRTMAdapter",
    "ScientificSourceRegistry",
]
