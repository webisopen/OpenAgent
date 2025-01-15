from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from alembic.config import Config
from alembic import command

_SessionLocal = None


def init_db():
    """Initialize the database."""
    # Create database engine
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL must be set")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

    # Run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    return engine, SessionLocal


def get_db() -> Session:
    """Get a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    db = _SessionLocal()
    try:
        return db
    except:
        db.close()
        raise


__all__ = ["init_db", "get_db"]
