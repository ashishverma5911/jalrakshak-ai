"""
Database Session and Engine Management for JalRakshak AI
"""
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from ..core.config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT
from .base import Base

logger = logging.getLogger("jalrakshak.db")

# Setup engine arguments depending on dialect
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    engine_kwargs["pool_size"] = DB_POOL_SIZE
    engine_kwargs["max_overflow"] = DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = DB_POOL_TIMEOUT

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_db_connected() -> bool:
    """
    Checks if the configured database is reachable without raising an unhandled exception.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.debug(f"Database connection check returned offline: {e}")
        return False


def init_db_schema(target_engine=None):
    """
    Initializes database tables from Base metadata.
    """
    active_engine = target_engine or engine
    Base.metadata.create_all(bind=active_engine)
