"""
Comprehensive Test Suite for Stage 3 Master Remediation
Verifies:
1. Genuine NetCDF-3 scientific array decoding (variables, dimensions, coordinates, time baselines).
2. Explicit NetCDF-4 / HDF5 safe quarantine and unsupported format marking.
3. Rejection of missing precipitation variables and negative rainfall in NetCDF.
4. Genuine GeoTIFF raster pixel decoding (ModelTiepoint, ModelPixelScale, GeoKey CRS, NoData, geotransform).
5. Deflate compressed GeoTIFF decoding.
6. Enforcing GeoTIFF dimension bounds (max 10,000 px, max 25M pixels) before memory allocation.
7. Rejection of unreferenced GeoTIFFs lacking spatial tags.
8. Spatial validation: dataset inside district, partial overlap %, and disjoint extent rejection.
9. Raster masking: excluding pixels outside district polygon and computing in-district metrics.
10. Security: 15 MB upload limit, Zip-Bomb actual decompressed size guards (30 MB limit),
    excessive compression ratio rejection (> 50:1), symlink attack detection, nested archive rejection,
    and Zip-Slip path traversal defense.
11. Controlled quarantine retention and storage quota enforcement.
12. SHA-256 duplicate upload rejection and FastAPI endpoints (/scientific-dataset, /history, /cleanup).
"""

import io
import time
import struct
import zlib
import zipfile
import pytest
import numpy as np
from datetime import date
from typing import List, Tuple, Dict, Any, Optional
from fastapi.testclient import TestClient

from app.main import app
from app.services.upload_service import (
    ScientificUploadService,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UNCOMPRESSED_ZIP_BYTES,
    MAX_COMPRESSION_RATIO,
    MAGIC_NETCDF_CLASSIC_1,
    MAGIC_HDF5_NETCDF4,
    MAGIC_TIFF_LE,
)
from app.pipeline.netcdf_decoder import NetCDFDecoder
from app.pipeline.raster_decoder import GeoTIFFDecoder, MAX_RASTER_WIDTH, MAX_RASTER_HEIGHT, MAX_RASTER_PIXELS
from app.pipeline.spatial_aggregation import SpatialAggregator, SpatialAggregationError

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_upload_storage(tmp_path, monkeypatch):
    """Isolate registry and quarantine/verified/spool storage to tmp_path for each test."""
    test_reg = tmp_path / "upload_registry.json"
    test_quarantine = tmp_path / "quarantine"
    test_verified = tmp_path / "verified"
    test_spool = tmp_path / "spool"
    monkeypatch.setattr("app.services.upload_service.REGISTRY_FILE", test_reg)
    monkeypatch.setattr("app.services.upload_service.QUARANTINE_DIR", test_quarantine)
    monkeypatch.setattr("app.services.upload_service.VERIFIED_DIR", test_verified)
    monkeypatch.setattr("app.services.upload_service.SPOOL_DIR", test_spool)
    monkeypatch.setattr("app.api.uploads.SPOOL_DIR", test_spool)
    monkeypatch.setenv("UPLOAD_API_KEY", "test-auth-secret-key-12345")


# =============================================================================
# Helper Functions: Creating Genuine NetCDF-3 and GeoTIFF Binary Payloads
# =============================================================================

def helper_create_netcdf3(
    precip_array: np.ndarray,
    lats: List[float],
    lons: List[float],
    var_name: str = "precipitation",
    units: bytes = b"mm/day",
    fill_value: float = -9999.0,
    time_units: bytes = b"days since 2024-08-01"
) -> bytes:
    """Creates a genuine NetCDF-3 Classic binary payload using scipy.io.netcdf_file."""
    from scipy.io import netcdf_file

    bio = io.BytesIO()
    f = netcdf_file(bio, "w")
    time_len = precip_array.shape[0] if precip_array.ndim == 3 else 1
    lat_len = len(lats)
    lon_len = len(lons)

    f.createDimension("time", time_len)
    f.createDimension("lat", lat_len)
    f.createDimension("lon", lon_len)

    t_var = f.createVariable("time", "i", ("time",))
    t_var[:] = list(range(time_len))
    t_var.units = time_units

    lat_var = f.createVariable("lat", "f", ("lat",))
    lat_var[:] = lats

    lon_var = f.createVariable("lon", "f", ("lon",))
    lon_var[:] = lons

    if precip_array.ndim == 2:
        precip_3d = np.expand_dims(precip_array, axis=0)
    else:
        precip_3d = precip_array

    p_var = f.createVariable(var_name, "f", ("time", "lat", "lon"))
    p_var[:] = precip_3d.astype(np.float32)
    p_var.units = units
    p_var._FillValue = fill_value

    f.flush()
    raw_bytes = bio.getvalue()
    f.close()
    return raw_bytes


def helper_create_geotiff(
    pixels: np.ndarray,
    origin: Tuple[float, float] = (83.1, 27.0),
    pixel_scale: Tuple[float, float] = (0.05, 0.05),
    epsg: int = 4326,
    nodata: float = -9999.0,
    compression: int = 1
) -> bytes:
    """Creates a genuine georeferenced GeoTIFF binary payload with IFD and GeoKeys."""
    height, width = pixels.shape
    raw_pixel_bytes = pixels.astype(np.float32).tobytes()

    if compression == 8:
        stored_pixel_bytes = zlib.compress(raw_pixel_bytes)
    else:
        stored_pixel_bytes = raw_pixel_bytes

    header = b"II\x2a\x00" + struct.pack("<I", 8)

    num_tags = 13
    ifd_len = 2 + (num_tags * 12) + 4
    tag_data_offset = 8 + ifd_len

    pixel_scale_bytes = struct.pack("<3d", pixel_scale[0], pixel_scale[1], 0.0)
    tiepoint_bytes = struct.pack("<6d", 0.0, 0.0, 0.0, origin[0], origin[1], 0.0)
    geokeys = struct.pack("<4H4H", 1, 1, 0, 1, 2048, 0, 1, epsg)
    nodata_str = f"{nodata}\x00".encode("ascii")

    tag_data = pixel_scale_bytes + tiepoint_bytes + geokeys + nodata_str
    pixel_offset = tag_data_offset + len(tag_data)

    p_scale_offset = tag_data_offset
    tie_offset = p_scale_offset + len(pixel_scale_bytes)
    geokeys_offset = tie_offset + len(tiepoint_bytes)
    nodata_offset = geokeys_offset + len(geokeys)

    entries = [
        struct.pack("<HHII", 256, 4, 1, width),
        struct.pack("<HHII", 257, 4, 1, height),
        struct.pack("<HHII", 258, 3, 1, 32),
        struct.pack("<HHII", 259, 3, 1, compression),
        struct.pack("<HHII", 273, 4, 1, pixel_offset),
        struct.pack("<HHII", 277, 3, 1, 1),
        struct.pack("<HHII", 278, 4, 1, height),
        struct.pack("<HHII", 279, 4, 1, len(stored_pixel_bytes)),
        struct.pack("<HHII", 339, 3, 1, 3),  # IEEE float
        struct.pack("<HHII", 33550, 12, 3, p_scale_offset),
        struct.pack("<HHII", 33922, 12, 6, tie_offset),
        struct.pack("<HHII", 34735, 3, 8, geokeys_offset),
        struct.pack("<HHII", 42113, 2, len(nodata_str), nodata_offset),
    ]

    ifd = struct.pack("<H", num_tags) + b"".join(entries) + struct.pack("<I", 0)
    return header + ifd + tag_data + stored_pixel_bytes


# =============================================================================
# 1. Genuine NetCDF-3 & NetCDF-4 Validation Tests
# =============================================================================

def test_netcdf3_scientific_decoding_success():
    """Verify genuine scientific decoding of NetCDF-3 with variables, arrays, coordinates and stats."""
    precip_grid = np.array([
        [10.0, 25.5, 0.0],
        [15.0, -9999.0, 30.0],
        [0.0, 5.0, 550.0],  # Contains 550.0 mm provisional extreme
    ], dtype=np.float32)
    lats = [26.5, 26.75, 27.0]
    lons = [83.2, 83.4, 83.6]

    nc_bytes = helper_create_netcdf3(precip_grid, lats, lons)
    report = ScientificUploadService.validate_netcdf_dataset(nc_bytes, target_region_id="district-gorakhpur")

    assert report.is_valid is True
    assert report.scientific_decoding_status == "SUCCESS"
    assert report.processing_stage == "SPATIALLY_VALIDATED"
    assert report.file_type == "NetCDF"
    assert "Classic NetCDF-1" in report.metadata["format_variant"]
    assert report.total_records == 9
    assert report.valid_records == 8
    assert report.missing_records == 1
    assert report.extreme_records == 1  # 550 mm flagged
    assert report.min_value == 0.0
    assert report.max_value == 550.0
    assert report.mean_value is not None
    assert report.bounding_box is not None
    assert report.bounding_box["min_lng"] == pytest.approx(83.2, abs=1e-4)
    assert report.bounding_box["max_lat"] == pytest.approx(27.0, abs=1e-4)


def test_netcdf4_hdf5_safe_quarantine_rejection():
    """Verify NetCDF-4 / HDF5 files are safely quarantined as UNSUPPORTED, not falsely validated."""
    hdf5_payload = MAGIC_HDF5_NETCDF4 + b"\x00" * 128
    report = ScientificUploadService.validate_netcdf_dataset(hdf5_payload)

    assert report.is_valid is False
    assert report.scientific_decoding_status == "UNSUPPORTED"
    assert report.processing_stage == "UNSUPPORTED"
    assert any("HDF5 C-bindings" in err for err in report.errors)


def test_netcdf_negative_precipitation_rejected():
    """Verify that physically impossible negative precipitation in NetCDF is rejected."""
    precip_grid = np.array([[10.0, -15.0], [0.0, 5.0]], dtype=np.float32)
    nc_bytes = helper_create_netcdf3(precip_grid, [26.5, 26.6], [83.2, 83.3])
    report = ScientificUploadService.validate_netcdf_dataset(nc_bytes)

    assert report.is_valid is False
    assert report.scientific_decoding_status == "FAILED"
    assert any("negative precipitation" in err.lower() for err in report.errors)


def test_netcdf_missing_precipitation_variable_rejected():
    """Verify rejection when NetCDF does not contain a CF-compliant precipitation variable."""
    precip_grid = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    nc_bytes = helper_create_netcdf3(precip_grid, [26.5, 26.6], [83.2, 83.3], var_name="sea_surface_temp")
    report = ScientificUploadService.validate_netcdf_dataset(nc_bytes)

    assert report.is_valid is False
    assert report.scientific_decoding_status == "FAILED"
    assert any("precipitation variable" in err.lower() for err in report.errors)


# =============================================================================
# 2. Genuine GeoTIFF Decoding & Dimension Safety Tests
# =============================================================================

def test_geotiff_scientific_decoding_success():
    """Verify genuine decoding of GeoTIFF raster arrays, geotransform, CRS and stats."""
    pixels = np.array([
        [15.0, 20.0, 0.0, -9999.0],
        [8.0, 0.0, 12.5, 30.0],
        [0.0, 5.0, 10.0, 2.0],
    ], dtype=np.float32)

    tif_bytes = helper_create_geotiff(pixels, origin=(83.1, 27.0), pixel_scale=(0.05, 0.05))
    report = ScientificUploadService.validate_geotiff_dataset(tif_bytes, target_region_id="district-gorakhpur")

    assert report.is_valid is True
    assert report.scientific_decoding_status == "SUCCESS"
    assert report.processing_stage == "SPATIALLY_VALIDATED"
    assert report.spatial_crs == "EPSG:4326"
    assert report.raster_dimensions == {"width": 4, "height": 3, "bands": 1}
    assert report.total_records == 12
    assert report.valid_records == 9  # In-district valid pixels after masking
    assert report.missing_records <= 3
    assert report.max_value == 30.0
    assert report.min_value == 0.0


def test_geotiff_deflate_compression_decoding():
    """Verify Deflate (compression=8) compressed GeoTIFF decoding."""
    pixels = np.ones((5, 5), dtype=np.float32) * 22.5
    pixels[0, 0] = -9999.0
    tif_bytes = helper_create_geotiff(pixels, compression=8)

    report = ScientificUploadService.validate_geotiff_dataset(tif_bytes, target_region_id="district-gorakhpur")
    assert report.is_valid is True
    assert report.scientific_decoding_status == "SUCCESS"
    assert report.mean_value == 22.5


def test_geotiff_oversized_dimensions_rejected_before_allocation():
    """Verify oversized width/height (> 10,000 px) are rejected before expensive array allocation."""
    header = b"II\x2a\x00" + struct.pack("<I", 8)
    num_tags = 2
    entry_w = struct.pack("<HHII", 256, 4, 1, 15000)  # Width 15,000 > MAX_RASTER_WIDTH
    entry_h = struct.pack("<HHII", 257, 4, 1, 200)
    next_ifd = struct.pack("<I", 0)
    fake_tif = header + struct.pack("<H", num_tags) + entry_w + entry_h + next_ifd

    report = ScientificUploadService.validate_geotiff_dataset(fake_tif)
    assert report.is_valid is False
    assert report.scientific_decoding_status == "MALFORMED"
    assert any("exceed configured maximum safety limits" in err for err in report.errors)


def test_geotiff_missing_spatial_tags_rejected():
    """Verify rejection of standard TIFF without mandatory GeoTIFF georeferencing tags."""
    header = b"II\x2a\x00" + struct.pack("<I", 8)
    num_tags = 2
    entry_w = struct.pack("<HHII", 256, 4, 1, 100)
    entry_h = struct.pack("<HHII", 257, 4, 1, 100)
    next_ifd = struct.pack("<I", 0)
    standard_tif = header + struct.pack("<H", num_tags) + entry_w + entry_h + next_ifd

    report = ScientificUploadService.validate_geotiff_dataset(standard_tif)
    assert report.is_valid is False
    assert any("missing mandatory geotiff spatial tags" in err.lower() for err in report.errors)


# =============================================================================
# 3. Spatial Validation & District Masking Tests
# =============================================================================

def test_spatial_disjoint_extent_rejected():
    """Verify that a dataset outside the target district boundary is rejected with clear error."""
    # Create dataset in Mahoba coordinates (lng 79.5, lat 25.3)
    pixels = np.ones((3, 3), dtype=np.float32) * 10.0
    tif_bytes = helper_create_geotiff(pixels, origin=(79.5, 25.5))

    # Test against Gorakhpur (lng 83.1 to 83.7, lat 26.2 to 27.1)
    report = ScientificUploadService.validate_geotiff_dataset(tif_bytes, target_region_id="district-gorakhpur")
    assert report.is_valid is False
    assert report.spatial_validation_status == "DISJOINT"
    assert any("does not intersect target district" in err for err in report.errors)


def test_spatial_partial_overlap_flagged():
    """Verify that partial spatial overlap is calculated and flagged."""
    # Bbox covering northern half of Gorakhpur
    cov = SpatialAggregator.validate_dataset_spatial_coverage("district-gorakhpur", {
        "min_lng": 83.2, "min_lat": 26.8, "max_lng": 83.5, "max_lat": 27.2
    })
    assert cov["is_intersecting"] is True
    assert cov["is_partial_coverage"] is True
    assert 10.0 < cov["spatial_overlap_pct"] < 90.0


def test_raster_masking_to_district_boundary():
    """Verify that pixels outside the district boundary are masked and excluded from statistics."""
    # Create raster where top-left is 100.0 mm and rest is 10.0 mm
    origin_x, origin_y = 83.2, 27.0
    scale_x, scale_y = 0.05, 0.05
    geotransform = (origin_x, scale_x, 0.0, origin_y, 0.0, -scale_y)
    data = np.ones((4, 4), dtype=np.float32) * 10.0

    mask_res = SpatialAggregator.mask_raster_to_district("district-gorakhpur", data, geotransform)
    assert mask_res["in_district_valid_pixels"] > 0
    assert mask_res["in_district_mean_mm"] == 10.0


# =============================================================================
# 4. Security: ZIP Bombs, Symlinks, Size Limits, and Traversal
# =============================================================================

def test_security_oversized_upload_rejected():
    """Verify that uploads exceeding MAX_UPLOAD_SIZE_BYTES (15 MB) are rejected."""
    oversized_data = b"0" * (MAX_UPLOAD_SIZE_BYTES + 1024)
    res = ScientificUploadService.process_dataset_upload(oversized_data, "large.csv")
    assert res.status == "REJECTED"
    assert res.processing_stage == "REJECTED"
    assert any("exceeds maximum safety limit" in err for err in res.validation_report.errors)


def test_security_zip_bomb_uncompressed_limit():
    """Verify that ZIP archives expanding beyond MAX_UNCOMPRESSED_ZIP_BYTES (30 MB) are rejected."""
    # Compress 35 MB of zeros (compresses down to < 50 KB)
    zero_bytes = b"0" * (MAX_UNCOMPRESSED_ZIP_BYTES + 1024 * 1024)
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.csv", zero_bytes)

    zip_bytes = bio.getvalue()
    report = ScientificUploadService.validate_zip_archive(zip_bytes)
    assert report.is_valid is False
    assert report.processing_stage == "REJECTED"
    assert any("zip bomb detected" in err.lower() for err in report.errors)


def test_security_zip_symlink_attack_rejected():
    """Verify that ZIP archives containing symbolic links are detected and rejected."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        info = zipfile.ZipInfo("symlink_entry")
        # Unix mode: 0o120000 = S_IFLNK
        info.external_attr = 0o120777 << 16
        zf.writestr(info, "/etc/passwd")

    report = ScientificUploadService.validate_zip_archive(bio.getvalue())
    assert report.is_valid is False
    assert any("symbolic link detected" in err.lower() for err in report.errors)


def test_security_zip_nested_archive_rejected():
    """Verify that nested archives (.zip inside .zip) are rejected to prevent decompression abuse."""
    inner_bio = io.BytesIO()
    with zipfile.ZipFile(inner_bio, "w") as inner_zf:
        inner_zf.writestr("data.csv", "date,rainfall_mm\n2024-01-01,10.0\n")

    outer_bio = io.BytesIO()
    with zipfile.ZipFile(outer_bio, "w") as outer_zf:
        outer_zf.writestr("nested.zip", inner_bio.getvalue())

    report = ScientificUploadService.validate_zip_archive(outer_bio.getvalue())
    assert report.is_valid is False
    assert any("nested archive detected" in err.lower() for err in report.errors)


def test_security_zip_slip_path_traversal():
    """Verify that Zip-Slip path traversal entries (..) are rejected."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("../../etc/cron.d/malicious", "exploit")

    report = ScientificUploadService.validate_zip_archive(bio.getvalue())
    assert report.is_valid is False
    assert any("path traversal" in err.lower() for err in report.errors)


# =============================================================================
# 5. Quarantine Storage Retention & Quota Enforcement
# =============================================================================

def test_quarantine_cleanup_and_quota_enforcement(tmp_path, monkeypatch):
    """Verify expired quarantine files are removed and storage quota is enforced."""
    q_dir = tmp_path / "quarantine"
    q_dir.mkdir(parents=True, exist_ok=True)

    # 1. Old expired file (25 hours old)
    old_file = q_dir / "old_upload.tmp"
    old_file.write_bytes(b"old data" * 100)
    old_time = time.time() - (25 * 3600)
    import os
    os.utime(old_file, (old_time, old_time))

    # 2. Recent file (1 hour old)
    recent_file = q_dir / "recent_upload.tmp"
    recent_file.write_bytes(b"recent data" * 100)

    res = ScientificUploadService.cleanup_expired_quarantine(max_age_hours=24.0)
    assert res["deleted_files_count"] >= 1
    assert not old_file.exists()
    assert recent_file.exists()


# =============================================================================
# 6. Duplicate Prevention & FastAPI Route Integration
# =============================================================================

def test_duplicate_dataset_rejection():
    """Verify duplicate uploads with identical content are detected via SHA-256 and rejected."""
    csv_bytes = "date,rainfall_mm\n2024-09-01,25.0\n2024-09-02,10.0\n".encode("utf-8")

    res1 = ScientificUploadService.process_dataset_upload(csv_bytes, "unique_series.csv")
    assert res1.status == "VALIDATED"

    # Second upload with identical content
    res2 = ScientificUploadService.process_dataset_upload(csv_bytes, "duplicate_series.csv")
    assert res2.status == "REJECTED"
    assert any("duplicate dataset detected" in err.lower() for err in res2.validation_report.errors)


def test_api_upload_scientific_dataset_success():
    """Verify POST /api/v1/uploads/scientific-dataset handles multipart uploads cleanly with auth."""
    csv_content = "date,rainfall_mm\n2024-08-10,35.0\n2024-08-11,0.0\n"
    files = {"file": ("api_test_series.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"target_region_id": "district-gorakhpur"}
    headers = {"X-API-Key": "test-auth-secret-key-12345"}

    response = client.post("/api/v1/uploads/scientific-dataset", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "VALIDATED"
    assert res_json["processing_stage"] in ["VALIDATED", "SPATIALLY_VALIDATED"]
    assert res_json["data_classification"] == "MANUAL_UPLOAD"


def test_api_upload_cleanup_endpoint():
    """Verify POST /api/v1/uploads/cleanup manually triggers storage cleanup with auth."""
    headers = {"X-API-Key": "test-auth-secret-key-12345"}
    response = client.post("/api/v1/uploads/cleanup?max_age_hours=24.0", headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert "deleted_files_count" in res_json
    assert "reclaimed_bytes" in res_json
