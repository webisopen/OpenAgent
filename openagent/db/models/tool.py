from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()  # type: ignore


class ToolType(enum.Enum):
    TEXT_GENERATION = "text_generation"
    SOCIAL_INTEGRATION = "social_integration"


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(Enum(ToolType), nullable=False)
    model_id = Column(Integer, nullable=False)  # One-to-one relationship with Model
    config = Column(Text)  # Configuration stored in JSON format
    created_at = Column(DateTime, default=datetime.UTC, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.UTC, onupdate=datetime.UTC, nullable=False
    )
