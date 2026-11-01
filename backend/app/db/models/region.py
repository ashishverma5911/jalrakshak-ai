"""
Region SQLAlchemy Model for JalRakshak AI Multi-Region Hierarchy
Supports: India -> States -> Districts -> Subdistricts/Blocks
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import relationship

from ..base import Base


class Region(Base):
    __tablename__ = "regions"

    id = Column(String(64), primary_key=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    region_type = Column(String(32), nullable=False, index=True)  # country, state, district, subdistrict
    parent_id = Column(String(64), ForeignKey("regions.id", ondelete="RESTRICT"), nullable=True, index=True)
    country_code = Column(String(8), nullable=False, default="IN", index=True)
    state_code = Column(String(8), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    region_metadata = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Self-referential hierarchy
    parent = relationship("Region", remote_side=[id], back_populates="children")
    children = relationship("Region", back_populates="parent", cascade="all, delete-orphan")

    # Linked hazards & boundaries
    hazards = relationship("RegionHazard", back_populates="region", cascade="all, delete-orphan")
    boundaries = relationship("RegionBoundary", back_populates="region", cascade="all, delete-orphan")

    # Composite indexes for fast scoped lookups
    __table_args__ = (
        Index("ix_regions_type_active", "region_type", "is_active"),
        Index("ix_regions_state_type", "state_code", "region_type"),
        Index("ix_regions_country_state", "country_code", "state_code"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "region_type": self.region_type,
            "parent_id": self.parent_id,
            "country_code": self.country_code,
            "state_code": self.state_code,
            "is_active": self.is_active,
            "metadata": self.region_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
