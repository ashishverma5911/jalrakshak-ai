"""
Scientific Source Adapter Registry for JalRakshak AI
Provides centralized discovery, metadata inspection, and connection auditing
for all onboarded scientific environmental data adapters.
"""

import logging
from typing import Dict, Any, List, Type, Optional
from datetime import datetime, timezone

from .base import (
    ScientificSourceAdapter,
    AdapterMetadata,
    AdapterError,
)
from .chirps import CHIRPSAdapter
from .gpm_imerg import GPMIMERGAdapter
from .open_meteo import OpenMeteoAdapter
from .srtm import SRTMAdapter

logger = logging.getLogger("jalrakshak.pipeline.adapter.registry")


class ScientificSourceRegistry:
    """
    Central catalog and lifecycle coordinator for scientific data source adapters.
    """

    _registry: Dict[str, Type[ScientificSourceAdapter]] = {
        "chirps_daily": CHIRPSAdapter,
        "nasa_gpm_imerg": GPMIMERGAdapter,
        "open_meteo_archive": OpenMeteoAdapter,
        "nasa_srtm_30m": SRTMAdapter,
    }

    @classmethod
    def register(cls, source_id: str, adapter_cls: Type[ScientificSourceAdapter]) -> None:
        """Dynamically registers a new scientific data adapter."""
        cls._registry[source_id.lower().strip()] = adapter_cls
        logger.info(f"Registered scientific source adapter: {source_id}")

    @classmethod
    def get_adapter(cls, source_id: str) -> Type[ScientificSourceAdapter]:
        """Retrieves adapter class by source identifier. Raises KeyError if unknown."""
        key = source_id.lower().strip()
        if key not in cls._registry:
            raise KeyError(
                f"Unknown scientific source adapter '{source_id}'. "
                f"Available adapters: {list(cls._registry.keys())}"
            )
        return cls._registry[key]

    @classmethod
    def list_adapters(cls) -> List[AdapterMetadata]:
        """Returns metadata for all registered adapters."""
        return [adapter.get_metadata() for adapter in cls._registry.values()]

    @classmethod
    async def check_all_connections(cls) -> Dict[str, Any]:
        """
        Runs connection verification across all registered adapters in parallel.
        Returns aggregated health report.
        """
        import asyncio

        tasks = []
        source_keys = list(cls._registry.keys())

        for key in source_keys:
            adapter = cls._registry[key]
            tasks.append(adapter.check_connection())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        report: Dict[str, Any] = {
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "total_adapters": len(source_keys),
            "sources": {},
        }

        for key, res in zip(source_keys, results):
            if isinstance(res, Exception):
                report["sources"][key] = {
                    "source_id": key,
                    "status": "error",
                    "error": str(res),
                }
            else:
                report["sources"][key] = res

        return report
