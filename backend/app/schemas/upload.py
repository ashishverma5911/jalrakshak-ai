"""
Pydantic Schemas for Manual Scientific Dataset Uploads and Validation
Defines transparent scientific decoding states, spatial validation metrics,
and data provenance classifications for JalRakshak AI.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    """Detailed scientific content and structural validation audit."""
    is_valid: bool
    file_type: str = Field(..., description="Detected format: CSV, NetCDF, GeoTIFF, or ZIP")
    mime_detected: str
    file_size_bytes: int
    sha256_hash: str
    target_region_id: Optional[str] = Field(None, description="Target district ID, e.g. district-gorakhpur")
    data_mode: str = Field("MANUAL_UPLOAD", description="Provenance data mode")
    data_classification: str = Field(
        "MANUAL_UPLOAD",
        description="IN_SITU_GROUND_TRUTH, SATELLITE_DERIVED_OR_BLENDED, MODELLED_OR_REANALYSIS, MANUAL_UPLOAD, DEMONSTRATION"
    )
    processing_stage: str = Field(
        "STRUCTURE_VALIDATED",
        description="STRUCTURE_VALIDATED, SCIENTIFICALLY_DECODED, SPATIALLY_VALIDATED, VERIFIED_REAL, REJECTED, UNSUPPORTED, QUARANTINED"
    )
    scientific_decoding_status: str = Field(
        "SUCCESS",
        description="SUCCESS, FAILED, UNSUPPORTED, or NOT_DECODED"
    )
    spatial_validation_status: str = Field(
        "NOT_PERFORMED",
        description="VALIDATED, PARTIAL_OVERLAP, DISJOINT, or NOT_PERFORMED"
    )
    spatial_overlap_pct: Optional[float] = Field(None, description="Percentage of district boundary covered by dataset")
    spatial_crs: Optional[str] = Field(None, description="Coordinate Reference System, e.g. EPSG:4326")
    spatial_coverage_status: Optional[str] = Field(None, description="Coverage summary against target district polygon")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="min_lng, min_lat, max_lng, max_lat")
    raster_dimensions: Optional[Dict[str, int]] = Field(None, description="width, height, bands")
    temporal_semantics: Optional[str] = Field(None, description="daily_accumulation, half_hourly_rate, etc.")
    uncompressed_bytes: Optional[int] = None
    compression_ratio: Optional[float] = None
    total_records: int = 0
    valid_records: int = 0
    missing_records: int = 0
    extreme_records: int = 0
    date_range: Optional[Dict[str, str]] = None
    mean_value: Optional[float] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DatasetUploadResponse(BaseModel):
    """Response returned upon uploading and inspecting a scientific dataset."""
    upload_id: str
    filename: str
    status: str = Field(..., description="VALIDATED, REJECTED, QUARANTINED, or UNSUPPORTED")
    processing_stage: str
    data_classification: str
    message: str
    validation_report: ValidationReport
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UploadHistoryItem(BaseModel):
    """Historical summary of an uploaded scientific dataset."""
    upload_id: str
    filename: str
    file_type: str
    target_region_id: Optional[str]
    records_count: int
    status: str
    processing_stage: str = "VALIDATED"
    data_classification: str = "MANUAL_UPLOAD"
    spatial_overlap_pct: Optional[float] = None
    file_size_bytes: int
    uploaded_at: str
