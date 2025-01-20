from typing import Optional, List
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam
from openagent.tools import ToolConfig


# Create Chat Completion
class CreateChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessageParam]


# Create Agent
class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    instruction: Optional[str] = None
    token_image: Optional[str] = None
    ticker: str
    contract_address: Optional[str] = None
    pair_address: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None
    tool_configs: Optional[List[ToolConfig]] = None


# Run Agent
class RunAgentRequest(BaseModel):
    agent_id: int
