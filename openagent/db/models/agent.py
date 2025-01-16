import enum

from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum
from datetime import datetime, UTC

from openagent.db.models.base import Base


class AgentStatus(enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    personality = Column(String)
    instruction = Column(String)
    wallet_address = Column(String, nullable=False)
    token_image = Column(String)
    ticker = Column(String, nullable=False)
    contract_address = Column(String)
    pair_address = Column(String)
    twitter = Column(String)
    telegram = Column(String)
    website = Column(String)
    tool_configs = Column(JSON)
    status = Column(Enum(AgentStatus), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
