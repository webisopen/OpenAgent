from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from alembic.config import Config
from alembic import command

_SessionLocal: sessionmaker


def init_db():
    """Initialize the database."""
    # Create database engine
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL must be set")

    engine = create_engine(database_url)

    global _SessionLocal

    _SessionLocal = sessionmaker(bind=engine)

    # Run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    return engine, _SessionLocal


def get_db():
    """Get a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    return _SessionLocal()


__all__ = ["init_db", "get_db"]
