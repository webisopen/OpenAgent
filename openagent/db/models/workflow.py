from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()  # type: ignore


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    agent_id = Column(
        Integer, nullable=False
    )  # Use global agent personality and instruction
    enabled_tools = Column(String)  # comma separated tool ids
    min_model_score = Column(Float)  # Minimum required model capability score
    status = Column(String)
    created_at = Column(DateTime, default=datetime.UTC, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.UTC, onupdate=datetime.UTC, nullable=False
    )
