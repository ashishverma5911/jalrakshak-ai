"""
HazardType and RegionHazard SQLAlchemy Models
"""
from typing import Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from ..base import Base


class HazardType(Base):
    __tablename__ = "hazard_types"

    id = Column(String(32), primary_key=True)  # e.g. "flood", "drought"
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RegionHazard(Base):
    __tablename__ = "region_hazards"

    id = Column(String(64), primary_key=True)
    region_id = Column(String(64), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    hazard_type_id = Column(String(32), ForeignKey("hazard_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    configuration = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    region = relationship("Region", back_populates="hazards")
    hazard_type = relationship("HazardType")

    __table_args__ = (
        UniqueConstraint("region_id", "hazard_type_id", name="uq_region_hazard"),
        Index("ix_region_hazards_enabled", "hazard_type_id", "is_enabled"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "region_id": self.region_id,
            "hazard_type_id": self.hazard_type_id,
            "hazard_code": self.hazard_type.code if self.hazard_type else self.hazard_type_id,
            "hazard_name": self.hazard_type.name if self.hazard_type else self.hazard_type_id,
            "is_enabled": self.is_enabled,
            "configuration": self.configuration or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
