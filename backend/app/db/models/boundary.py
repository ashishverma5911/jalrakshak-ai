"""
RegionBoundary SQLAlchemy Model with PostGIS Geometry support
"""
from typing import Dict, Any
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from ..base import Base, GeoBoundaryType


class RegionBoundary(Base):
    __tablename__ = "region_boundaries"

    id = Column(String(64), primary_key=True)
    region_id = Column(String(64), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    geometry = Column(GeoBoundaryType(), nullable=True)
    boundary_source = Column(String(64), nullable=False, default="survey_of_india")
    boundary_version = Column(String(32), nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    region = relationship("Region", back_populates="boundaries")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "region_id": self.region_id,
            "boundary_source": self.boundary_source,
            "boundary_version": self.boundary_version,
            "has_geometry": self.geometry is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
