from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from alembic.config import Config
from alembic import command
import os
from typing import Optional, Generator


class DatabaseManager:
    _instance = None
    _engine: Optional[object] = None
    _session_factory: Optional[sessionmaker] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls) -> None:
        """Initialize the database connection and run migrations."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL must be set")

        # Create engine
        cls._engine = create_engine(database_url)

        # Create session factory
        cls._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=cls._engine)

        # Run migrations
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    @classmethod
    def get_session(cls) -> Session:
        """Get a new database session."""
        if cls._session_factory is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return cls._session_factory()

    @classmethod
    def get_engine(cls):
        """Get the SQLAlchemy engine."""
        if cls._engine is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return cls._engine


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Usage:
        @router.get("/")
        def route(db: Session = Depends(get_db)):
            ...
    """
    db = DatabaseManager.get_session()
    try:
        yield db
    finally:
        db.close()


__all__ = ["DatabaseManager", "get_db"]
