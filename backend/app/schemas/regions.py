"""
Pydantic v2 Schemas for Multi-Region Foundation
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HazardSummary(BaseModel):
    code: str = Field(..., description="Hazard identifier code (e.g. flood, drought)")
    name: Optional[str] = Field(None, description="Descriptive hazard title")
    status: str = Field("not_configured", description="Operational status: pilot, active, not_configured")
    is_enabled: bool = Field(True, description="Whether this hazard assessment is enabled")
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Region-specific hazard configuration")


class RegionSummary(BaseModel):
    id: str = Field(..., description="Stable region identifier (e.g. district-gorakhpur)")
    code: str = Field(..., description="Unique administrative code (e.g. IN-UP-GOR)")
    name: str = Field(..., description="Official region name")
    region_type: str = Field(..., description="Administrative type: country, state, district, subdistrict")
    parent_id: Optional[str] = Field(None, description="Parent region ID")
    country_code: str = Field("IN", description="ISO country code")
    state_code: Optional[str] = Field(None, description="State code if applicable (e.g. UP, BR)")
    is_active: bool = Field(True, description="Whether the region is actively tracked")
    supported_hazards: List[HazardSummary] = Field(default_factory=list, description="Hazards supported in this region")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Geographical attributes and legacy tags")


class RegionDetailResponse(BaseModel):
    id: str = Field(..., description="Stable region identifier")
    code: str = Field(..., description="Unique administrative code")
    name: str = Field(..., description="Official region name")
    region_type: str = Field(..., description="Administrative type: country, state, district, subdistrict")
    parent_id: Optional[str] = Field(None, description="Parent region ID")
    country_code: str = Field("IN", description="ISO country code")
    state_code: Optional[str] = Field(None, description="State code")
    is_active: bool = Field(True, description="Whether the region is actively tracked")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Geographical & climatological metadata")
    supported_hazards: List[HazardSummary] = Field(default_factory=list, description="Configured hazard profiles")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class RegionHazardItem(BaseModel):
    id: str
    region_id: str
    hazard_type_id: str
    hazard_code: str
    hazard_name: str
    is_enabled: bool
    configuration: Dict[str, Any] = Field(default_factory=dict)


class RegionHazardsResponse(BaseModel):
    region_id: str
    region_code: str
    region_name: str
    hazards: List[RegionHazardItem]


class RegionListResponse(BaseModel):
    total: int
    regions: List[RegionSummary]
