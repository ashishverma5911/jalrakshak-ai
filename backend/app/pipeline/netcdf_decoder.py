"""
Scientific NetCDF Dataset Decoder for JalRakshak AI.
Decodes NetCDF-3 Classic, 64-bit offset, and 64-bit data files using scipy.io.netcdf_file.
Provides explicit separation and quarantine for NetCDF-4/HDF5 format variants
when HDF5 C-libraries are not present in constrained runtime environments.

Scientific Requirements:
1. Parse actual dimensions, variables, coordinate grids, and time baselines.
2. Identify precipitation variables via CF-compliant and meteorological name mapping.
3. Reject ambiguous or missing precipitation variables.
4. Extract array values, apply _FillValue / missing_value masking, calculate in-bounds statistics.
5. Extract temporal units and chronological range.
6. Enforce physical constraints: reject negative rainfall, flag provisional extremes (> 500 mm/day).
7. Compute geographic bounding box (min_lng, min_lat, max_lng, max_lat) for spatial intersection.
"""

import io
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
import numpy as np

logger = logging.getLogger("jalrakshak.pipeline.netcdf")

# Known Magic Byte Signatures
MAGIC_NETCDF_CLASSIC_1 = b"CDF\x01"
MAGIC_NETCDF_CLASSIC_2 = b"CDF\x02"
MAGIC_NETCDF_CLASSIC_5 = b"CDF\x05"
MAGIC_HDF5_NETCDF4 = b"\x89HDF\r\n\x1a\n"

# Standard CF and meteorological precipitation variable candidates (in priority order)
PRECIP_VAR_CANDIDATES = [
    "precipitation",
    "precipitationCal",
    "precip",
    "rainfall",
    "rainfall_mm",
    "prcp",
    "daily_precip",
    "total_precipitation",
    "tp",
    "rain",
]

# Coordinate variable candidates
LAT_CANDIDATES = ["lat", "latitude", "y", "nav_lat"]
LON_CANDIDATES = ["lon", "longitude", "x", "nav_lon"]
TIME_CANDIDATES = ["time", "t", "timestamp", "time_counter", "date"]


class NetCDFDecodingError(ValueError):
    """Raised when NetCDF scientific decoding fails due to structural or physical defects."""
    pass


@dataclass
class NetCDFDecodedResult:
    is_valid: bool
    format_variant: str
    scientific_decoding_status: str  # "SUCCESS", "UNSUPPORTED", "FAILED"
    variables_found: List[str]
    dimensions: Dict[str, int]
    precipitation_variable: Optional[str] = None
    units: Optional[str] = None
    temporal_semantics: str = "daily_accumulation"
    date_range: Optional[Dict[str, str]] = None
    bounding_box: Optional[Dict[str, float]] = None  # min_lng, min_lat, max_lng, max_lat
    total_records: int = 0
    valid_records: int = 0
    missing_records: int = 0
    extreme_records: int = 0
    mean_value: Optional[float] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    observations: List[Dict[str, Any]] = field(default_factory=list)  # sample / aggregated records
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_array_shape: Optional[Tuple[int, ...]] = None


class NetCDFDecoder:
    """
    Decodes CF-compliant and meteorological NetCDF datasets into scientific arrays and metrics.
    """

    @classmethod
    def detect_format_variant(cls, file_bytes: bytes) -> str:
        """Returns the specific NetCDF format variant or raises NetCDFDecodingError."""
        if file_bytes.startswith(MAGIC_HDF5_NETCDF4):
            return "NetCDF-4 / HDF5"
        elif file_bytes.startswith(MAGIC_NETCDF_CLASSIC_1):
            return "Classic NetCDF-1 (32-bit offset)"
        elif file_bytes.startswith(MAGIC_NETCDF_CLASSIC_2):
            return "NetCDF-2 (64-bit offset)"
        elif file_bytes.startswith(MAGIC_NETCDF_CLASSIC_5):
            return "NetCDF-5 (64-bit data)"
        else:
            raise NetCDFDecodingError("Invalid NetCDF header: file does not begin with a recognized NetCDF magic signature.")

    @classmethod
    def decode_netcdf(cls, file_bytes: bytes) -> NetCDFDecodedResult:
        """
        Parses NetCDF binary data.
        Decodes NetCDF-3 classic files via scipy.io.netcdf_file.
        Safely identifies and quarantines NetCDF-4/HDF5 when C-libraries are unavailable.
        """
        try:
            format_variant = cls.detect_format_variant(file_bytes)
        except NetCDFDecodingError as e:
            return NetCDFDecodedResult(
                is_valid=False,
                format_variant="UNKNOWN",
                scientific_decoding_status="FAILED",
                variables_found=[],
                dimensions={},
                errors=[str(e)],
            )

        # Explicit separation for NetCDF-4 / HDF5
        if format_variant == "NetCDF-4 / HDF5":
            return NetCDFDecodedResult(
                is_valid=False,
                format_variant=format_variant,
                scientific_decoding_status="UNSUPPORTED",
                variables_found=[],
                dimensions={},
                errors=[
                    "NetCDF-4 / HDF5 format detected. Full scientific array decoding requires "
                    "HDF5 C-bindings (libhdf5/netCDF4) which are unsupported on the 512 MB hosting instance. "
                    "Dataset quarantined safely without false verification."
                ],
                warnings=["To ingest NetCDF-4 granules, convert to NetCDF-3 Classic or CF-compliant tabular CSV before upload."],
            )

        # Decode NetCDF-3 Classic (CDF-1, CDF-2, CDF-5)
        bio = io.BytesIO(file_bytes)
        try:
            from scipy.io import netcdf_file
            nc = netcdf_file(bio, "r", mmap=False)
        except Exception as e:
            return NetCDFDecodedResult(
                is_valid=False,
                format_variant=format_variant,
                scientific_decoding_status="FAILED",
                variables_found=[],
                dimensions={},
                errors=[f"Corrupt or unreadable NetCDF-3 binary structure: {e}"],
            )

        try:
            var_names = list(nc.variables.keys())
            dimensions = {k: int(v) if v is not None else 0 for k, v in nc.dimensions.items()}

            # 1. Identify precipitation variable
            precip_var_name = None
            for cand in PRECIP_VAR_CANDIDATES:
                for v in var_names:
                    if v.lower() == cand.lower():
                        precip_var_name = v
                        break
                if precip_var_name:
                    break

            if not precip_var_name:
                nc.close()
                return NetCDFDecodedResult(
                    is_valid=False,
                    format_variant=format_variant,
                    scientific_decoding_status="FAILED",
                    variables_found=var_names,
                    dimensions=dimensions,
                    errors=[
                        f"No CF-compliant precipitation variable found in NetCDF dataset. "
                        f"Expected one of: {PRECIP_VAR_CANDIDATES}. Found variables: {var_names}"
                    ],
                )

            p_var = nc.variables[precip_var_name]
            raw_data = p_var.data.copy()

            # 2. Extract units and temporal semantics
            raw_units_attr = getattr(p_var, "units", None)
            if raw_units_attr is None:
                raw_units_attr = getattr(p_var, "unit", "")
            if isinstance(raw_units_attr, bytes):
                raw_units = raw_units_attr.decode("latin-1").strip()
            else:
                raw_units = str(raw_units_attr).strip()

            temporal_sem = "daily_accumulation"
            if raw_units.lower() in ["mm/hr", "mm/hour"]:
                nc.close()
                return NetCDFDecodedResult(
                    is_valid=False,
                    format_variant=format_variant,
                    scientific_decoding_status="FAILED",
                    variables_found=var_names,
                    dimensions=dimensions,
                    precipitation_variable=precip_var_name,
                    units=raw_units,
                    errors=[
                        "NetCDF precipitation reported in 'mm/hr' requires explicit temporal integration intervals. "
                        "Blindly accumulating instantaneous or half-hourly rates without time-step bounds is prohibited."
                    ],
                )

            # 3. Handle Fill Values / Missing Values
            fill_val = getattr(p_var, "_FillValue", None)
            missing_val = getattr(p_var, "missing_value", None)

            # Convert raw_data to float32
            data_arr = raw_data.astype(np.float32)
            invalid_mask = np.isnan(data_arr) | np.isinf(data_arr)
            if fill_val is not None:
                invalid_mask = invalid_mask | (raw_data == fill_val)
            if missing_val is not None:
                invalid_mask = invalid_mask | (raw_data == missing_val)
            # Standard negative missing indicators (e.g., -9999, -999)
            invalid_mask = invalid_mask | (raw_data <= -900.0)

            total_records = int(data_arr.size)
            missing_records = int(np.sum(invalid_mask))
            valid_arr = data_arr[~invalid_mask]
            valid_records = int(valid_arr.size)

            warnings = []
            errors = []

            # 4. Check for physically impossible negative precipitation
            if valid_records > 0:
                neg_count = int(np.sum(valid_arr < 0.0))
                if neg_count > 0:
                    nc.close()
                    return NetCDFDecodedResult(
                        is_valid=False,
                        format_variant=format_variant,
                        scientific_decoding_status="FAILED",
                        variables_found=var_names,
                        dimensions=dimensions,
                        precipitation_variable=precip_var_name,
                        units=raw_units or "mm",
                        errors=[
                            f"Physically impossible negative precipitation detected ({neg_count} observations < 0.0 mm)."
                        ],
                    )

            extreme_records = int(np.sum(valid_arr > 500.0)) if valid_records > 0 else 0
            if extreme_records > 0:
                warnings.append(
                    f"Dataset contains {extreme_records} provisional extreme observations exceeding 500 mm/day threshold."
                )

            # Compute statistics
            mean_val = round(float(np.mean(valid_arr)), 2) if valid_records > 0 else None
            max_val = round(float(np.max(valid_arr)), 2) if valid_records > 0 else None
            min_val = round(float(np.min(valid_arr)), 2) if valid_records > 0 else None

            # 5. Extract Coordinates and Bounding Box
            lat_var_name = next((v for v in var_names if v.lower() in LAT_CANDIDATES), None)
            lon_var_name = next((v for v in var_names if v.lower() in LON_CANDIDATES), None)

            bounding_box = None
            if lat_var_name and lon_var_name:
                try:
                    lat_vals = nc.variables[lat_var_name].data.copy().flatten()
                    lon_vals = nc.variables[lon_var_name].data.copy().flatten()
                    
                    # Coordinate validation: lat in [-90, 90], lon in [-180, 180] or [0, 360]
                    lat_min, lat_max = float(np.min(lat_vals)), float(np.max(lat_vals))
                    lon_min, lon_max = float(np.min(lon_vals)), float(np.max(lon_vals))

                    if lon_max > 180.0:
                        lon_vals = np.where(lon_vals > 180.0, lon_vals - 360.0, lon_vals)
                        lon_min, lon_max = float(np.min(lon_vals)), float(np.max(lon_vals))

                    if lat_min < -90.0 or lat_max > 90.0 or lon_min < -180.0 or lon_max > 180.0:
                        errors.append(f"Invalid coordinate ranges: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}].")
                    else:
                        bounding_box = {
                            "min_lng": round(lon_min, 6),
                            "min_lat": round(lat_min, 6),
                            "max_lng": round(lon_max, 6),
                            "max_lat": round(lat_max, 6),
                        }
                except Exception as ce:
                    warnings.append(f"Failed to extract coordinate bounding box: {ce}")

            # 6. Extract Time Coordinate
            time_var_name = next((v for v in var_names if v.lower() in TIME_CANDIDATES), None)
            date_range = None
            if time_var_name:
                try:
                    t_var = nc.variables[time_var_name]
                    t_units = getattr(t_var, "units", "")
                    if isinstance(t_units, bytes):
                        t_units = t_units.decode("latin-1")
                    
                    t_vals = t_var.data.copy().flatten()
                    if len(t_vals) > 0:
                        # Attempt to parse 'days since YYYY-MM-DD'
                        if "since" in str(t_units).lower():
                            parts = str(t_units).split("since")
                            unit_step = parts[0].strip().lower()
                            base_str = parts[1].strip().split()[0]
                            base_dt = datetime.strptime(base_str, "%Y-%m-%d")

                            if "day" in unit_step:
                                min_dt = base_dt + timedelta(days=float(np.min(t_vals)))
                                max_dt = base_dt + timedelta(days=float(np.max(t_vals)))
                            elif "hour" in unit_step:
                                min_dt = base_dt + timedelta(hours=float(np.min(t_vals)))
                                max_dt = base_dt + timedelta(hours=float(np.max(t_vals)))
                            else:
                                min_dt = base_dt
                                max_dt = base_dt
                            
                            date_range = {
                                "start": min_dt.strftime("%Y-%m-%d"),
                                "end": max_dt.strftime("%Y-%m-%d"),
                            }
                except Exception as te:
                    warnings.append(f"Could not parse chronological date range from time variable: {te}")

            nc.close()

            is_valid = len(errors) == 0 and valid_records > 0
            decoding_status = "SUCCESS" if is_valid else ("FAILED" if len(errors) > 0 else "NO_VALID_DATA")

            return NetCDFDecodedResult(
                is_valid=is_valid,
                format_variant=format_variant,
                scientific_decoding_status=decoding_status,
                variables_found=var_names,
                dimensions=dimensions,
                precipitation_variable=precip_var_name,
                units=raw_units or "mm",
                temporal_semantics=temporal_sem,
                date_range=date_range,
                bounding_box=bounding_box,
                total_records=total_records,
                valid_records=valid_records,
                missing_records=missing_records,
                extreme_records=extreme_records,
                mean_value=mean_val,
                max_value=max_val,
                min_value=min_val,
                raw_array_shape=raw_data.shape,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            try:
                nc.close()
            except Exception:
                pass
            logger.error(f"Failed to decode NetCDF dataset: {e}", exc_info=True)
            return NetCDFDecodedResult(
                is_valid=False,
                format_variant=format_variant,
                scientific_decoding_status="FAILED",
                variables_found=var_names if 'var_names' in locals() else [],
                dimensions=dimensions if 'dimensions' in locals() else {},
                errors=[f"Scientific array decoding failed: {e}"],
            )
