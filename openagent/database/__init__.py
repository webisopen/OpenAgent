import os
from typing import Generator
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
import logging
from dotenv import load_dotenv

from openagent.database.models.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    _instance = None
    _engine: object | None = None
    _session_factory: sessionmaker | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls) -> None:
        """Initialize the database connection and run migrations."""
        load_dotenv()

        # Get database URL from environment variable
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        # Create engine with PostgreSQL-specific configuration
        cls._engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Enable connection health checks
            pool_size=5,  # Set connection pool size
            max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
        )

        # Create session factory
        cls._session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=cls._engine
        )

        # Try to run migrations
        try:
            alembic_cfg = Config("alembic.ini")
            # Override sqlalchemy.url in the config
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            logger.info(f"Running Alembic migrations with URL: {database_url}")
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed successfully")
        except Exception as e:
            logger.warning(f"Error running Alembic migrations: {str(e)}")
            logger.info("Falling back to creating tables directly with SQLAlchemy")
            # If migrations fail, create tables directly
            Base.metadata.create_all(cls._engine)
            logger.info("Tables created directly with SQLAlchemy")

    @classmethod
    def generate_migration(cls, message="auto generated"):
        """Generate a new migration based on model changes"""
        load_dotenv()

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.revision(alembic_cfg, autogenerate=True, message=message)
        logger.info(f"Migration generated with message: {message}")

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
