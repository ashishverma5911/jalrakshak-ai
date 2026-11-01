"""0001_initial_multi_region_schema

Revision ID: 0001_initial_region_schema
Revises: 
Create Date: 2026-10-30 14:50:00

Initial multi-region foundation schema with PostgreSQL/PostGIS support:
- regions (hierarchical country -> state -> district -> subdistrict)
- hazard_types (extensible hazard registry: flood, drought, etc.)
- region_hazards (many-to-many junction with region-specific configs)
- region_boundaries (geospatial boundaries with PostGIS SRID 4326)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.base import GeoBoundaryType

# revision identifiers, used by Alembic.
revision: str = "0001_initial_region_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Enable PostGIS extension if running on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Create 'regions' table
    op.create_table(
        "regions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("region_type", sa.String(length=32), nullable=False),
        sa.Column("parent_id", sa.String(length=64), nullable=True),
        sa.Column("country_code", sa.String(length=8), server_default="IN", nullable=False),
        sa.Column("state_code", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["regions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_regions_code"),
    )
    op.create_index("ix_regions_code", "regions", ["code"])
    op.create_index("ix_regions_name", "regions", ["name"])
    op.create_index("ix_regions_region_type", "regions", ["region_type"])
    op.create_index("ix_regions_parent_id", "regions", ["parent_id"])
    op.create_index("ix_regions_country_code", "regions", ["country_code"])
    op.create_index("ix_regions_state_code", "regions", ["state_code"])
    op.create_index("ix_regions_is_active", "regions", ["is_active"])
    op.create_index("ix_regions_type_active", "regions", ["region_type", "is_active"])
    op.create_index("ix_regions_state_type", "regions", ["state_code", "region_type"])
    op.create_index("ix_regions_country_state", "regions", ["country_code", "state_code"])

    # 2. Create 'hazard_types' table
    op.create_table(
        "hazard_types",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_hazard_types_code"),
    )
    op.create_index("ix_hazard_types_code", "hazard_types", ["code"])
    op.create_index("ix_hazard_types_is_active", "hazard_types", ["is_active"])

    # 3. Create 'region_hazards' table
    op.create_table(
        "region_hazards",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("hazard_type_id", sa.String(length=32), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("configuration", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["hazard_type_id"], ["hazard_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", "hazard_type_id", name="uq_region_hazard"),
    )
    op.create_index("ix_region_hazards_region_id", "region_hazards", ["region_id"])
    op.create_index("ix_region_hazards_hazard_type_id", "region_hazards", ["hazard_type_id"])
    op.create_index("ix_region_hazards_is_enabled", "region_hazards", ["is_enabled"])
    op.create_index("ix_region_hazards_enabled", "region_hazards", ["hazard_type_id", "is_enabled"])

    # 4. Create 'region_boundaries' table
    op.create_table(
        "region_boundaries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("geometry", GeoBoundaryType(), nullable=True),
        sa.Column("boundary_source", sa.String(length=64), server_default="survey_of_india", nullable=False),
        sa.Column("boundary_version", sa.String(length=32), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_region_boundaries_region_id", "region_boundaries", ["region_id"])


def downgrade() -> None:
    op.drop_table("region_boundaries")
    op.drop_table("region_hazards")
    op.drop_table("hazard_types")
    op.drop_table("regions")
