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
    GEMINI_API_KEY,
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
        location: Optional[str],
        query: str,
        mode: str = "demo"
    ) -> Dict[str, Any]:
        """
        Retrieves real calculated risk indicators, baselines, and limitations from
        backend engines. Explicit user location takes absolute precedence over query keywords.
        """
        loc_clean = (location or "").lower().replace("district-", "").strip()
        q_lower = query.lower()

        # 1. Explicit user-selected location MUST take priority unconditionally.
        if loc_clean and loc_clean not in ["", "all", "none"]:
            target_loc = loc_clean
        else:
            # Only infer location from query if user did not supply an explicit location.
            # Match EXPLICIT district names only. Hazard keywords (flood, drought, etc.)
            # must NEVER change or infer the district!
            if "mahoba" in q_lower:
                target_loc = "mahoba"
            elif "gorakhpur" in q_lower:
                target_loc = "gorakhpur"
            elif "lucknow" in q_lower:
                target_loc = "lucknow"
            elif "patna" in q_lower:
                target_loc = "patna"
            elif "gaya" in q_lower:
                target_loc = "gaya"
            elif "varanasi" in q_lower:
                target_loc = "varanasi"
            else:
                target_loc = "gorakhpur"

        evidence_items: List[GroundedEvidenceItem] = []
        indicators_list: List[Dict[str, Any]] = []
        limitations: List[str] = []
        citations: List[str] = []
        timestamps: Dict[str, str] = {
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        is_demo = (mode == "demo")
        data_mode = "DEMONSTRATION" if is_demo else "CACHED_VERIFIED"

        if target_loc == "mahoba":
            district_info = _ingestion_service.get_district_info("mahoba")
            daily_df = _ingestion_service.load_daily_rainfall("mahoba", mode=mode)
            assessment = DroughtRiskEngine.evaluate(district_info, daily_df, mode=mode)
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
                f"{DATA_SOURCES_REGISTRY['chirps_daily']['source_name']} (0.05° Gridded Daily Series & 1991–2020 Normals)",
                f"{DATA_SOURCES_REGISTRY['srtm_dem']['source_name']} (30m Elevation Benchmark)",
                "WMO Standardized Precipitation Index (SPI) Methodology (WMO-No. 1090)",
                f"{DATA_SOURCES_REGISTRY['upsdma_imd']['source_name']}",
            ]
        elif target_loc == "gorakhpur":
            # Gorakhpur flood context
            district_info = _ingestion_service.get_district_info("gorakhpur")
            daily_df = _ingestion_service.load_daily_rainfall("gorakhpur", mode=mode)
            assessment = FloodRiskEngine.evaluate(district_info, daily_df, mode=mode)
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
                f"{DATA_SOURCES_REGISTRY['chirps_daily']['source_name']} (0.05° Gridded Daily Series & 1991–2020 Normals)",
                f"{DATA_SOURCES_REGISTRY['srtm_dem']['source_name']} (30m Elevation Benchmark)",
                f"{DATA_SOURCES_REGISTRY['upsdma_imd']['source_name']}",
            ]
        else:
            # Candidate district (e.g. Lucknow, Patna, Gaya, Varanasi)
            is_demo = False
            data_mode = "DATA_PENDING"
            timestamps["observation_period"] = "Pending Ingestion"
            citations = ["JalRakshak Multi-Region Registry"]
            limitations = [
                f"Candidate district '{target_loc.capitalize()}' is pending onboarding.",
                "Zero data bleed policy enforced: candidate districts do not inherit pilot metrics or rainfall observations.",
            ]

        return {
            "target_location": target_loc,
            "evidence_items": evidence_items,
            "indicators_list": indicators_list,
            "limitations": limitations,
            "citations": citations,
            "timestamps": timestamps,
            "is_demo_data": is_demo,
            "data_mode": data_mode,
        }

    @classmethod
    async def query_hosted_gemma_runtime(
        cls,
        prompt: str,
        system_instruction: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Architecture: Google-Hosted Gemma 4 API (gemma-4-26b-a4b-it via Google AI Studio / Gemini API).
        Requires GEMINI_API_KEY environment variable.
        If credentials are absent or runtime is unreachable, safely falls back to deterministic grounded synthesis.
        """
        if not GEMINI_API_KEY:
            logger.debug("Google-Hosted Gemma 4 API key (GEMINI_API_KEY) not configured. Using deterministic grounded synthesis.")
            return False, None

        endpoint = f"{GEMMA_API_URL.rstrip('/')}/{GEMMA_MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_instruction}\n\nEvidence-Grounded User Inquiry: {prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
            },
        }
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=GEMMA_TIMEOUT_SECONDS) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and isinstance(candidates, list):
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"]
                            if text and isinstance(text, str) and text.strip():
                                return True, text.strip()
                else:
                    logger.warning(f"Hosted Gemma 4 API responded with status {resp.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as ex:
            logger.info(f"Hosted Gemma 4 API endpoint unreachable ({type(ex).__name__}): {ex}")
        except Exception as general_ex:
            logger.warning(f"Unexpected error querying hosted Gemma 4 API: {general_ex}")

        return False, None

    # Backwards-compatible alias
    query_local_gemma_runtime = query_hosted_gemma_runtime

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

        # Handle explicit question about demo data / live measurements / data modes
        if any(term in q_lower for term in ["live measurement", "live data", "real-time data", "is this live", "is this demo", "is this real", "is data real", "data mode", "provenance"]):
            return (
                "[DATA TRANSPARENCY & PROVENANCE DISCLOSURE]\n\n"
                "• **Current Execution Mode**: Transparently distinguishes between prototype fixtures (`is_demo_data: true`, `DEMONSTRATION`) and verified observations (`CACHED_VERIFIED`).\n"
                "• **Precipitation Baseline**: Daily continuous observation series (2015–2026) with 30-year climatological normals (1991–2020).\n"
                "• **Terrain Data**: NASA SRTM 30m Digital Elevation Model static district topographic benchmarks.\n"
                "• **Satellite Telemetry Status**: Near-real-time NASA GPM IMERG satellite feeds are currently not integrated into operational scoring. Live streaming feeds require authenticated institutional APIs.\n"
                "• **Candidate Districts**: Offline with zero data bleed; metric indicators are pending onboarding."
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
        data_mode = grounded_data.get("data_mode", "DEMONSTRATION")

        if loc == "gorakhpur":
            # Extract indicators with explicit None checks (0.0 is a valid measurement, NOT falsy missing data)
            rain_7d = indicators.get("flood_precip_7d_accum")
            anomaly_7d = indicators.get("flood_precip_7d_anomaly")
            rain_30d = indicators.get("flood_precip_30d_accum")
            wet_days = indicators.get("flood_heavy_rainfall_days")
            if wet_days is None:
                wet_days = indicators.get("flood_wet_days_7d")
            percentile = indicators.get("flood_historical_percentile")
            terrain_idx = indicators.get("flood_terrain_vulnerability")

            rain_7d_str = f"{rain_7d:.1f} mm" if rain_7d is not None else "Data unavailable"
            anomaly_7d_str = (
                f"representing a departure of {anomaly_7d:+.1f}% from the 30-year climatological normal (1991–2020)"
                if anomaly_7d is not None
                else "departure from 30-year normal unavailable"
            )
            percentile_str = (
                f"Current 7-day accumulation ranks at the {percentile:.1f}th percentile historically"
                if percentile is not None
                else "Historical percentile calculation unavailable (insufficient baseline records)"
            )
            rain_30d_str = f"{rain_30d:.1f} mm" if rain_30d is not None else "Data unavailable"
            wet_days_str = (
                f"recorded across {int(wet_days)} heavy rainfall days (daily precipitation >= 64.5 mm)"
                if wet_days is not None
                else "heavy rainfall day frequency unavailable"
            )
            terrain_str = (
                f"{terrain_idx:.2f} (High vulnerability due to low slope < 0.5° and low elevation ~77.7m MSL)"
                if terrain_idx is not None
                else "Terrain elevation analysis unavailable"
            )

            mode_label = (
                "Verified Daily Observational Series (1991–2020 Normal Baseline)"
                if data_mode == "CACHED_VERIFIED"
                else "Prototype Demonstration Fixture (Simulated Data)"
            )

            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"• **Data Mode**: `{data_mode}` ({mode_label})\n"
                f"• **Location Context**: Gorakhpur district, Eastern Uttar Pradesh (Rapti & Rohini River Basin, elevation ~77.7m MSL, flat alluvial plain).\n"
                f"• **7-Day Cumulative Rainfall**: {rain_7d_str}, {anomaly_7d_str}.\n"
                f"• **Historical Comparison**: {percentile_str}.\n"
                f"• **30-Day Antecedent Rainfall**: {rain_30d_str} {wet_days_str}.\n"
                f"• **Terrain Flood Vulnerability**: {terrain_str}.\n"
                f"• **Authoritative Document Context**: Gorakhpur is categorized as a hyper-sensitive flood district in the UPSDMA 2024 Flood Mock Exercise Report.\n\n"
                f"**Mandatory Scientific Boundaries**:\n"
                f"1. Rainfall accumulation indicates meteorological water loading only. It does NOT model actual Rapti river gauge levels, upstream Nepal releases, or embankment integrity.\n"
                f"2. For official flood evacuation orders and river stage warnings, refer directly to Central Water Commission (CWC) and UPSDMA bulletins."
            )
        elif loc == "mahoba":
            rain_90d = indicators.get("drought_precip_90d_accum")
            anomaly_90d = indicators.get("drought_precip_90d_anomaly")
            kharif_def = indicators.get("drought_seasonal_deficit")
            spi3 = indicators.get("drought_spi_3")
            dry_days = indicators.get("drought_consecutive_dry_days")

            rain_90d_str = f"{rain_90d:.1f} mm" if rain_90d is not None else "Data unavailable"
            anomaly_90d_str = (
                f"which is {anomaly_90d:+.1f}% departure from 30-year normal"
                if anomaly_90d is not None
                else "departure from 30-year normal unavailable"
            )
            kharif_str = (
                f"Cumulative Kharif monsoon departure stands at {kharif_def:+.1f}% relative to the 845.4 mm normal"
                if kharif_def is not None
                else "Kharif seasonal departure unavailable"
            )
            spi3_str = (
                f"{spi3:.2f} (classified under WMO criteria)"
                if spi3 is not None
                else "Calculation unavailable (insufficient data)"
            )
            dry_days_str = (
                f"Longest unbroken consecutive dry spell reached {int(dry_days)} days (< 1.0 mm/day)"
                if dry_days is not None
                else "Dry spell persistence unavailable"
            )

            mode_label = (
                "Verified Daily Observational Series (1991–2020 Normal Baseline)"
                if data_mode == "CACHED_VERIFIED"
                else "Prototype Demonstration Fixture (Simulated Data)"
            )

            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"• **Data Mode**: `{data_mode}` ({mode_label})\n"
                f"• **Location Context**: Mahoba district, Bundelkhand Plateau, Southern Uttar Pradesh (Elevation ~197.1m MSL, crystalline granite bedrock).\n"
                f"• **90-Day Cumulative Rainfall**: {rain_90d_str}, {anomaly_90d_str}.\n"
                f"• **Kharif Monsoon Departure**: {kharif_str}.\n"
                f"• **Standardized Precipitation Index (SPI-3)**: {spi3_str}.\n"
                f"• **Dry Spell Persistence**: {dry_days_str}.\n\n"
                f"**Mandatory Scientific Boundaries**:\n"
                f"1. SPI-3 and rainfall deficits measure meteorological drought only. They do NOT measure root-zone soil moisture or crystalline fractured-rock aquifer depletion without ground telemetry.\n"
                f"2. Crop irrigation advisories must be cross-referenced with UP Agriculture Department and Krishi Vigyan Kendra (KVK) bulletins."
            )
        else:
            answer = (
                f"[GROUNDED DATA EXPLANATION — DETERMINISTIC ENGINE (Gemma 4 Runtime Unavailable)]\n\n"
                f"• **District**: {loc.capitalize()}\n"
                f"• **Data Status**: `DATA_PENDING` (Pending Onboarding)\n"
                f"• **Notice**: Observational telemetry and scientific hazard calculations for candidate district '{loc.capitalize()}' are pending onboarding.\n"
                f"• Candidate district '{loc.capitalize()}' is unlinked from active telemetry. Zero cross-district data bleed is strictly enforced.\n"
                f"• No observations, risk indices, or rainfall measurements are interpolated from other districts."
            )

        return answer

    @classmethod
    async def process_chat(
        cls,
        query: str,
        location: Optional[str] = "gorakhpur",
        mode: str = "demo"
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
                data_mode="DEMONSTRATION",
                limitations=["Input rejected due to safety or prompt-injection defense check."],
            )

        clean_query = sanitized_or_error
        grounded_data = cls.retrieve_grounded_evidence(location, clean_query, mode=mode)

        # Build strict system prompt for neural runtime if available
        system_prompt = (
            "You are the JalRakshak Environmental Intelligence Grounded Assistant for Uttar Pradesh, India.\n"
            "You explain environmental indicators to disaster relief coordinators and municipal officials.\n"
            "STRICT RULES:\n"
            "1. ONLY rely on the provided evidence indicators, baselines, and official source metadata.\n"
            "2. NEVER invent, modify, or predict numbers, inundation depths, or probabilities.\n"
            "3. If an indicator is missing or marked as Data Unavailable, explicitly state it is unavailable; NEVER guess or invent a value.\n"
            "4. NEVER substitute or interpolate data from other districts. If a candidate district is requested, state DATA_PENDING.\n"
            "5. Explicitly state that rainfall accumulation alone does NOT prove an imminent flood.\n"
            "6. Explicitly state that SPI-3 does NOT directly measure soil moisture or groundwater.\n"
            "7. Distinguish observed measurements from derived indicators and official alerts."
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
            data_mode=grounded_data.get("data_mode", "DEMONSTRATION"),
            limitations=grounded_data["limitations"],
        )
