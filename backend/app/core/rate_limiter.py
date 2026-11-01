"""
JalRakshak AI — In-Memory Sliding Window API Rate Limiter
Protects sensitive scientific upload and quarantine management endpoints against volumetric abuse.

Architectural Notice:
This rate limiter operates in-memory for single-process deployments (suitable for prototype and 512 MB instances).
State is not shared across multi-worker Uvicorn processes or container restarts.
For clustered multi-node production deployments, attach an external Redis backend or API gateway proxy.
"""

import time
import threading
import logging
from collections import defaultdict, deque
from typing import Dict, Deque
from fastapi import Request, HTTPException, status

logger = logging.getLogger("jalrakshak.rate_limiter")


class InMemoryRateLimiter:
    """
    Thread-safe sliding window rate limiter by client IP.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        action_name: str = "request",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.action_name = action_name
        self._history: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _resolve_client_ip(self, request: Request) -> str:
        """
        Safely resolves client IP address.
        Security Policy:
        - Prioritizes direct socket connection from request.client.host.
        - If request.client.host is within configured TRUSTED_PROXIES and TRUST_PROXY_HEADERS is enabled,
          safely extracts the genuine client IP from X-Forwarded-For.
        - Arbitrary X-Forwarded-For headers from untrusted connections are rejected to prevent header spoofing.
        """
        from .config import TRUSTED_PROXIES, TRUST_PROXY_HEADERS

        direct_host = request.client.host if request.client and request.client.host else "127.0.0.1"

        if TRUST_PROXY_HEADERS and (direct_host in TRUSTED_PROXIES or "*" in TRUSTED_PROXIES):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Leftmost IP represents the client originating the request
                ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
                if ips:
                    return ips[0]

        return direct_host

    def check(self, request: Request) -> None:
        """
        Checks rate limit for incoming request.
        Raises HTTP 429 Too Many Requests if rate limit is exceeded.
        """
        client_ip = self._resolve_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._history[client_ip]

            # Evict timestamps outside sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(cutoff - oldest + self.window_seconds))
                logger.warning(
                    f"Rate limit exceeded for {self.action_name} from IP {client_ip}. "
                    f"Count: {len(timestamps)}/{self.max_requests} in {self.window_seconds}s. Retry-After: {retry_after}s"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {self.action_name}. Maximum {self.max_requests} requests per {int(self.window_seconds)}s.",
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

    def reset(self) -> None:
        """Clears all stored rate limit history (primarily for test isolation)."""
        with self._lock:
            self._history.clear()


# Pre-configured Limiters for Upload Endpoints
# 1. Dataset Uploads: max 10 requests per 60 seconds per IP
upload_limiter = InMemoryRateLimiter(
    max_requests=10,
    window_seconds=60.0,
    action_name="dataset uploads",
)

# 2. Quarantine Cleanup: max 3 requests per 60 seconds per IP (stricter limit for destructive operation)
cleanup_limiter = InMemoryRateLimiter(
    max_requests=3,
    window_seconds=60.0,
    action_name="storage cleanup",
)


def rate_limit_upload(request: Request) -> None:
    """FastAPI dependency enforcing upload endpoint rate limiting."""
    upload_limiter.check(request)


def rate_limit_cleanup(request: Request) -> None:
    """FastAPI dependency enforcing cleanup endpoint rate limiting."""
    cleanup_limiter.check(request)
