from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from openagent.database.models.agent import AgentStatus
from openagent.database.models.tool import ToolType
from openagent.tools import ToolConfig

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
    status: AgentStatus


class AgentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agents: list[AgentResponse]
    total: int


class ModelResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    capability_score: float
    capabilities: str | None = None


class ModelListResponse(BaseModel):
    models: list[ModelResponse]
    total: int


class ToolResponse(BaseModel):
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
