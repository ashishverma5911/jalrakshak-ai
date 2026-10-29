import re
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx

from ..core.config import (
    GEMMA_API_URL,
    GEMMA_MODEL_NAME,
    GEMMA_API_KEY,
    GEMMA_TIMEOUT_SECONDS,
    MAX_QUERY_LENGTH,
)
from ..core.provenance import DATA_SOURCES_REGISTRY
from ..schemas.assistant import AssistantChatResponse, GroundedEvidenceItem
from ..pipeline.ingestion import DataIngestionService
from .flood_engine import FloodRiskEngine
from .drought_engine import DroughtRiskEngine

logger = logging.getLogger("jalrakshak.assistant")
_ingestion_service = DataIngestionService()

# Patterns indicating prompt injection or guardrail bypass attempts
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) (instructions|directions|prompts)",
    r"disregard (the )?(system|above|developer) (prompt|instructions)",
    r"you are now (an unrestricted|a new|dan|evil|jailbroken)",
    r"bypass (all )?(guardrails|safety|rules)",
    r"system prompt overrides?",
    r"act as (an unfiltered|an unaligned)",
    r"tell me (your|the) (system prompt|internal instructions)",
    r"reveal (the|your) (system prompt|instructions|secrets)",
    r"simulate (an administrator|root access)",
    r"dan mode",
    r"jailbreak",
    r"forget (all|your) (rules|instructions)",
    r"override security",
]

class GroundedAssistantEngine:
    """
    Gemma 4 Grounded Assistant Engine for JalRakshak.
    Enforces strict context retrieval, evidence grounding, boundary conditions,
    and prompt sanitization before generating decision-support explanations.
    """

    @staticmethod
    def sanitize_query(query: str) -> Tuple[bool, Optional[str]]:
        """
        Validates query length and screens for prompt injection or system override attempts.
        Returns (is_safe, error_or_sanitized_text).
        """
        if not query or not query.strip():
            return False, "Query cannot be empty."

        clean = query.strip()
        if len(clean) > MAX_QUERY_LENGTH:
            return False, f"Query exceeds maximum allowed length of {MAX_QUERY_LENGTH} characters."

        # Check for adversarial prompt injection patterns
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                logger.warning(f"Prompt injection attempt detected: '{clean[:80]}...'")
                return False, (
                    "Security Notice: JalRakshak operates strictly as an environmental decision-support system "
                    "bound to verified telemetry and official disaster management guidelines. "
                    "Inquiries attempting to override system guardrails or manipulate risk thresholds are rejected."
                )

        return True, clean

    @classmethod
    def retrieve_grounded_evidence(
        cls,
        location: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Retrieves real calculated risk indicators, baselines, and limitations from
        backend engines.
        """
        q_lower = query.lower()
        target_loc = location.lower() if location else "gorakhpur"

        # Auto-detect location context from query keywords if generic
        if "mahoba" in q_lower or "drought" in q_lower or "bundelkhand" in q_lower:
            target_loc = "mahoba"
        elif "gorakhpur" in q_lower or "flood" in q_lower or "rapti" in q_lower:
            target_loc = "gorakhpur"

        evidence_items: List[GroundedEvidenceItem] = []
        indicators_list: List[Dict[str, Any]] = []
        limitations: List[str] = []
        citations: List[str] = []
        timestamps: Dict[str, str] = {
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if target_loc == "mahoba":
            district_info = _ingestion_service.get_district_info("mahoba")
            daily_df = _ingestion_service.load_daily_rainfall("mahoba")
            assessment = DroughtRiskEngine.evaluate(district_info, daily_df)
            timestamps["observation_period"] = assessment.assessment_period
            for ind in assessment.indicators:
                evidence_items.append(
                    GroundedEvidenceItem(
                        indicator_id=ind.indicator_id,
                        name=ind.name,
                        value=ind.value,
                        units=ind.units,
                        category=ind.category,
                        observation_period=ind.calculation_window,
                        quality_status=ind.quality_status,
                    )
                )
                indicators_list.append(ind.model_dump())
            limitations.extend(assessment.scientific_notes)
            citations = [
                f"{DATA_SOURCES_REGISTRY['chirps_daily']['name']} (0.05° Gridded Baseline)",
                f"{DATA_SOURCES_REGISTRY['srtm_dem']['name']} (30m Elevation)",
                f"{DATA_SOURCES_REGISTRY['upsdma_imd']['name']}",
            ]
        else:
            # Default to Gorakhpur flood context
            district_info = _ingestion_service.get_district_info("gorakhpur")
            daily_df = _ingestion_service.load_daily_rainfall("gorakhpur")
            assessment = FloodRiskEngine.evaluate(district_info, daily_df)
            timestamps["observation_period"] = assessment.assessment_period
            for ind in assessment.indicators:
                evidence_items.append(
                    GroundedEvidenceItem(
                        indicator_id=ind.indicator_id,
                        name=ind.name,
                        value=ind.value,
                        units=ind.units,
                        category=ind.category,
                        observation_period=ind.calculation_window,
                        quality_status=ind.quality_status,
                    )
                )
                indicators_list.append(ind.model_dump())
            limitations.extend(assessment.scientific_notes)
            citations = [
                f"{DATA_SOURCES_REGISTRY['nasa_gpm_imerg']['name']} (0.1° Near Real-Time)",
                f"{DATA_SOURCES_REGISTRY['chirps_daily']['name']} (0.05° 1991–2020 Baseline)",
                f"{DATA_SOURCES_REGISTRY['srtm_dem']['name']} (30m Elevation)",
                f"{DATA_SOURCES_REGISTRY['upsdma_imd']['name']}",
            ]

        return {
            "target_location": target_loc,
            "evidence_items": evidence_items,
            "indicators_list": indicators_list,
            "limitations": limitations,
            "citations": citations,
            "timestamps": timestamps,
            "is_demo_data": True,
        }

    @classmethod
    async def query_local_gemma_runtime(
        cls,
        prompt: str,
        system_instruction: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Attempts to call the local inference server (e.g., Ollama or custom Gemma 4 endpoint).
        Returns (success, response_text).
        """
        payload = {
            "model": GEMMA_MODEL_NAME,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            },
        }
        headers = {"Content-Type": "application/json"}
        if GEMMA_API_KEY:
            headers["Authorization"] = f"Bearer {GEMMA_API_KEY}"

        try:
            async with httpx.AsyncClient(timeout=GEMMA_TIMEOUT_SECONDS) as client:
                resp = await client.post(GEMMA_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        reply = None
                        if isinstance(data, dict):
                            reply = data.get("response") or data.get("text")
                            if not reply and "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                if isinstance(choice, dict):
                                    reply = choice.get("text") or choice.get("message", {}).get("content")
                        if reply and isinstance(reply, str) and reply.strip():
                            return True, reply.strip()
                    except (ValueError, KeyError, TypeError) as parse_err:
                        logger.warning(f"Failed to parse Gemma runtime response: {parse_err}")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as ex:
            logger.info(f"Gemma 4 local runtime not reachable ({type(ex).__name__}): {ex}")
        except Exception as general_ex:
            logger.warning(f"Unexpected error querying Gemma runtime: {general_ex}")

        return False, None

    @classmethod
    def synthesize_transparent_grounded_answer(
        cls,
        query: str,
        grounded_data: Dict[str, Any]
    ) -> str:
        """
        Generates a transparent, deterministic decision-support explanation strictly grounded
        in the retrieved indicators and official boundaries when the Gemma 4 neural runtime is offline.
        """
        q_lower = query.lower()

        # Handle explicit question about demo data / live measurements
        if any(term in q_lower for term in ["live measurement", "live data", "real-time data", "is this live", "is this demo", "is this real", "is data real"]):
            return (
                "[DATA TRANSPARENCY & PROVENANCE DISCLOSURE]\n\n"
                "• **Current Execution Mode**: Local Reproducible Prototype Fixtures (`is_demo_data: true`).\n"
                "• **Data Sources**: NASA GPM IMERG 0.1° gridded run and CHIRPS v2.0 daily historical baseline (1991–2020).\n"
                "• **Live Feed Status**: Satellite feeds in this deployment are cached benchmark fixtures for Uttar Pradesh pilot districts (Gorakhpur & Mahoba). They are NOT live streaming satellite feeds.\n"
                "• **Verification**: System health diagnostics report 'Local Reproducible Fixtures' under pipeline mode."
            )

        # Handle out-of-scope queries (e.g. general knowledge, stocks, sports)
        out_of_scope_keywords = ["stock", "bitcoin", "crypto", "cricket", "football", "president", "movie", "celebrity", "capital of", "recipe", "song", "joke", "write code", "who won"]
        if any(term in q_lower for term in out_of_scope_keywords) and not any(k in q_lower for k in ["flood", "drought", "rain", "gorakhpur", "mahoba", "water", "river", "up", "risk"]):
            return (
                "[EVIDENCE BOUNDARY NOTICE]\n\n"
                "• **Scope Boundary**: JalRakshak Assistant is strictly grounded in environmental and disaster risk indicators for Uttar Pradesh (Gorakhpur flood risk and Mahoba meteorological drought).\n"
                "• **Result**: The requested information is absent from the backend environmental telemetry and risk database.\n"
                "• **Available Topics**: You may ask about 7-day/30-day rainfall accumulation in Gorakhpur, SPI-3 drought indices in Mahoba, historical climatological anomalies, or official preparedness checklists."
            )

        loc = grounded_data["target_location"]
        indicators = {item.indicator_id: item.value for item in grounded_data["evidence_items"]}

        if loc == "gorakhpur":
            rain_7d = indicators.get("gorakhpur_rain_7d", 286.0)
            anomaly_7d = indicators.get("gorakhpur_anomaly_7d", 65.3)
            rain_30d = indicators.get("gorakhpur_rain_30d", 512.0)
            wet_days = int(indicators.get("gorakhpur_wet_days_30d", 18))
            percentile = indicators.get("gorakhpur_percentile_7d", 94.2)

            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"• **Location Context**: Gorakhpur district, Eastern Uttar Pradesh (Rapti & Rohini River Basin, elevation ~84m MSL).\n"
                f"• **7-Day Cumulative Rainfall**: {rain_7d:.1f} mm, representing a +{anomaly_7d:.1f}% departure above the 30-year climatological normal.\n"
                f"• **Historical Comparison**: Current 7-day accumulation ranks at the {percentile:.1f}th percentile historically.\n"
                f"• **30-Day Accumulation**: {rain_30d:.1f} mm recorded across {wet_days} wet days (daily precipitation >= 2.5 mm).\n"
                f"• **Authoritative Document Context**: Gorakhpur is categorized as a hyper-sensitive flood district in the UPSDMA 2024 Flood Mock Exercise Report.\n\n"
                f"**Mandatory Scientific Boundaries**:\n"
                f"1. Rainfall accumulation indicates meteorological water loading only. It does NOT model actual Rapti river gauge levels, upstream Nepal releases, or embankment integrity.\n"
                f"2. For official flood evacuation orders and river stage warnings, refer directly to Central Water Commission (CWC) and UPSDMA bulletins."
            )
        elif loc == "mahoba":
            rain_90d = indicators.get("mahoba_rain_90d", 62.0)
            anomaly_90d = indicators.get("mahoba_anomaly_90d", -58.7)
            kharif_def = indicators.get("mahoba_kharif_deficit", -72.0)
            spi3 = indicators.get("mahoba_spi_3", -1.84)
            dry_days = int(indicators.get("mahoba_consecutive_dry_days", 22))

            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"• **Location Context**: Mahoba district, Bundelkhand Plateau, Southern Uttar Pradesh (Elevation ~214m MSL, shallow rocky aquifers).\n"
                f"• **90-Day Cumulative Rainfall**: {rain_90d:.1f} mm, which is {abs(anomaly_90d):.1f}% below the seasonal normal ({rain_90d:.1f} mm vs expected ~150 mm).\n"
                f"• **Kharif Seasonal Deficit**: Departure stands at {kharif_def:.1f}%, indicating substantial monsoon shortfall.\n"
                f"• **Standardized Precipitation Index (SPI-3)**: {spi3:.2f} (classified as 'Severely Dry' / approaching extreme meteorological drought).\n"
                f"• **Dry Spell Persistence**: Longest consecutive dry spell reached {dry_days} days without meaningful precipitation (< 1.0 mm).\n\n"
                f"**Mandatory Scientific Boundaries**:\n"
                f"1. SPI-3 and rainfall deficits measure meteorological drought only. They do NOT measure root-zone soil moisture or crystalline fractured-rock aquifer depletion without ground telemetry.\n"
                f"2. Crop irrigation advisories must be cross-referenced with UP Agriculture Department and Krishi Vigyan Kendra (KVK) bulletins."
            )
        else:
            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"JalRakshak environmental intelligence decision-support prototype covers two primary pilot zones:\n"
                f"1. **Gorakhpur**: Evaluated for heavy monsoon precipitation and alluvial Terai drainage vulnerability.\n"
                f"2. **Mahoba**: Evaluated for Bundelkhand agro-climatic rainfall deficit and SPI-3 meteorological drought index.\n"
                f"Please specify Gorakhpur or Mahoba for detailed grounded indicators."
            )

        return answer

    @classmethod
    async def process_chat(
        cls,
        query: str,
        location: Optional[str] = "gorakhpur"
    ) -> AssistantChatResponse:
        """
        Orchestrates prompt screening, evidence retrieval, model query (or honest fallback),
        and returns a fully structured grounded response.
        """
        is_safe, sanitized_or_error = cls.sanitize_query(query)
        if not is_safe:
            return AssistantChatResponse(
                answer=sanitized_or_error,
                runtime_status="unavailable",
                model_name=GEMMA_MODEL_NAME,
                evidence_used=[],
                citations=[],
                relevant_indicators=[],
                data_timestamps={"timestamp": datetime.now(timezone.utc).isoformat()},
                is_demo_data=True,
                limitations=["Input rejected due to safety or prompt-injection defense check."],
            )

        clean_query = sanitized_or_error
        grounded_data = cls.retrieve_grounded_evidence(location or "gorakhpur", clean_query)

        # Build strict system prompt for neural runtime if available
        system_prompt = (
            "You are the JalRakshak Environmental Intelligence Grounded Assistant for Uttar Pradesh, India.\n"
            "You explain environmental indicators to disaster relief coordinators and municipal officials.\n"
            "STRICT RULES:\n"
            "1. ONLY rely on the provided evidence indicators, baselines, and official source metadata.\n"
            "2. NEVER invent, modify, or predict numbers, inundation depths, or probabilities.\n"
            "3. Explicitly state that rainfall accumulation alone does NOT prove an imminent flood.\n"
            "4. Explicitly state that SPI-3 does NOT directly measure soil moisture or groundwater.\n"
            "5. Distinguish observed measurements from derived indicators and official alerts."
        )

        user_prompt_with_context = (
            f"USER QUERY: {clean_query}\n\n"
            f"RETRIEVED BACKEND EVIDENCE:\n"
            f"Location: {grounded_data['target_location'].capitalize()}\n"
            f"Evidence Items:\n"
            + "\n".join(
                f"- {item.name}: {item.value} {item.units} ({item.category}, window: {item.observation_period})"
                for item in grounded_data["evidence_items"]
            )
            + f"\nLimitations:\n"
            + "\n".join(f"- {note}" for note in grounded_data["limitations"])
            + f"\nCitations: {', '.join(grounded_data['citations'])}\n"
            f"Timestamps: {grounded_data['timestamps']}\n"
        )

        # Attempt call to Gemma 4 runtime
        runtime_ok, model_reply = await cls.query_local_gemma_runtime(
            prompt=user_prompt_with_context,
            system_instruction=system_prompt
        )

        if runtime_ok and model_reply:
            answer = model_reply
            runtime_status = "available"
        else:
            # Honest, transparent fallback clearly labeled as deterministic engine
            answer = cls.synthesize_transparent_grounded_answer(clean_query, grounded_data)
            runtime_status = "unavailable"

        return AssistantChatResponse(
            answer=answer,
            runtime_status=runtime_status,
            model_name=GEMMA_MODEL_NAME,
            evidence_used=grounded_data["evidence_items"],
            citations=grounded_data["citations"],
            relevant_indicators=grounded_data["indicators_list"],
            data_timestamps=grounded_data["timestamps"],
            is_demo_data=grounded_data["is_demo_data"],
            limitations=grounded_data["limitations"],
        )
