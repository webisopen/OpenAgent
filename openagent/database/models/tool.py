from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from openagent.database.models.base import Base
from datetime import datetime, UTC
import enum


class ToolType(enum.Enum):
    TEXT_GENERATION = "text_generation"
    SOCIAL_INTEGRATION = "social_integration"


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(Enum(ToolType), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
