from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    model: str = Field(default="gpt-4", description="Name of the language model to use")
    temperature: float = Field(default=0.7, description="Temperature for model sampling")
    system_prompt: Optional[str] = Field(default=None, description="System prompt for the model")


class IOConfig(BaseModel):
    inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Input handler configurations")
    outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Output handler configurations")


class AgentConfig(BaseModel):
    name: str = Field(default="default-agent", description="Name of the agent")
    description: str = Field(default="", description="Description of the agent")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="Language model configuration")
    tools: List[str] = Field(default_factory=list, description="List of tool names to load")
    io: IOConfig = Field(default_factory=IOConfig, description="IO handler configurations")

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "AgentConfig":
        """Load configuration from a YAML file"""
        import yaml
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict) 