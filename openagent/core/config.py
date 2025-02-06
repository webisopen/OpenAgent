from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field
import os
import re


class LLMConfig(BaseModel):
    model: str = Field(default="gpt-4", description="Name of the language model to use")
    temperature: float = Field(
        default=0.7, description="Temperature for model sampling"
    )
    system_prompt: Optional[str] = Field(
        default=None, description="System prompt for the model"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the language model. If not provided, will try to load from environment variable based on model prefix",
    )


class IOConfig(BaseModel):
    inputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Input handler configurations"
    )
    outputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Output handler configurations"
    )


class AgentConfig(BaseModel):
    name: str = Field(default="default-agent", description="Name of the agent")
    description: str = Field(default="", description="Description of the agent")
    stateful: Optional[bool] = Field(
        default=True, description="Whether to load session state from storage"
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig, description="Language model configuration"
    )
    tools: List[str] = Field(
        default_factory=list, description="List of tool names to load"
    )
    io: IOConfig = Field(
        default_factory=IOConfig, description="IO handler configurations"
    )

    @staticmethod
    def _expand_env_vars(value: Any) -> Any:
        """Recursively expand environment variables in values"""
        if isinstance(value, str):
            # Find all ${VAR} patterns
            pattern = r"\${([^}]+)}"
            matches = re.finditer(pattern, value)

            # Replace each match with environment variable value
            result = value
            for match in matches:
                env_var = match.group(1)
                env_value = os.getenv(env_var)
                if env_value is None:
                    raise ValueError(f"Environment variable {env_var} is not set")
                result = result.replace(f"${{{env_var}}}", env_value)
            return result
        elif isinstance(value, dict):
            return {k: AgentConfig._expand_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [AgentConfig._expand_env_vars(item) for item in value]
        return value

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "AgentConfig":
        """Load configuration from a YAML file"""
        import yaml

        with open(yaml_path, "r") as f:
            config_dict = yaml.safe_load(f)

        # Expand environment variables in the config
        config_dict = cls._expand_env_vars(config_dict)

        return cls(**config_dict)
