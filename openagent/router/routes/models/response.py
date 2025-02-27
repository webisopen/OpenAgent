from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from openagent.database.models.agent import AgentStatus, AgentType
from openagent.database.models.tool import ToolType
from openagent.tools.tool_config import ToolConfig

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: T | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    personality: str | None = None
    instruction: str | None = None
    wallet_address: str
    token_image: str | None = None
    ticker: str
    contract_address: str | None = None
    pair_address: str | None = None
    twitter: str | None = None
    telegram: str | None = None
    website: str | None = None
    tool_configs: list[ToolConfig] | None = None
    type: AgentType
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


class PublicToolConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None
    tool_id: int
    model_id: int


class PublicAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    personality: str | None = None
    instruction: str | None = None
    wallet_address: str
    token_image: str | None = None
    ticker: str
    contract_address: str | None = None
    pair_address: str | None = None
    twitter: str | None = None
    telegram: str | None = None
    website: str | None = None
    tool_configs: list[PublicToolConfigResponse] | None = None
    type: AgentType
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, obj):
        if hasattr(obj, "tool_configs") and obj.tool_configs:
            obj.tool_configs = [
                PublicToolConfigResponse(
                    name=tc["name"],
                    description=tc.get("description"),
                    tool_id=tc["tool_id"],
                    model_id=tc["model_id"],
                )
                for tc in obj.tool_configs
            ]
        return super().from_orm(obj)


class AgentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agents: list[PublicAgentResponse]
    total: int


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    capability_score: float
    capabilities: str | None = None


class ModelListResponse(BaseModel):
    models: list[ModelResponse]
    total: int


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    type: ToolType


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]
    total: int


class AuthResponse(BaseModel):
    token: str
    wallet_address: str
