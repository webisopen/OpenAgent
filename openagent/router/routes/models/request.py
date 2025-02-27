from openagent.database.models.agent import AgentType
from pydantic import BaseModel

from openagent.tools.tool_config import ToolConfig


# Create Agent
class CreateAgentRequest(BaseModel):
    name: str
    description: str | None = None
    personality: str | None = None
    instruction: str | None = None
    token_image: str | None = None
    ticker: str
    contract_address: str | None = None
    pair_address: str | None = None
    twitter: str | None = None
    telegram: str | None = None
    website: str | None = None
    type: AgentType
    tool_configs: list[ToolConfig] | None = None

    def get_tool_configs_data(self) -> list[dict]:
        return [config.model_dump() for config in self.tool_configs]


# Run Agent
class RunAgentRequest(BaseModel):
    agent_id: int
