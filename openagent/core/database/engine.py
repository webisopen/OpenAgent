import os
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine as sa_create_engine, text as sa_text, Engine
from loguru import logger


def _create_sqlite_engine(db_url: Optional[str] = None, db_name: Optional[str] = None, storage_dir: str = "storage") -> Engine:
    """
    Create a SQLite engine from a URL or create a default URL if not provided.
    
    Args:
        db_url: SQLite database URL (sqlite:///path/to/file.db)
        db_name: Database name to use if db_url is not provided
        storage_dir: Directory to store SQLite databases (default: 'storage')
        
    Returns:
        SQLAlchemy engine instance
        
    Raises:
        ValueError: If neither db_url nor db_name is provided
    """
    if db_url:
        return sa_create_engine(db_url)
    
    if not db_name:
        raise ValueError("Either db_url or db_name must be provided for SQLite")
    
    # Create default SQLite path
    db_path = os.path.join(os.getcwd(), storage_dir, f"{db_name}.db")
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    
    return sa_create_engine(f"sqlite:///{db_path}")


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


def create_engine(db_type: str = "sqlite", db_url: Optional[str] = None, db_name: Optional[str] = None, storage_dir: str = "storage") -> Engine:
    """
    Create a database engine based on the provided configuration.
    
    Args:
        db_type: Type of database ('sqlite' or 'postgres')
        db_url: Database URL. For postgres: postgresql://user:password@host:port/database, 
                for sqlite: sqlite:///path/to/file.db
        db_name: Database name to use if db_url is not provided (SQLite only)
        storage_dir: Directory to store SQLite databases (default: 'storage')
            
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        ValueError: If an unsupported database type is specified or if required parameters are missing
    """
    if db_type == "sqlite":
        return _create_sqlite_engine(db_url, db_name, storage_dir)
    elif db_type == "postgres":
        if not db_url:
            raise ValueError("Database URL is required for PostgreSQL")
        return _create_postgres_engine(db_url)
    else:
        raise ValueError(f"Unsupported database type: {db_type}") 