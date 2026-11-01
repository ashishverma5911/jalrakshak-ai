"""0002_daily_precipitation_timeseries

Revision ID: 0002_daily_precipitation_timeseries
Revises: 0001_initial_region_schema
Create Date: 2026-10-30 21:35:00

Adds daily_precipitation timeseries table:
- Composite primary key: (region_id, observation_date)
- Declarative range partitioning by observation_date on PostgreSQL (annual partitions 2014-2026 + DEFAULT partition)
- Non-negative check constraint (rainfall_mm >= 0.0 OR NULL)
- Provenance and quality status columns
- Fallback for SQLite testing environment
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_daily_precipitation_timeseries"
down_revision: Union[str, None] = "0001_initial_region_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        # 1. Create partitioned parent table in PostgreSQL
        op.execute("""
            CREATE TABLE daily_precipitation (
                region_id VARCHAR(64) NOT NULL,
                observation_date DATE NOT NULL,
                rainfall_mm DOUBLE PRECISION,
                data_source VARCHAR(64) NOT NULL DEFAULT 'chirps_daily',
                ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                quality_status VARCHAR(32) NOT NULL DEFAULT 'observed',
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                CONSTRAINT pk_daily_precipitation PRIMARY KEY (region_id, observation_date),
                CONSTRAINT fk_daily_precip_region FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE RESTRICT,
                CONSTRAINT chk_rainfall_non_negative CHECK (rainfall_mm IS NULL OR rainfall_mm >= 0.0)
            ) PARTITION BY RANGE (observation_date);
        """)

        # 2. Create annual partitions covering historical baseline (2014-2026)
        for year in range(2014, 2027):
            next_year = year + 1
            op.execute(f"""
                CREATE TABLE IF NOT EXISTS daily_precipitation_{year}
                PARTITION OF daily_precipitation
                FOR VALUES FROM ('{year}-01-01') TO ('{next_year}-01-01');
            """)

        # 3. Create DEFAULT partition for future observations beyond 2026 and legacy dates
        op.execute("""
            CREATE TABLE IF NOT EXISTS daily_precipitation_default
            PARTITION OF daily_precipitation DEFAULT;
        """)

        # 4. Create performance indexes
        op.create_index("ix_daily_precip_date", "daily_precipitation", ["observation_date"])
        op.create_index("ix_daily_precip_source", "daily_precipitation", ["data_source"])
        op.create_index("ix_daily_precip_quality", "daily_precipitation", ["quality_status"])
        op.create_index("ix_daily_precip_region_date", "daily_precipitation", ["region_id", "observation_date"])

    else:
        # Standard table for non-PostgreSQL / SQLite test environments
        op.create_table(
            "daily_precipitation",
            sa.Column("region_id", sa.String(length=64), nullable=False),
            sa.Column("observation_date", sa.Date(), nullable=False),
            sa.Column("rainfall_mm", sa.Float(), nullable=True),
            sa.Column("data_source", sa.String(length=64), server_default="chirps_daily", nullable=False),
            sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("quality_status", sa.String(length=32), server_default="observed", nullable=False),
            sa.Column("metadata", sa.JSON(), server_default="{}", nullable=False),
            sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("region_id", "observation_date"),
            sa.CheckConstraint("rainfall_mm IS NULL OR rainfall_mm >= 0.0", name="chk_rainfall_non_negative"),
        )
        op.create_index("ix_daily_precip_date", "daily_precipitation", ["observation_date"])
        op.create_index("ix_daily_precip_source", "daily_precipitation", ["data_source"])
        op.create_index("ix_daily_precip_quality", "daily_precipitation", ["quality_status"])
        op.create_index("ix_daily_precip_region_date", "daily_precipitation", ["region_id", "observation_date"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP TABLE IF EXISTS daily_precipitation CASCADE;")
    else:
        op.drop_table("daily_precipitation")
