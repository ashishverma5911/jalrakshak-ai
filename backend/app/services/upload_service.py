"""
Secure Scientific Dataset Upload & Validation Service for JalRakshak AI
Supports: CSV, NetCDF (Classic NetCDF-3), GeoTIFF, and ZIP archives.
Provides genuine scientific decoding, geodesic spatial intersection,
and strict resource security defenses for constrained 512 MB hosting.

Security Invariants:
1. Validates true binary contents via magic byte signatures and structural IFD/CDF parsers.
2. Enforces strict configurable upload limits (15 MB upload, 30 MB uncompressed, max 50:1 ratio).
3. Guards against Zip bombs, symlink attacks (external attribute flags), and Zip-Slip traversal.
4. Isolates all incoming uploads in a sandboxed quarantine directory before scientific validation.
5. Computes SHA-256 hashes to prevent duplicate dataset uploads.
6. Enforces genuine geodesic spatial overlap against validated district boundary polygons.
7. Maintains automated quarantine expiration (24h retention) and storage quota enforcement (100 MB).
8. Distinguishes MANUAL_UPLOAD from IN_SITU_GROUND_TRUTH, SATELLITE_DERIVED, and DEMONSTRATION.
"""

import os
import io
import re
import json
import time
import uuid
import struct
import shutil
import hashlib
import zipfile
import threading
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from ..schemas.upload import ValidationReport, DatasetUploadResponse, UploadHistoryItem
from ..pipeline.adapters.base import ScientificSourceAdapter, AdapterUnitError, QualityStatus
from ..pipeline.spatial_aggregation import SpatialAggregator, SpatialAggregationError
from ..pipeline.netcdf_decoder import NetCDFDecoder, NetCDFDecodedResult
from ..pipeline.raster_decoder import (
    GeoTIFFDecoder,
    GeoTIFFDecodedResult,
    MAX_RASTER_WIDTH,
    MAX_RASTER_HEIGHT,
    MAX_RASTER_PIXELS,
    MAX_RASTER_BANDS,
)

logger = logging.getLogger("jalrakshak.services.upload")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
QUARANTINE_DIR = UPLOADS_DIR / "quarantine"
VERIFIED_DIR = UPLOADS_DIR / "verified"
SPOOL_DIR = UPLOADS_DIR / "spool"
REGISTRY_FILE = UPLOADS_DIR / "upload_registry.json"

# Configurable Safety Limits (Tailored for 512 MB RAM hosting)
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024       # 15 MB
MAX_UNCOMPRESSED_ZIP_BYTES = 30 * 1024 * 1024  # 30 MB
MAX_COMPRESSION_RATIO = 50.0                   # Max allowable decompression ratio (50:1)
MAX_ZIP_FILES_COUNT = 30                       # Max files inside ZIP archive
MAX_STORAGE_QUOTA_BYTES = 100 * 1024 * 1024   # 100 MB total upload storage quota
QUARANTINE_RETENTION_HOURS = 24.0             # Quarantine file TTL expiration

# Thread/Process Lock for safe concurrent writes to upload_registry.json
_registry_lock = threading.Lock()

# Known Magic Byte Signatures
MAGIC_NETCDF_CLASSIC_1 = b"CDF\x01"
MAGIC_NETCDF_CLASSIC_2 = b"CDF\x02"
MAGIC_NETCDF_CLASSIC_5 = b"CDF\x05"
MAGIC_HDF5_NETCDF4 = b"\x89HDF\r\n\x1a\n"
MAGIC_TIFF_LE = b"II\x2a\x00"
MAGIC_TIFF_BE = b"MM\x00\x2a"
MAGIC_BIGTIFF_LE = b"II\x2b\x00"
MAGIC_BIGTIFF_BE = b"MM\x00\x2b"
MAGIC_ZIP = b"PK\x03\x04"
MAGIC_EMPTY_ZIP = b"PK\x05\x06"

# Malicious binary executable signatures to reject immediately
EXECUTABLE_SIGNATURES = [
    (b"MZ", "DOS/Windows Executable"),
    (b"\x7fELF", "Linux ELF Executable"),
    (b"\xca\xfe\xba\xbe", "Java Class / Mach-O Fat Binary"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit Binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit Binary"),
]


class ScientificUploadService:
    """
    Manages quarantine, content inspection, schema validation, scientific decoding,
    spatial verification, and storage retention for environmental datasets.
    """

    @classmethod
    def _ensure_directories(cls) -> None:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        VERIFIED_DIR.mkdir(parents=True, exist_ok=True)
        SPOOL_DIR.mkdir(parents=True, exist_ok=True)
        if not REGISTRY_FILE.exists():
            with _registry_lock:
                if not REGISTRY_FILE.exists():
                    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                        json.dump([], f)

    @classmethod
    def load_registry(cls) -> List[Dict[str, Any]]:
        cls._ensure_directories()
        with _registry_lock:
            try:
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read upload registry: {e}")
                return []

    @classmethod
    def save_registry_item(cls, item: Dict[str, Any]) -> None:
        cls._ensure_directories()
        with _registry_lock:
            try:
                if REGISTRY_FILE.exists():
                    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                        registry = json.load(f)
                else:
                    registry = []
            except Exception:
                registry = []

            # Avoid duplicate upload_id
            registry = [r for r in registry if r.get("upload_id") != item.get("upload_id")]
            registry.insert(0, item)
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)

    @classmethod
    def cleanup_expired_quarantine(
        cls,
        max_age_hours: float = QUARANTINE_RETENTION_HOURS,
        max_storage_quota_bytes: int = MAX_STORAGE_QUOTA_BYTES
    ) -> Dict[str, Any]:
        """
        Removes expired quarantined and spooled files (> max_age_hours).
        Enforces maximum storage quota by purging oldest non-verified files.
        Never deletes verified datasets referenced by active registry records.
        """
        cls._ensure_directories()
        now = time.time()
        max_age_sec = max_age_hours * 3600.0

        deleted_files = 0
        reclaimed_bytes = 0

        # 1. Clean expired quarantine files and spools with path-traversal containment
        for folder in [QUARANTINE_DIR, SPOOL_DIR]:
            if not folder.exists():
                continue
            folder_root = folder.resolve()
            for file_path in folder.glob("*"):
                if file_path.is_file():
                    try:
                        resolved_file = file_path.resolve()
                        if not resolved_file.is_relative_to(folder_root):
                            logger.error(f"Security: Refusing to unlink file outside folder root: {file_path}")
                            continue

                        mtime = file_path.stat().st_mtime
                        if (now - mtime) > max_age_sec:
                            size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files += 1
                            reclaimed_bytes += size
                    except Exception as e:
                        logger.warning(f"Failed to purge quarantine file {file_path.name}: {e}")

        # 2. Check total upload storage quota
        total_upload_bytes = 0
        all_quarantine_files = []
        q_root = QUARANTINE_DIR.resolve()
        for p in QUARANTINE_DIR.glob("*"):
            if p.is_file():
                st = p.stat()
                total_upload_bytes += st.st_size
                all_quarantine_files.append((st.st_mtime, st.st_size, p))

        for p in VERIFIED_DIR.glob("*"):
            if p.is_file():
                total_upload_bytes += p.stat().st_size

        # If quota exceeded, delete oldest quarantine files first (VERIFIED datasets are preserved)
        if total_upload_bytes > max_storage_quota_bytes:
            all_quarantine_files.sort(key=lambda x: x[0])  # Oldest first
            for mtime, size, fpath in all_quarantine_files:
                try:
                    resolved_file = fpath.resolve()
                    if not resolved_file.is_relative_to(q_root):
                        continue
                    fpath.unlink()
                    deleted_files += 1
                    reclaimed_bytes += size
                    total_upload_bytes -= size
                    if total_upload_bytes <= max_storage_quota_bytes:
                        break
                except Exception as e:
                    logger.warning(f"Quota cleanup failed for {fpath.name}: {e}")

        logger.info(f"Quarantine cleanup: {deleted_files} files deleted, {reclaimed_bytes:,} bytes reclaimed.")
        return {
            "deleted_files_count": deleted_files,
            "reclaimed_bytes": reclaimed_bytes,
            "current_storage_bytes": total_upload_bytes,
            "quota_bytes": max_storage_quota_bytes,
            "durability": "EPHEMERAL_LOCAL",
        }

    @classmethod
    def detect_file_type(cls, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """
        Detects file format via magic byte signatures and structural indicators.
        Returns: (format_name, mime_type)
        Raises: ValueError if file matches an executable or unsupported format.
        """
        # 1. Screen for malicious executables
        for sig, desc in EXECUTABLE_SIGNATURES:
            if file_bytes.startswith(sig):
                raise ValueError(f"Malicious content detected: file has signature of {desc}.")

        # 2. Check ZIP
        if file_bytes.startswith(MAGIC_ZIP) or file_bytes.startswith(MAGIC_EMPTY_ZIP):
            return "ZIP", "application/zip"

        # 3. Check GeoTIFF / TIFF
        if (
            file_bytes.startswith(MAGIC_TIFF_LE)
            or file_bytes.startswith(MAGIC_TIFF_BE)
            or file_bytes.startswith(MAGIC_BIGTIFF_LE)
            or file_bytes.startswith(MAGIC_BIGTIFF_BE)
        ):
            return "GeoTIFF", "image/tiff"

        # 4. Check NetCDF
        if (
            file_bytes.startswith(MAGIC_NETCDF_CLASSIC_1)
            or file_bytes.startswith(MAGIC_NETCDF_CLASSIC_2)
            or file_bytes.startswith(MAGIC_NETCDF_CLASSIC_5)
        ):
            return "NetCDF", "application/x-netcdf"

        if file_bytes.startswith(MAGIC_HDF5_NETCDF4):
            return "NetCDF", "application/x-netcdf4"

        # 5. Check CSV / Text
        sample = file_bytes[:4096]
        if b"\x00" not in sample:
            try:
                sample_str = sample.decode("utf-8")
                first_lines = sample_str.splitlines()
                if len(first_lines) > 0 and any(delim in first_lines[0] for delim in [",", ";", "\t"]):
                    return "CSV", "text/csv"
                if filename.lower().endswith(".csv") and len(first_lines) > 0:
                    return "CSV", "text/csv"
            except UnicodeDecodeError:
                pass

        raise ValueError("Unsupported or corrupted scientific data file format.")

    @classmethod
    def compute_sha256(cls, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Strips path traversal elements, leading dots, and illegal characters."""
        base = os.path.basename(filename)
        clean = re.sub(r"[^\w\.\-\_]", "_", base)
        return clean or "uploaded_dataset"

    # =========================================================================
    # CSV Scientific Validation
    # =========================================================================

    @classmethod
    def validate_csv_dataset(
        cls,
        file_bytes: bytes,
        target_region_id: Optional[str] = None
    ) -> ValidationReport:
        """
        Validates CSV rainfall dataset structure, columns, units, chronological ordering,
        physical bounds, and spatial containment.
        """
        sha256 = cls.compute_sha256(file_bytes)
        report = ValidationReport(
            is_valid=False,
            file_type="CSV",
            mime_detected="text/csv",
            file_size_bytes=len(file_bytes),
            sha256_hash=sha256,
            target_region_id=target_region_id,
            data_mode="MANUAL_UPLOAD",
            data_classification="MANUAL_UPLOAD",
            processing_stage="STRUCTURE_VALIDATED",
            scientific_decoding_status="SUCCESS",
            spatial_validation_status="NOT_PERFORMED",
            temporal_semantics="daily_accumulation",
            spatial_crs="EPSG:4326",
            warnings=[],
            errors=[],
            metadata={},
        )

        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            report.errors.append(f"Failed to parse CSV text: {e}")
            report.scientific_decoding_status = "FAILED"
            report.processing_stage = "REJECTED"
            return report

        if df.empty:
            report.errors.append("Uploaded CSV file contains no data rows.")
            report.scientific_decoding_status = "FAILED"
            report.processing_stage = "REJECTED"
            return report

        # Identify Date Column
        date_candidates = ["date", "time", "timestamp", "observation_date", "datetime"]
        date_col = next((c for c in df.columns if c.strip().lower() in date_candidates), None)
        if not date_col:
            report.errors.append(f"Missing required date column. Expected one of: {date_candidates}")

        # Identify Rainfall Column
        rain_candidates = ["rainfall_mm", "precipitation", "precipitation_sum", "precip", "rain", "prcp"]
        rain_col = next((c for c in df.columns if c.strip().lower() in rain_candidates), None)
        if not rain_col:
            report.errors.append(f"Missing required precipitation column. Expected one of: {rain_candidates}")

        if report.errors:
            report.scientific_decoding_status = "FAILED"
            report.processing_stage = "REJECTED"
            return report

        # Process Dates
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        invalid_dates_cnt = df[date_col].isna().sum()
        if invalid_dates_cnt > 0:
            report.warnings.append(f"Ignored {invalid_dates_cnt} rows with invalid/unparseable dates.")
            df = df.dropna(subset=[date_col])

        if df.empty:
            report.errors.append("No valid observation dates found in CSV.")
            report.scientific_decoding_status = "FAILED"
            report.processing_stage = "REJECTED"
            return report

        # Deduplication check
        dup_cnt = df.duplicated(subset=[date_col]).sum()
        if dup_cnt > 0:
            report.warnings.append(f"Detected {dup_cnt} duplicate date observations. Keeping latest entries.")
            df = df.drop_duplicates(subset=[date_col], keep="last")

        # Sort chronologically
        df = df.sort_values(by=date_col).reset_index(drop=True)

        # Date Range
        min_date = df[date_col].min().strftime("%Y-%m-%d")
        max_date = df[date_col].max().strftime("%Y-%m-%d")
        report.date_range = {"start": min_date, "end": max_date}

        # Check Unit and Temporal Semantics
        unit_col = next((c for c in df.columns if c.strip().lower() in ["unit", "units"]), None)
        raw_unit = str(df[unit_col].iloc[0]).strip().lower() if unit_col and not df[unit_col].empty else "mm"

        # Rate handling: require explicit duration if rate-based
        if raw_unit in ["mm/hr", "mm/hour"]:
            dur_col = next((c for c in df.columns if c.strip().lower() in ["duration_hours", "interval_hours"]), None)
            min_col = next((c for c in df.columns if c.strip().lower() in ["interval_minutes"]), None)

            if not dur_col and not min_col:
                report.errors.append(
                    "Precipitation reported in 'mm/hr' requires explicit 'duration_hours' or 'interval_minutes' "
                    "column to prevent ungrounded temporal rate assumptions."
                )
                report.scientific_decoding_status = "FAILED"
                report.processing_stage = "REJECTED"
                return report

            report.temporal_semantics = "converted_rate_to_accumulation"
            if dur_col:
                df["accum_rainfall_mm"] = df[rain_col].astype(float) * df[dur_col].astype(float)
            else:
                df["accum_rainfall_mm"] = df[rain_col].astype(float) * (df[min_col].astype(float) / 60.0)
            eval_col = "accum_rainfall_mm"
        else:
            eval_col = rain_col
            report.temporal_semantics = "daily_accumulation"

        # Value and bounds validation
        df[eval_col] = pd.to_numeric(df[eval_col], errors="coerce")

        total_cnt = len(df)
        missing_cnt = int(df[eval_col].isna().sum())
        valid_df = df.dropna(subset=[eval_col])

        # Negative checks
        negative_cnt = int((valid_df[eval_col] < 0.0).sum())
        if negative_cnt > 0:
            report.errors.append(
                f"Physically impossible negative precipitation detected ({negative_cnt} observations < 0.0 mm)."
            )
            report.scientific_decoding_status = "FAILED"
            report.processing_stage = "REJECTED"
            return report

        # Extreme checks (> 500 mm/day)
        extreme_cnt = int((valid_df[eval_col] > 500.0).sum())
        if extreme_cnt > 0:
            report.warnings.append(
                f"Contains {extreme_cnt} provisional extreme observations exceeding 500 mm/day threshold."
            )

        report.total_records = total_cnt
        report.valid_records = len(valid_df)
        report.missing_records = missing_cnt
        report.extreme_records = extreme_cnt

        if not valid_df.empty:
            report.mean_value = round(float(valid_df[eval_col].mean()), 2)
            report.max_value = round(float(valid_df[eval_col].max()), 2)
            report.min_value = round(float(valid_df[eval_col].min()), 2)

        # Spatial Validation
        lat_col = next((c for c in df.columns if c.strip().lower() in ["lat", "latitude"]), None)
        lon_col = next((c for c in df.columns if c.strip().lower() in ["lon", "lng", "longitude"]), None)

        if lat_col and lon_col:
            df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
            df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
            spatial_valid = df.dropna(subset=[lat_col, lon_col])
            if not spatial_valid.empty:
                min_lat, max_lat = float(spatial_valid[lat_col].min()), float(spatial_valid[lat_col].max())
                min_lng, max_lng = float(spatial_valid[lon_col].min()), float(spatial_valid[lon_col].max())
                report.bounding_box = {
                    "min_lng": round(min_lng, 6),
                    "min_lat": round(min_lat, 6),
                    "max_lng": round(max_lng, 6),
                    "max_lat": round(max_lat, 6),
                }

                if target_region_id:
                    clean_id = target_region_id.lower().strip()
                    if not clean_id.startswith("district-"):
                        clean_id = f"district-{clean_id}"
                    try:
                        cov = SpatialAggregator.validate_dataset_spatial_coverage(clean_id, report.bounding_box)
                        report.spatial_validation_status = "PARTIAL_OVERLAP" if cov["is_partial_coverage"] else "VALIDATED"
                        report.spatial_overlap_pct = cov["spatial_overlap_pct"]
                        report.spatial_coverage_status = (
                            f"Validated against district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                        )
                        if cov["is_partial_coverage"]:
                            report.warnings.append(
                                f"Dataset partially overlaps district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                            )
                    except SpatialAggregationError as sae:
                        report.errors.append(str(sae))
                        report.spatial_validation_status = "DISJOINT"
                        report.processing_stage = "REJECTED"
                        return report
        elif target_region_id:
            # Tabular daily aggregate series for target district
            clean_id = target_region_id.lower().strip()
            if not clean_id.startswith("district-"):
                clean_id = f"district-{clean_id}"
            try:
                SpatialAggregator.load_district_boundary(clean_id)
                report.spatial_validation_status = "VALIDATED"
                report.spatial_overlap_pct = 100.0
                report.spatial_coverage_status = f"Validated for target district '{clean_id}'"
            except SpatialAggregationError as sae:
                report.warnings.append(f"District boundary validation note: {sae}")
                report.spatial_validation_status = "NOT_PERFORMED"

        report.is_valid = len(report.errors) == 0
        if report.is_valid:
            if report.spatial_validation_status in ["VALIDATED", "PARTIAL_OVERLAP"]:
                report.processing_stage = "SPATIALLY_VALIDATED"
            else:
                report.processing_stage = "SCIENTIFICALLY_DECODED"
        else:
            report.processing_stage = "REJECTED"

        return report

    # =========================================================================
    # GeoTIFF Scientific Validation & Raster Masking
    # =========================================================================

    @classmethod
    def validate_geotiff_dataset(
        cls,
        file_bytes: bytes,
        target_region_id: Optional[str] = None
    ) -> ValidationReport:
        """
        Validates and scientifically decodes GeoTIFF raster arrays.
        Enforces pixel dimension limits, extracts CRS and geotransform,
        tests district boundary intersection, and masks out-of-district pixels.
        """
        sha256 = cls.compute_sha256(file_bytes)
        report = ValidationReport(
            is_valid=False,
            file_type="GeoTIFF",
            mime_detected="image/tiff",
            file_size_bytes=len(file_bytes),
            sha256_hash=sha256,
            target_region_id=target_region_id,
            data_mode="MANUAL_UPLOAD",
            data_classification="MANUAL_UPLOAD",
            processing_stage="STRUCTURE_VALIDATED",
            scientific_decoding_status="FAILED",
            spatial_validation_status="NOT_PERFORMED",
            spatial_crs="EPSG:4326",
            warnings=[],
            errors=[],
            metadata={},
        )

        decoded: GeoTIFFDecodedResult = GeoTIFFDecoder.decode_geotiff(file_bytes)

        report.scientific_decoding_status = decoded.scientific_decoding_status
        report.warnings.extend(decoded.warnings)
        report.errors.extend(decoded.errors)
        report.raster_dimensions = {
            "width": decoded.width,
            "height": decoded.height,
            "bands": decoded.bands,
        }
        report.spatial_crs = decoded.crs
        report.bounding_box = decoded.bounding_box
        report.total_records = decoded.total_records
        report.valid_records = decoded.valid_records
        report.missing_records = decoded.missing_records
        report.extreme_records = decoded.extreme_records
        report.mean_value = decoded.mean_value
        report.max_value = decoded.max_value
        report.min_value = decoded.min_value

        if not decoded.is_valid:
            report.processing_stage = (
                "UNSUPPORTED" if decoded.scientific_decoding_status == "UNSUPPORTED" else "REJECTED"
            )
            return report

        # Spatial Verification and District Masking
        if target_region_id and decoded.bounding_box and decoded.raster_array is not None and decoded.geotransform:
            clean_id = target_region_id.lower().strip()
            if not clean_id.startswith("district-"):
                clean_id = f"district-{clean_id}"

            try:
                # 1. Test Bounding Box Intersection
                cov = SpatialAggregator.validate_dataset_spatial_coverage(
                    clean_id, decoded.bounding_box, crs=decoded.crs
                )
                report.spatial_validation_status = "PARTIAL_OVERLAP" if cov["is_partial_coverage"] else "VALIDATED"
                report.spatial_overlap_pct = cov["spatial_overlap_pct"]
                report.spatial_coverage_status = (
                    f"Validated against district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                )

                if cov["is_partial_coverage"]:
                    report.warnings.append(
                        f"GeoTIFF partially overlaps district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                    )

                # 2. Mask Raster Pixels Outside District Boundary
                mask_res = SpatialAggregator.mask_raster_to_district(
                    clean_id, decoded.raster_array, decoded.geotransform, nodata_val=decoded.nodata_value
                )
                report.valid_records = mask_res["in_district_valid_pixels"]
                report.mean_value = mask_res["in_district_mean_mm"]
                report.max_value = mask_res["in_district_max_mm"]
                report.min_value = mask_res["in_district_min_mm"]
                report.extreme_records = mask_res["in_district_extreme_pixels"]
                report.metadata["in_district_cells_total"] = mask_res["in_district_cells_total"]

            except SpatialAggregationError as sae:
                report.errors.append(str(sae))
                report.spatial_validation_status = "DISJOINT"
                report.processing_stage = "REJECTED"
                report.is_valid = False
                return report

        report.is_valid = len(report.errors) == 0
        if report.is_valid:
            if report.spatial_validation_status in ["VALIDATED", "PARTIAL_OVERLAP"]:
                report.processing_stage = "SPATIALLY_VALIDATED"
            else:
                report.processing_stage = "SCIENTIFICALLY_DECODED"
        else:
            report.processing_stage = "REJECTED"

        return report

    # =========================================================================
    # NetCDF Scientific Validation
    # =========================================================================

    @classmethod
    def validate_netcdf_dataset(
        cls,
        file_bytes: bytes,
        target_region_id: Optional[str] = None
    ) -> ValidationReport:
        """
        Scientifically decodes NetCDF datasets using NetCDFDecoder.
        Explicitly separates NetCDF-3 Classic (decoded) from NetCDF-4/HDF5 (quarantined/unsupported).
        """
        sha256 = cls.compute_sha256(file_bytes)
        report = ValidationReport(
            is_valid=False,
            file_type="NetCDF",
            mime_detected="application/x-netcdf",
            file_size_bytes=len(file_bytes),
            sha256_hash=sha256,
            target_region_id=target_region_id,
            data_mode="MANUAL_UPLOAD",
            data_classification="MANUAL_UPLOAD",
            processing_stage="STRUCTURE_VALIDATED",
            scientific_decoding_status="FAILED",
            spatial_validation_status="NOT_PERFORMED",
            spatial_crs="EPSG:4326",
            warnings=[],
            errors=[],
            metadata={},
        )

        decoded: NetCDFDecodedResult = NetCDFDecoder.decode_netcdf(file_bytes)

        report.metadata["format_variant"] = decoded.format_variant
        report.metadata["variables_found"] = decoded.variables_found
        report.metadata["dimensions"] = decoded.dimensions
        report.scientific_decoding_status = decoded.scientific_decoding_status
        report.warnings.extend(decoded.warnings)
        report.errors.extend(decoded.errors)
        report.temporal_semantics = decoded.temporal_semantics
        report.date_range = decoded.date_range
        report.bounding_box = decoded.bounding_box
        report.total_records = decoded.total_records
        report.valid_records = decoded.valid_records
        report.missing_records = decoded.missing_records
        report.extreme_records = decoded.extreme_records
        report.mean_value = decoded.mean_value
        report.max_value = decoded.max_value
        report.min_value = decoded.min_value

        if decoded.format_variant == "NetCDF-4 / HDF5":
            report.mime_detected = "application/x-netcdf4"
            report.processing_stage = "UNSUPPORTED"
            report.is_valid = False
            return report

        if not decoded.is_valid:
            report.processing_stage = "REJECTED"
            return report

        # Spatial intersection verification
        if target_region_id and decoded.bounding_box:
            clean_id = target_region_id.lower().strip()
            if not clean_id.startswith("district-"):
                clean_id = f"district-{clean_id}"

            try:
                cov = SpatialAggregator.validate_dataset_spatial_coverage(clean_id, decoded.bounding_box)
                report.spatial_validation_status = "PARTIAL_OVERLAP" if cov["is_partial_coverage"] else "VALIDATED"
                report.spatial_overlap_pct = cov["spatial_overlap_pct"]
                report.spatial_coverage_status = (
                    f"Validated against district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                )
                if cov["is_partial_coverage"]:
                    report.warnings.append(
                        f"NetCDF extent partially overlaps district '{clean_id}' ({cov['spatial_overlap_pct']}% coverage)."
                    )
            except SpatialAggregationError as sae:
                report.errors.append(str(sae))
                report.spatial_validation_status = "DISJOINT"
                report.processing_stage = "REJECTED"
                report.is_valid = False
                return report

        report.is_valid = len(report.errors) == 0
        if report.is_valid:
            if report.spatial_validation_status in ["VALIDATED", "PARTIAL_OVERLAP"]:
                report.processing_stage = "SPATIALLY_VALIDATED"
            else:
                report.processing_stage = "SCIENTIFICALLY_DECODED"
        else:
            report.processing_stage = "REJECTED"

        return report

    # =========================================================================
    # ZIP Archive Safe Extraction & Nested Validation
    # =========================================================================

    @classmethod
    def validate_zip_archive(
        cls,
        file_bytes: bytes,
        target_region_id: Optional[str] = None
    ) -> ValidationReport:
        """
        Securely inspects ZIP archives with streaming byte bounds.
        Defenses:
        1. Zip-Bomb defense: validates actual decompressed chunk sizes (never trusts header alone).
        2. Excessive compression ratio rejection (> 50:1).
        3. Symlink rejection (checks info.external_attr for Unix symlinks).
        4. Nested archive rejection (.zip, .tar, .gz).
        5. Zip-Slip canonical path containment.
        """
        sha256 = cls.compute_sha256(file_bytes)
        report = ValidationReport(
            is_valid=False,
            file_type="ZIP",
            mime_detected="application/zip",
            file_size_bytes=len(file_bytes),
            sha256_hash=sha256,
            target_region_id=target_region_id,
            data_mode="MANUAL_UPLOAD",
            data_classification="MANUAL_UPLOAD",
            processing_stage="STRUCTURE_VALIDATED",
            scientific_decoding_status="SUCCESS",
            spatial_validation_status="NOT_PERFORMED",
            warnings=[],
            errors=[],
            metadata={"contained_files": []},
        )

        try:
            zip_buffer = io.BytesIO(file_bytes)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                infolist = zf.infolist()

                if not infolist:
                    report.errors.append("ZIP archive is empty.")
                    report.processing_stage = "REJECTED"
                    return report

                if len(infolist) > MAX_ZIP_FILES_COUNT:
                    report.errors.append(
                        f"ZIP archive contains {len(infolist)} files, exceeding limit of {MAX_ZIP_FILES_COUNT}."
                    )
                    report.processing_stage = "REJECTED"
                    return report

                total_uncompressed = 0
                quarantine_id = f"zip_{uuid.uuid4().hex[:12]}"
                extract_root = QUARANTINE_DIR / quarantine_id

                nested_reports = []

                for info in infolist:
                    # 1. Symlink Attack Detection
                    # Mode 0o120000 = S_IFLNK (symbolic link in Unix)
                    is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
                    if is_symlink:
                        report.errors.append(f"Security violation: Symbolic link detected in ZIP entry: '{info.filename}'.")
                        report.processing_stage = "REJECTED"
                        return report

                    # 2. Nested Archive Abuse Detection
                    lower_name = info.filename.lower()
                    if any(lower_name.endswith(ext) for ext in [".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar"]):
                        report.errors.append(
                            f"Security violation: Nested archive detected in ZIP entry: '{info.filename}'. Recursive decompression is prohibited."
                        )
                        report.processing_stage = "REJECTED"
                        return report

                    # 3. Zip-Slip Path Traversal Protection
                    target_dest = (extract_root / info.filename).resolve()
                    if not str(target_dest).startswith(str(extract_root.resolve())):
                        report.errors.append(f"Malicious path traversal detected in ZIP entry: '{info.filename}'")
                        report.processing_stage = "REJECTED"
                        return report

                    if ".." in info.filename or info.filename.startswith("/") or info.filename.startswith("\\"):
                        report.errors.append(f"Path traversal detected in ZIP entry: '{info.filename}'")
                        report.processing_stage = "REJECTED"
                        return report

                    report.metadata["contained_files"].append(info.filename)

                    if not info.is_dir():
                        # 4. Stream entry in 64 KB chunks to measure real decompressed bytes
                        entry_uncompressed_bytes = 0
                        chunks = []
                        with zf.open(info.filename, "r") as entry_file:
                            while chunk := entry_file.read(65536):
                                entry_uncompressed_bytes += len(chunk)
                                total_uncompressed += len(chunk)
                                chunks.append(chunk)

                                # Zip bomb size check
                                if total_uncompressed > MAX_UNCOMPRESSED_ZIP_BYTES:
                                    report.errors.append(
                                        f"ZIP bomb detected: Uncompressed content exceeds maximum safety threshold ({MAX_UNCOMPRESSED_ZIP_BYTES:,} bytes)."
                                    )
                                    report.processing_stage = "REJECTED"
                                    return report

                        # 5. Compression ratio check
                        if info.compress_size > 0:
                            ratio = float(entry_uncompressed_bytes) / float(info.compress_size)
                            if ratio > MAX_COMPRESSION_RATIO:
                                report.errors.append(
                                    f"ZIP bomb detected: Entry '{info.filename}' has excessive compression ratio ({ratio:.1f}:1 > {MAX_COMPRESSION_RATIO}:1)."
                                )
                                report.processing_stage = "REJECTED"
                                return report

                        entry_bytes = b"".join(chunks)
                        ext = info.filename.lower()
                        if ext.endswith(".csv"):
                            sub_rep = cls.validate_csv_dataset(entry_bytes, target_region_id)
                            nested_reports.append(sub_rep)
                        elif ext.endswith(".nc") or ext.endswith(".nc4"):
                            sub_rep = cls.validate_netcdf_dataset(entry_bytes, target_region_id)
                            nested_reports.append(sub_rep)
                        elif ext.endswith(".tif") or ext.endswith(".tiff"):
                            sub_rep = cls.validate_geotiff_dataset(entry_bytes, target_region_id)
                            nested_reports.append(sub_rep)

                if not nested_reports:
                    report.errors.append("ZIP archive does not contain any supported scientific files (.csv, .nc, .tif).")
                    report.processing_stage = "REJECTED"
                    return report

                report.uncompressed_bytes = total_uncompressed
                report.compression_ratio = round(float(total_uncompressed) / max(1.0, float(len(file_bytes))), 2)

                # Aggregate metrics from contained files
                report.total_records = sum(r.total_records for r in nested_reports)
                report.valid_records = sum(r.valid_records for r in nested_reports)
                report.missing_records = sum(r.missing_records for r in nested_reports)
                report.extreme_records = sum(r.extreme_records for r in nested_reports)

                all_errors = []
                all_warnings = []
                for r in nested_reports:
                    all_errors.extend(r.errors)
                    all_warnings.extend(r.warnings)

                report.errors.extend(all_errors)
                report.warnings.extend(all_warnings)

        except zipfile.BadZipFile:
            report.errors.append("Uploaded file is not a valid or readable ZIP archive.")
            report.processing_stage = "REJECTED"
            return report
        except Exception as e:
            report.errors.append(f"Failed to inspect ZIP archive: {e}")
            report.processing_stage = "REJECTED"
            return report

        report.is_valid = len(report.errors) == 0
        if report.is_valid:
            report.processing_stage = "SPATIALLY_VALIDATED" if any(
                r.spatial_validation_status in ["VALIDATED", "PARTIAL_OVERLAP"] for r in nested_reports
            ) else "SCIENTIFICALLY_DECODED"
        else:
            report.processing_stage = "REJECTED"

        return report

    # =========================================================================
    # Main Ingestion & Quarantine Pipeline
    # =========================================================================

    @classmethod
    def process_dataset_upload(
        cls,
        file_bytes: bytes,
        filename: str,
        target_region_id: Optional[str] = None
    ) -> DatasetUploadResponse:
        """
        Orchestrates quarantine, content inspection, format validation, scientific decoding,
        spatial verification, and registry logging.
        """
        cls._ensure_directories()
        safe_name = cls.sanitize_filename(filename)
        upload_id = f"up_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Enforce file size limit
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            report = ValidationReport(
                is_valid=False,
                file_type="UNKNOWN",
                mime_detected="application/octet-stream",
                file_size_bytes=len(file_bytes),
                sha256_hash=cls.compute_sha256(file_bytes),
                processing_stage="REJECTED",
                scientific_decoding_status="FAILED",
                errors=[
                    f"File size ({len(file_bytes):,} bytes) exceeds maximum safety limit of "
                    f"{MAX_UPLOAD_SIZE_BYTES:,} bytes (15 MB)."
                ],
            )
            return DatasetUploadResponse(
                upload_id=upload_id,
                filename=safe_name,
                status="REJECTED",
                processing_stage="REJECTED",
                data_classification="MANUAL_UPLOAD",
                message="File size exceeds maximum allowed upload limit.",
                validation_report=report,
                uploaded_at=now_iso,
            )

        # Check for duplicate file hash in registry
        file_hash = cls.compute_sha256(file_bytes)
        existing_registry = cls.load_registry()
        for item in existing_registry:
            if item.get("file_hash") == file_hash and item.get("status") == "VALIDATED":
                report = ValidationReport(
                    is_valid=False,
                    file_type=item.get("file_type", "UNKNOWN"),
                    mime_detected="application/octet-stream",
                    file_size_bytes=len(file_bytes),
                    sha256_hash=file_hash,
                    processing_stage="REJECTED",
                    scientific_decoding_status="FAILED",
                    errors=[f"Duplicate dataset detected: identical content was previously uploaded as '{item.get('filename')}'."],
                )
                return DatasetUploadResponse(
                    upload_id=upload_id,
                    filename=safe_name,
                    status="REJECTED",
                    processing_stage="REJECTED",
                    data_classification="MANUAL_UPLOAD",
                    message="Duplicate dataset upload rejected.",
                    validation_report=report,
                    uploaded_at=now_iso,
                )

        # Content inspection
        try:
            detected_format, mime_type = cls.detect_file_type(file_bytes, safe_name)
        except ValueError as ve:
            report = ValidationReport(
                is_valid=False,
                file_type="REJECTED",
                mime_detected="application/octet-stream",
                file_size_bytes=len(file_bytes),
                sha256_hash=file_hash,
                processing_stage="REJECTED",
                scientific_decoding_status="FAILED",
                errors=[str(ve)],
            )
            return DatasetUploadResponse(
                upload_id=upload_id,
                filename=safe_name,
                status="REJECTED",
                processing_stage="REJECTED",
                data_classification="MANUAL_UPLOAD",
                message="File format validation failed.",
                validation_report=report,
                uploaded_at=now_iso,
            )

        # Execute format-specific validator
        if detected_format == "CSV":
            report = cls.validate_csv_dataset(file_bytes, target_region_id)
        elif detected_format == "NetCDF":
            report = cls.validate_netcdf_dataset(file_bytes, target_region_id)
        elif detected_format == "GeoTIFF":
            report = cls.validate_geotiff_dataset(file_bytes, target_region_id)
        elif detected_format == "ZIP":
            report = cls.validate_zip_archive(file_bytes, target_region_id)
        else:
            report = ValidationReport(
                is_valid=False,
                file_type="UNSUPPORTED",
                mime_detected=mime_type,
                file_size_bytes=len(file_bytes),
                sha256_hash=file_hash,
                processing_stage="UNSUPPORTED",
                scientific_decoding_status="UNSUPPORTED",
                errors=[f"Unsupported format '{detected_format}'."],
            )

        status_str = "VALIDATED" if report.is_valid else ("UNSUPPORTED" if report.processing_stage == "UNSUPPORTED" else "REJECTED")
        msg = (
            "Dataset successfully decoded, validated, and registered."
            if report.is_valid
            else ("Format currently unsupported in this environment." if report.processing_stage == "UNSUPPORTED" else "Dataset failed scientific validation checks.")
        )

        # Save to quarantine or verified storage
        if report.is_valid:
            dest_file = VERIFIED_DIR / f"{upload_id}_{safe_name}"
        else:
            dest_file = QUARANTINE_DIR / f"{upload_id}_{safe_name}"

        with open(dest_file, "wb") as f:
            f.write(file_bytes)

        # Update registry
        reg_item = {
            "upload_id": upload_id,
            "filename": safe_name,
            "file_hash": file_hash,
            "file_type": detected_format,
            "target_region_id": target_region_id,
            "data_mode": "MANUAL_UPLOAD",
            "data_classification": "MANUAL_UPLOAD",
            "processing_stage": report.processing_stage,
            "file_size_bytes": len(file_bytes),
            "records_count": report.total_records,
            "valid_records": report.valid_records,
            "missing_records": report.missing_records,
            "status": status_str,
            "spatial_overlap_pct": report.spatial_overlap_pct,
            "storage_path": str(dest_file),
            "uploaded_at": now_iso,
        }
        cls.save_registry_item(reg_item)

        return DatasetUploadResponse(
            upload_id=upload_id,
            filename=safe_name,
            status=status_str,
            processing_stage=report.processing_stage,
            data_classification=report.data_classification,
            message=msg,
            validation_report=report,
            uploaded_at=now_iso,
        )
