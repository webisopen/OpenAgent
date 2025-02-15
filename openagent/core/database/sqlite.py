import os

import sqlalchemy
from sqlalchemy import Engine


def create_engine(path: str, **kwargs) -> Engine:
    """Create a new engine instance

    Args:
        path (str): The database file path

    Returns:
        Engine: A new engine instance
    """
    # if file does not exist, create it
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    if not os.path.exists(path):
        open(path, "w").close()
    engine = sqlalchemy.create_engine(f"sqlite:///{path}", **kwargs)

    return engine
