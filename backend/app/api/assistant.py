import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from ..schemas.assistant import AssistantChatRequest, AssistantChatResponse
from ..engine.assistant_engine import GroundedAssistantEngine

logger = logging.getLogger("jalrakshak.api.assistant")

router = APIRouter(prefix="/assistant", tags=["Assistant"])

@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    """
    POST /api/v1/assistant/chat
    Answers user queries grounded strictly in calculated risk indicators,
    provenance citations, and scientific boundary conditions.
    """
    try:
        response = await GroundedAssistantEngine.process_chat(
            query=request.query,
            location=request.location,
            mode=request.mode if hasattr(request, "mode") and request.mode else "demo"
        )
        return response
    except Exception as e:
        logger.error(f"Assistant processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Assistant processing failed while querying indicators. Operating in grounded fallback mode."
        )
