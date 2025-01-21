from typing import Optional, List
from pydantic import BaseModel
from openagent.tools import ToolConfig


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

    def get_tool_configs_data(self) -> List[dict]:
        return [config.model_dump() for config in self.tool_configs]


# Run Agent
class RunAgentRequest(BaseModel):
    agent_id: int
