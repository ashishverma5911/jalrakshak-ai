"""
Scientific Source Adapter Base Architecture for JalRakshak AI
Provides abstract interfaces, typed data contracts, validation primitives,
and unit-integrity enforcement for multi-source environmental datasets.

Scientific Invariants:
1. Distinguishes rainfall rate (mm/hr) from rainfall accumulation (mm).
2. Never silently substitutes missing/null observations as zero.
3. Preserves source-specific timestamps, units, and spatial resolution.
4. Enforces strict geographic bounds and zero cross-district data substitution.
5. Classifies datasets explicitly: OBSERVED, SATELLITE_DERIVED, MODELLED_REANALYSIS, FORECAST, STATIC_REFERENCE.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field


class SourceConnectionStatus(str, Enum):
    CONNECTED = "connected"
    AUTHENTICATION_REQUIRED = "authentication_required"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    STATIC_REFERENCE = "static_reference"
    ERROR = "error"


class DatasetType(str, Enum):
    OBSERVED = "observed"                      # Direct in-situ meteorological ground stations
    SATELLITE_DERIVED = "satellite_derived"    # Satellite radar/microwave/IR retrieval with or without ground blending
    MODELLED_REANALYSIS = "modelled_reanalysis"# Numerical weather prediction model reanalysis (e.g., ERA5)
    FORECAST = "forecast"                      # Numerical weather prediction forecasts (e.g., GFS, ECMWF)
    STATIC_REFERENCE = "static_reference"      # Fixed terrain or boundary reference (e.g., SRTM DEM)


class QualityStatus(str, Enum):
    OBSERVED = "observed"                      # Valid measured/retrieved precipitation > 0 and <= 500 mm
    ZERO_PRECIPITATION = "zero_precipitation"  # Legitimate zero rainfall (0.0 mm), distinct from missing
    PROVISIONAL_EXTREME = "provisional_extreme"# > 500 mm/day, flagged for mandatory scientific review
    MISSING = "missing"                        # No observation available on this timestamp
    UNVERIFIED = "unverified"                  # Unprocessed or unvalidated observation


class PrecipitationUnit(str, Enum):
    MM = "mm"                                  # Total precipitation accumulation (millimeters)
    MM_DAY = "mm/day"                          # Daily accumulation rate (millimeters per day)
    MM_HR = "mm/hr"                            # Instantaneous or hourly precipitation rate (millimeters per hour)
    METERS = "meters"                          # Surface elevation above WGS84 EGM96 Geoid


class AdapterError(Exception):
    """Base exception for scientific source adapters."""
    pass


class AdapterConnectionError(AdapterError):
    """Raised when remote connection to scientific data source fails or times out."""
    pass


class AdapterAuthenticationError(AdapterError):
    """Raised when authentication credentials are required or rejected."""
    pass


class AdapterPayloadError(AdapterError):
    """Raised when payload structure, schema, or bounds fail validation."""
    pass


class AdapterUnitError(AdapterError):
    """Raised when invalid or unconvertible units are encountered."""
    pass


class DistrictIsolationError(AdapterError):
    """Raised when cross-district data leakage or substitution is attempted."""
    pass


class ObservationRecord(BaseModel):
    """Represents a single verified or retrieved observation."""
    date: date
    rainfall_mm: Optional[float] = Field(
        None,
        description="Accumulation in millimeters. Strictly None for missing dates. Never coerced to 0.0."
    )
    raw_value: Optional[float] = Field(None, description="Raw measurement before unit conversion.")
    raw_units: str = Field("mm", description="Units of raw value as retrieved from source.")
    temporal_semantics: str = Field("daily_accumulation", description="Temporal interval semantics: daily_accumulation, interval_accumulation, or converted_from_rate.")
    interval_hours: Optional[float] = Field(24.0, description="Duration in hours represented by this observation (e.g., 24.0 for daily, 0.5 for half-hourly).")
    quality_status: QualityStatus = Field(QualityStatus.OBSERVED)
    review_flag: Optional[str] = Field(None, description="Scientific review flag if extreme or anomalous.")


class AdapterMetadata(BaseModel):
    """Formal metadata specification for a scientific data provider."""
    source_id: str
    name: str
    provider: str
    product_version: str
    dataset_type: DatasetType
    spatial_resolution: str
    temporal_resolution: str
    default_units: str
    is_rate_based: bool = False
    historical_coverage: str
    latency: str
    auth_required: bool
    access_method: str
    citations: List[str] = Field(default_factory=list)
    limitations: str


class AdapterResponse(BaseModel):
    """Structured response container for adapter operations."""
    source_id: str
    region_id: str
    status: SourceConnectionStatus
    dataset_type: DatasetType
    product_version: str
    units: str
    temporal_semantics: str = Field("daily_accumulated_depth", description="Semantics of returned values.")
    is_rate_based: bool = Field(False, description="Whether returned units represent a rate or accumulated depth.")
    observations: List[ObservationRecord] = Field(default_factory=list)
    records_count: int = 0
    valid_count: int = 0
    missing_count: int = 0
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    date_range: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ScientificSourceAdapter(ABC):
    """
    Abstract Base Class for all JalRakshak scientific source adapters.
    Guarantees standard lifecycle: metadata query, connection verification,
    data retrieval, unit safety, and payload validation.
    """

    @classmethod
    @abstractmethod
    def get_metadata(cls) -> AdapterMetadata:
        """Returns the formal metadata definition for this source."""
        pass

    @classmethod
    @abstractmethod
    async def check_connection(cls) -> Dict[str, Any]:
        """
        Verifies endpoint reachability, credentials, and service health.
        Must return a structured status dict with at least 'status' and 'timestamp'.
        """
        pass

    @classmethod
    @abstractmethod
    async def fetch_series(
        cls,
        region_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> AdapterResponse:
        """
        Retrieves, validates, and normalizes time-series observations for a district.
        Must strictly enforce district isolation and physical bounds.
        """
        pass

    @classmethod
    @abstractmethod
    def validate_payload(cls, raw_payload: Any) -> Dict[str, Any]:
        """
        Validates raw response structure, columns, data types, and bounds.
        Raises AdapterPayloadError on schema violation.
        """
        pass

    # =========================================================================
    # Shared Scientific Primitives & Unit Conversion Utilities
    # =========================================================================

    @staticmethod
    def normalize_region_id(region_id: str) -> str:
        """Standardizes region IDs to lowercase slug (e.g., 'gorakhpur' or 'district-gorakhpur')."""
        if not region_id or not isinstance(region_id, str):
            raise AdapterPayloadError("Invalid or empty region_id provided.")
        clean = region_id.lower().strip()
        if not clean.startswith("district-"):
            clean = f"district-{clean}"
        return clean

    @staticmethod
    def convert_rate_to_accumulation(rate_mm_hr: float, duration_hours: float) -> float:
        """
        Converts precipitation rate (mm/hr) to accumulated depth (mm) over an exact duration.
        Formula: Accumulation (mm) = Rate (mm/hr) * Duration (hours).
        
        Strict Scientific Rules:
        - duration_hours is mandatory. Guessing an unstated temporal interval is strictly prohibited.
        - duration_hours must be strictly positive (> 0.0).
        - rate_mm_hr cannot be negative (< 0.0).
        - NEVER multiply a half-hourly rate (0.5 hr) by 24 hours.
        """
        if duration_hours is None or not isinstance(duration_hours, (int, float)):
            raise AdapterUnitError("Explicit positive duration_hours is required to convert precipitation rate to accumulation.")
        if duration_hours <= 0.0:
            raise AdapterUnitError(f"Integration duration must be strictly positive, got {duration_hours} hours.")
        if rate_mm_hr is None or not isinstance(rate_mm_hr, (int, float)):
            raise AdapterUnitError(f"Invalid non-numeric precipitation rate: {rate_mm_hr}")
        if rate_mm_hr < 0.0:
            raise AdapterUnitError(f"Physically impossible negative precipitation rate: {rate_mm_hr} mm/hr.")
        
        accumulation = rate_mm_hr * duration_hours
        return round(accumulation, 3)

    @classmethod
    def convert_half_hourly_rate_to_accumulation(cls, rate_mm_hr: float) -> float:
        """
        Converts a 30-minute interval-mean precipitation rate (mm/hr) to 30-minute accumulated depth (mm).
        Duration is strictly 0.5 hours.
        Example: 2.0 mm/hr over 30 minutes = 1.0 mm.
        """
        return cls.convert_rate_to_accumulation(rate_mm_hr, duration_hours=0.5)

    @classmethod
    def convert_daily_mean_rate_to_accumulation(cls, rate_mm_hr: float) -> float:
        """
        Converts a genuine 24-hour daily mean precipitation rate (mm/hr) to daily accumulated depth (mm).
        Valid ONLY when the source rate genuinely represents the entire 24-hour observation day.
        Example: 2.0 mm/hr over 24 hours = 48.0 mm.
        """
        return cls.convert_rate_to_accumulation(rate_mm_hr, duration_hours=24.0)

    @classmethod
    def accumulate_half_hourly_series(cls, half_hourly_rates: List[Optional[float]]) -> Optional[float]:
        """
        Integrates a series of half-hourly precipitation rates into a total accumulated depth.
        Total (mm) = sum(rate_i * 0.5) for all valid intervals.
        Returns None if all values are None/missing.
        """
        if not half_hourly_rates:
            return None
        valid_rates = [r for r in half_hourly_rates if r is not None]
        if not valid_rates:
            return None
        total = sum(cls.convert_half_hourly_rate_to_accumulation(r) for r in valid_rates)
        return round(total, 3)

    @staticmethod
    def validate_rainfall_value(val: Any) -> Tuple[Optional[float], QualityStatus, Optional[str]]:
        """
        Enforces physical bounds on daily rainfall accumulation:
        - None / NaN -> (None, QualityStatus.MISSING, None)
        - < 0.0 -> raises AdapterPayloadError (physically impossible)
        - == 0.0 -> (0.0, QualityStatus.ZERO_PRECIPITATION, None)
        - > 500.0 -> (val, QualityStatus.PROVISIONAL_EXTREME, 'Provisional extreme > 500 mm/day requires scientific review')
        - 0.0 < val <= 500.0 -> (val, QualityStatus.OBSERVED, None)
        """
        if val is None:
            return None, QualityStatus.MISSING, None

        import math
        try:
            fval = float(val)
        except (ValueError, TypeError):
            raise AdapterPayloadError(f"Invalid non-numeric rainfall measurement: '{val}'")

        if math.isnan(fval):
            return None, QualityStatus.MISSING, None

        if fval < 0.0:
            raise AdapterPayloadError(f"Negative rainfall observation {fval} mm is physically invalid and rejected.")

        if fval == 0.0:
            return 0.0, QualityStatus.ZERO_PRECIPITATION, None

        rounded = round(fval, 2)
        if rounded > 500.0:
            return (
                rounded,
                QualityStatus.PROVISIONAL_EXTREME,
                f"Provisional extreme measurement ({rounded} mm/day) exceeds 500 mm threshold. Requires scientific review."
            )

        return rounded, QualityStatus.OBSERVED, None
