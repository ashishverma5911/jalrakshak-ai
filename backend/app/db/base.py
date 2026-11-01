"""
SQLAlchemy Base and Custom Types for JalRakshak AI
"""
from typing import Optional
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import TypeDecorator, Text
from geoalchemy2 import Geometry

Base = declarative_base()


class GeoBoundaryType(TypeDecorator):
    """
    Geospatial Boundary Column Type.
    In PostgreSQL, maps to PostGIS Geometry('GEOMETRY', srid=4326).
    In SQLite or other environments, gracefully falls back to Text (storing WKT / GeoJSON).
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True))
        return dialect.type_descriptor(Text())
