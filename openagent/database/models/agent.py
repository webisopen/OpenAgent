import enum
from datetime import UTC, datetime
from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String

from openagent.database.models.base import Base
from openagent.tools.tool_config import ToolConfig


class AgentStatus(str, enum.Enum):
    INACTIVE = "inactive"
    UNHEALTHY = "unhealthy"
    ACTIVE = "active"
    DELETED = "deleted"
    PAUSED = "paused"
    PENDING = "pending"

    def __str__(self):
        return self.value


class AgentType(str, enum.Enum):
    IP = "IP"
    DEFI = "DeFi"
    DESCI = "DeSci"
    OTHERS = "Others"

    def __str__(self):
        return self.value


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
    status = Column(
        Enum(AgentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    type = Column(
        Enum(AgentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    deployment_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        if "type" in kwargs and isinstance(kwargs["type"], AgentType):
            kwargs["type"] = kwargs["type"].value
        if "status" in kwargs and isinstance(kwargs["status"], AgentStatus):
            kwargs["status"] = kwargs["status"].value
        super().__init__(*args, **kwargs)

    @property
    def tool_configs_list(self) -> list[ToolConfig]:
        if not self.tool_configs:
            return []
        return [ToolConfig.model_validate(config) for config in self.tool_configs]

    @tool_configs_list.setter
    def tool_configs_list(self, configs: list[ToolConfig]):
        self.tool_configs = [config.model_dump() for config in configs]
