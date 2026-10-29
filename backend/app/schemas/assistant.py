from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class AssistantChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question or inquiry")
    location: Optional[str] = Field("gorakhpur", description="Focus pilot location (gorakhpur, mahoba, or all)")

class GroundedEvidenceItem(BaseModel):
    indicator_id: str
    name: str
    value: float
    units: str
    category: str
    observation_period: str
    quality_status: str

class AssistantChatResponse(BaseModel):
    answer: str
    runtime_status: Literal["available", "unavailable", "offline_demo"]
    model_name: str
    evidence_used: List[GroundedEvidenceItem]
    citations: List[str]
    relevant_indicators: List[Dict[str, Any]]
    data_timestamps: Dict[str, str]
    is_demo_data: bool = True
    limitations: List[str]
    disclaimer: str = (
        "JalRakshak Grounded Assistant is an environmental decision-support tool. "
        "Answers explain transparent calculated indicators and official documents. "
        "It does not produce validated flood predictions or replace official government emergency warnings."
    )
