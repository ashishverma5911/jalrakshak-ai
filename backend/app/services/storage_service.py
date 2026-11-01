"""
JalRakshak AI — Scientific Storage Abstraction Layer
Provides modular storage backend interfaces for temporary spool, quarantine, verified datasets,
and processed scientific outputs.

Architectural Notice:
Current implementation defaults to LocalStorageBackend (EPHEMERAL_LOCAL on free tier container hosts).
Designed to allow drop-in persistent object storage (e.g. AWS S3, Google Cloud Storage, or MinIO)
without altering the core scientific validation or risk engine pipelines.
"""

import time
import shutil
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("jalrakshak.services.storage")


class StorageTier(str, Enum):
    TEMPORARY_SPOOL = "spool"
    QUARANTINE = "quarantine"
    VERIFIED_DATASET = "verified"
    PROCESSED_OUTPUT = "processed"


class StorageDurability(str, Enum):
    EPHEMERAL_LOCAL = "EPHEMERAL_LOCAL"
    EPHEMERAL_DEMO = "EPHEMERAL_DEMO"
    DURABLE_OBJECT_STORE = "DURABLE_OBJECT_STORE"


class ScientificStorageBackend(ABC):
    """Abstract interface for environmental scientific dataset storage."""

    @abstractmethod
    def store(self, tier: StorageTier, filename: str, data: bytes) -> Path:
        """Stores binary payload in the specified storage tier."""
        pass

    @abstractmethod
    def retrieve(self, tier: StorageTier, filename: str) -> bytes:
        """Retrieves binary payload from the specified storage tier."""
        pass

    @abstractmethod
    def delete(self, tier: StorageTier, filename: str) -> bool:
        """Deletes file from the specified storage tier."""
        pass

    @abstractmethod
    def list_files(self, tier: StorageTier) -> List[Path]:
        """Lists files residing in the specified storage tier."""
        pass

    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Returns storage metrics and durability classification."""
        pass

    @abstractmethod
    def cleanup_expired_quarantine(
        self,
        max_age_hours: float,
        max_storage_quota_bytes: int,
    ) -> Dict[str, Any]:
        """Idempotently purges expired quarantine and spool artifacts."""
        pass


class LocalStorageBackend(ScientificStorageBackend):
    """
    Default local filesystem storage backend.
    Enforces strict path-traversal boundaries and quota management.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.tier_dirs: Dict[StorageTier, Path] = {
            StorageTier.TEMPORARY_SPOOL: self.root_dir / StorageTier.TEMPORARY_SPOOL.value,
            StorageTier.QUARANTINE: self.root_dir / StorageTier.QUARANTINE.value,
            StorageTier.VERIFIED_DATASET: self.root_dir / StorageTier.VERIFIED_DATASET.value,
            StorageTier.PROCESSED_OUTPUT: self.root_dir / StorageTier.PROCESSED_OUTPUT.value,
        }
        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Ensures all tier storage directories exist."""
        for d in self.tier_dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, tier: StorageTier, filename: str) -> Path:
        """Guarantees that resolved path cannot escape tier directory."""
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(f"Path traversal detected: {filename} contains invalid directory components.")
        target = (self.tier_dirs[tier] / filename).resolve()
        if not target.is_relative_to(self.tier_dirs[tier].resolve()):
            raise ValueError(f"Path traversal detected: {filename} escapes storage root.")
        return target

    def store(self, tier: StorageTier, filename: str, data: bytes) -> Path:
        self.ensure_directories()
        target = self._resolve_safe_path(tier, filename)
        with open(target, "wb") as f:
            f.write(data)
        return target

    def retrieve(self, tier: StorageTier, filename: str) -> bytes:
        target = self._resolve_safe_path(tier, filename)
        if not target.exists():
            raise FileNotFoundError(f"File '{filename}' not found in {tier.value} storage.")
        with open(target, "rb") as f:
            return f.read()

    def delete(self, tier: StorageTier, filename: str) -> bool:
        target = self._resolve_safe_path(tier, filename)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def list_files(self, tier: StorageTier) -> List[Path]:
        tdir = self.tier_dirs[tier]
        if not tdir.exists():
            return []
        return [p for p in tdir.glob("*") if p.is_file()]

    def get_storage_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "durability": StorageDurability.EPHEMERAL_LOCAL.value,
            "root_path": str(self.root_dir),
            "tier_file_counts": {},
            "tier_bytes": {},
            "total_storage_bytes": 0,
        }
        total_bytes = 0
        for tier, tdir in self.tier_dirs.items():
            if tdir.exists():
                files = [p for p in tdir.glob("*") if p.is_file()]
                bytes_count = sum(p.stat().st_size for p in files)
                stats["tier_file_counts"][tier.value] = len(files)
                stats["tier_bytes"][tier.value] = bytes_count
                total_bytes += bytes_count
            else:
                stats["tier_file_counts"][tier.value] = 0
                stats["tier_bytes"][tier.value] = 0

        stats["total_storage_bytes"] = total_bytes
        return stats

    def cleanup_expired_quarantine(
        self,
        max_age_hours: float,
        max_storage_quota_bytes: int,
    ) -> Dict[str, Any]:
        self.ensure_directories()
        now = time.time()
        max_age_sec = max_age_hours * 3600.0

        deleted_files = 0
        reclaimed_bytes = 0

        # 1. Clean expired quarantine files and spools
        for tier in [StorageTier.QUARANTINE, StorageTier.TEMPORARY_SPOOL]:
            tdir = self.tier_dirs[tier]
            if not tdir.exists():
                continue
            for file_path in tdir.glob("*"):
                if file_path.is_file():
                    try:
                        resolved = file_path.resolve()
                        if not resolved.is_relative_to(self.root_dir):
                            logger.error(f"Security: Refusing to unlink file outside storage root: {file_path}")
                            continue

                        mtime = file_path.stat().st_mtime
                        if (now - mtime) > max_age_sec:
                            size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files += 1
                            reclaimed_bytes += size
                    except Exception as e:
                        logger.warning(f"Failed to purge file {file_path.name}: {e}")

        # 2. Check total upload storage quota
        total_bytes = 0
        all_quarantine_files = []
        qdir = self.tier_dirs[StorageTier.QUARANTINE]
        if qdir.exists():
            for p in qdir.glob("*"):
                if p.is_file():
                    st = p.stat()
                    total_bytes += st.st_size
                    all_quarantine_files.append((st.st_mtime, st.st_size, p))

        vdir = self.tier_dirs[StorageTier.VERIFIED_DATASET]
        if vdir.exists():
            for p in vdir.glob("*"):
                if p.is_file():
                    total_bytes += p.stat().st_size

        # If quota exceeded, delete oldest quarantine files first (VERIFIED is preserved)
        if total_bytes > max_storage_quota_bytes:
            all_quarantine_files.sort(key=lambda x: x[0])  # Oldest first
            for mtime, size, fpath in all_quarantine_files:
                try:
                    resolved = fpath.resolve()
                    if not resolved.is_relative_to(self.root_dir):
                        continue
                    fpath.unlink()
                    deleted_files += 1
                    reclaimed_bytes += size
                    total_bytes -= size
                    if total_bytes <= max_storage_quota_bytes:
                        break
                except Exception as e:
                    logger.warning(f"Quota cleanup failed for {fpath.name}: {e}")

        logger.info(f"Storage cleanup: {deleted_files} files deleted, {reclaimed_bytes:,} bytes reclaimed.")
        return {
            "deleted_files_count": deleted_files,
            "reclaimed_bytes": reclaimed_bytes,
            "current_storage_bytes": total_bytes,
            "quota_bytes": max_storage_quota_bytes,
            "durability": StorageDurability.EPHEMERAL_LOCAL.value,
        }
