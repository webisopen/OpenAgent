import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text

from openagent.database.models.base import Base


class ToolType(enum.Enum):
    TEXT_GENERATION = "text_generation"
    SOCIAL_INTEGRATION = "social_integration"

    def __str__(self):
        return self.value


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(
        Enum(ToolType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        if "type" in kwargs and isinstance(kwargs["type"], ToolType):
            kwargs["type"] = kwargs["type"].value
        super().__init__(*args, **kwargs)
