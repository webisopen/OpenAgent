import os
from typing import Optional, Literal
from urllib.parse import urlparse

from sqlalchemy import create_engine as sa_create_engine, text as sa_text, Engine
from loguru import logger


def _create_sqlite_engine(db_url: str) -> Engine:
    """
    Create a SQLite engine from a URL.
    
    Args:
        db_url: SQLite database URL (sqlite:///path/to/file.db)
        
    Returns:
        SQLAlchemy engine instance
    """
    return sa_create_engine(db_url)


def _ensure_postgres_database_exists(db_url: str) -> None:
    """
    Ensure that the PostgreSQL database specified in the URL exists.
    Creates the database if it doesn't exist.
    
    Args:
        db_url: PostgreSQL database URL
    """
    url = urlparse(db_url)
    pg_db_name = url.path[1:]  # Remove leading '/'
    base_url = f"{url.scheme}://{url.netloc}"

    # Create a connection to the default postgres database
    default_engine = sa_create_engine(f"{base_url}/postgres")
    default_conn = default_engine.connect()
    default_conn.execute(sa_text("commit"))  # Close any open transactions

    try:
        # Check if database exists
        result = default_conn.execute(
            sa_text(f"SELECT 1 FROM pg_database WHERE datname = :db_name"), 
            {"db_name": pg_db_name}
        )
        
        if not result.scalar():
            # Create database if it doesn't exist
            default_conn.execute(sa_text("commit"))
            default_conn.execute(sa_text(f'CREATE DATABASE "{pg_db_name}"'))
            logger.info(f"Created database {pg_db_name}")
    except Exception as e:
        logger.error(f"Error creating database: {e}")
    finally:
        default_conn.close()
        default_engine.dispose()


def _create_postgres_engine(db_url: str) -> Engine:
    """
    Create a PostgreSQL engine from a URL.
    Ensures the database exists before creating the engine.
    
    Args:
        db_url: PostgreSQL database URL
        
    Returns:
        SQLAlchemy engine instance
    """
    _ensure_postgres_database_exists(db_url)
    return sa_create_engine(db_url)


def create_engine(db_url: str) -> Engine:
    """
    Create a database engine based on the provided configuration.
    Database type is automatically detected from the URL.
    
    Args:
        db_url: Database URL. For postgres: postgresql://user:password@host:port/database, 
                for sqlite: sqlite:///path/to/file.db
            
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        ValueError: If an unsupported database type is detected or if db_url is missing
    """
    if not db_url:
        raise ValueError("Database URL is required")
    
    # Auto-detect database type from URL
    if db_url.startswith('sqlite:'):
        return _create_sqlite_engine(db_url)
    elif db_url.startswith('postgresql:'):
        return _create_postgres_engine(db_url)
    else:
        raise ValueError(f"Could not detect database type from URL: {db_url}. "
                        "Supported URL formats: 'sqlite:///path/to/file.db' or 'postgresql://user:password@host:port/database'") 