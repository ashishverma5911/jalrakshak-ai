"""
DailyPrecipitation SQLAlchemy Model for JalRakshak AI
Stores gridded and station rainfall time-series with composite primary key (region_id, observation_date)
and declarative range partitioning on PostgreSQL.
"""
from datetime import date, datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import relationship

from ..base import Base


class DailyPrecipitation(Base):
    __tablename__ = "daily_precipitation"

    # Composite Primary Key
    region_id = Column(
        String(64),
        ForeignKey("regions.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    observation_date = Column(Date, primary_key=True, nullable=False)

    # Observed or gridded rainfall in millimeters
    # NULL indicates a verified missing observation date (not zero)
    rainfall_mm = Column(Float, nullable=True)

    # Provenance and source identifier (e.g., chirps_daily, nasa_gpm_imerg)
    data_source = Column(String(64), nullable=False, default="chirps_daily")

    # Ingestion audit timestamp
    ingestion_timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Quality status: observed, zero_precipitation, provisional_extreme, missing, unverified
    quality_status = Column(
        String(32), nullable=False, default="observed"
    )

    # Provenance metadata (e.g. spatial resolution, cell lat/lon, raw sensor flags)
    observation_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    region = relationship("Region")

    # Table arguments: Check constraint and performance indexes
    # Note: On PostgreSQL, range partitioning is declared at the table level in Alembic DDL
    __table_args__ = (
        CheckConstraint(
            "rainfall_mm IS NULL OR rainfall_mm >= 0.0",
            name="chk_rainfall_non_negative",
        ),
        Index("ix_daily_precip_date", "observation_date"),
        Index("ix_daily_precip_source", "data_source"),
        Index("ix_daily_precip_quality", "quality_status"),
        Index("ix_daily_precip_region_date", "region_id", "observation_date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "observation_date": self.observation_date.isoformat() if self.observation_date else None,
            "rainfall_mm": self.rainfall_mm,
            "data_source": self.data_source,
            "quality_status": self.quality_status,
            "ingestion_timestamp": self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None,
            "metadata": self.observation_metadata or {},
        }
