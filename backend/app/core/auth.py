"""
JalRakshak AI — Backend API Authentication & Authorization
Secures sensitive scientific dataset ingestion, upload history, and quarantine storage operations.
"""

import os
import secrets
import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from .config import UPLOAD_API_KEY

logger = logging.getLogger("jalrakshak.auth")

# FastAPI OpenAPI security schemes for interactive documentation
api_key_header_scheme = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Backend Upload API Key passed via X-API-Key header"
)
http_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Backend Upload API Key passed via Authorization: Bearer <key>"
)


def get_configured_upload_api_key() -> str:
    """
    Retrieves the configured secret key from the backend environment.
    Supports UPLOAD_API_KEY and fallback ADMIN_API_KEY.
    """
    key = os.getenv("UPLOAD_API_KEY", "").strip() or os.getenv("ADMIN_API_KEY", "").strip()
    if not key and UPLOAD_API_KEY:
        key = UPLOAD_API_KEY.strip()
    return key


def verify_api_key(provided_key: str, configured_key: str) -> bool:
    """
    Performs constant-time string comparison to prevent timing side-channel attacks.
    """
    if not provided_key or not configured_key:
        return False
    return secrets.compare_digest(provided_key, configured_key)


async def require_upload_auth(
    request: Request,
    header_key: Optional[str] = Depends(api_key_header_scheme),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_scheme),
) -> str:
    """
    FastAPI security dependency protecting dataset uploads, history inspection, and cleanup.
    
    Accepts credentials via either:
    - 'X-API-Key: <secret>'
    - 'Authorization: Bearer <secret>'
    
    Enforces:
    1. Rejection of missing credentials (401 Unauthorized)
    2. Rejection of malformed authorization schemes or empty keys (401 Unauthorized)
    3. Server-side key configuration verification (500 Internal Server Error if unconfigured)
    4. Constant-time secret comparison (401 Unauthorized if invalid)
    """
    raw_api_key = request.headers.get("X-API-Key")
    raw_auth = request.headers.get("Authorization")

    token: Optional[str] = None

    # 1. Parse and extract token from X-API-Key or Authorization header
    if raw_api_key is not None:
        stripped_key = raw_api_key.strip()
        if not stripped_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed X-API-Key header. Key cannot be empty.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = stripped_key
    elif raw_auth is not None:
        parts = raw_auth.strip().split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed Authorization header. Format must be 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1].strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API authentication credentials. Provide 'X-API-Key' or 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verify server-side secret configuration
    configured_key = get_configured_upload_api_key()
    if not configured_key:
        logger.error("Upload API authentication failed: UPLOAD_API_KEY is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Upload API authentication key is not configured in backend environment."
        )

    # 3. Constant-time credential verification
    if not verify_api_key(token, configured_key):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(f"Unauthorized upload access attempt rejected from client IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
