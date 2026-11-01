"""
FastAPI Routes for Secure Scientific Dataset Uploads and Validation History
Enforces chunked streaming, concurrency bounding, and quarantine retention management.
"""

import uuid
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from ..core.auth import require_upload_auth
from ..core.rate_limiter import rate_limit_upload, rate_limit_cleanup
from ..schemas.upload import DatasetUploadResponse, UploadHistoryItem
from ..services.upload_service import (
    ScientificUploadService,
    MAX_UPLOAD_SIZE_BYTES,
    SPOOL_DIR,
)

logger = logging.getLogger("jalrakshak.api.uploads")

router = APIRouter(
    prefix="/uploads",
    tags=["Scientific Data Uploads"],
    dependencies=[Depends(require_upload_auth)],
)

# Max concurrent heavy scientific decoding jobs on 512 MB RAM instance
_upload_semaphore = asyncio.Semaphore(1)


@router.post("/scientific-dataset", response_model=DatasetUploadResponse, dependencies=[Depends(rate_limit_upload)])
async def upload_scientific_dataset(
    file: UploadFile = File(..., description="Scientific dataset: CSV, NetCDF (.nc), GeoTIFF (.tif), or ZIP"),
    target_region_id: Optional[str] = Form(None, description="Optional target district (e.g. district-gorakhpur)"),
    auth: str = Depends(require_upload_auth),
) -> DatasetUploadResponse:
    """
    POST /api/v1/uploads/scientific-dataset
    Streams, validates, scientifically decodes, and quarantines incoming datasets.
    Enforces chunked streaming to temporary spool storage before reading to prevent heap exhaustion.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    # 1. Bounded chunked streaming to temporary spool file
    spool_id = f"spool_{uuid.uuid4().hex[:12]}"
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    spool_path = SPOOL_DIR / f"{spool_id}.tmp"

    total_bytes = 0
    try:
        with open(spool_path, "wb") as f_out:
            while chunk := await file.read(65536):  # 64 KB chunks
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload safety threshold ({MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB)."
                    )
                f_out.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        # 2. Concurrency-bounded scientific processing
        async with _upload_semaphore:
            with open(spool_path, "rb") as f_in:
                file_bytes = f_in.read()

            response = await asyncio.to_thread(
                ScientificUploadService.process_dataset_upload,
                file_bytes=file_bytes,
                filename=file.filename,
                target_region_id=target_region_id,
            )
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing scientific dataset upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing dataset upload: {str(e)}"
        )
    finally:
        # Guaranteed cleanup of ephemeral spool file
        if spool_path.exists():
            try:
                spool_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove spool file {spool_path.name}: {e}")


@router.get("/history", response_model=List[UploadHistoryItem])
def get_upload_history(
    auth: str = Depends(require_upload_auth),
) -> List[UploadHistoryItem]:
    """
    GET /api/v1/uploads/history
    Returns chronological registry of uploaded scientific datasets with processing status.
    Requires authentication.
    """
    raw_history = ScientificUploadService.load_registry()
    items = []
    for r in raw_history:
        items.append(
            UploadHistoryItem(
                upload_id=r.get("upload_id", "unknown"),
                filename=r.get("filename", "unknown"),
                file_type=r.get("file_type", "UNKNOWN"),
                target_region_id=r.get("target_region_id"),
                records_count=r.get("records_count", 0),
                status=r.get("status", "UNKNOWN"),
                processing_stage=r.get("processing_stage", "VALIDATED"),
                data_classification=r.get("data_classification", "MANUAL_UPLOAD"),
                spatial_overlap_pct=r.get("spatial_overlap_pct"),
                file_size_bytes=r.get("file_size_bytes", 0),
                uploaded_at=r.get("uploaded_at", ""),
            )
        )
    return items


@router.post("/cleanup", dependencies=[Depends(rate_limit_cleanup)])
def trigger_quarantine_cleanup(
    max_age_hours: float = 24.0,
    auth: str = Depends(require_upload_auth),
) -> Dict[str, Any]:
    """
    POST /api/v1/uploads/cleanup
    Manually triggers quarantine file expiration and quota enforcement.
    Requires authentication and is rate-limited.
    """
    return ScientificUploadService.cleanup_expired_quarantine(max_age_hours=max_age_hours)
