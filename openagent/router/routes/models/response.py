from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel
from openagent.db.models.agent import AgentStatus
from openagent.db.models.tool import ToolType
from openagent.tools import ToolConfig

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None


class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    instruction: Optional[str] = None
    wallet_address: str
    token_image: Optional[str] = None
    ticker: str
    contract_address: Optional[str] = None
    pair_address: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None
    tool_configs: Optional[List[ToolConfig]] = None
    status: AgentStatus


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


class ModelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    capability_score: float
    capabilities: Optional[str] = None


class ModelListResponse(BaseModel):
    models: List[ModelResponse]
    total: int


class ToolResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: ToolType


class ToolListResponse(BaseModel):
    tools: List[ToolResponse]
    total: int
