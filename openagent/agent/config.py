import os
import re
from typing import Dict, Optional, Any, List

from pydantic import BaseModel, Field, validator


class LLMConfig(BaseModel):
    model: str
    temperature: float = 0.7
    api_key: Optional[str] = None


class SchedulerConfig(BaseModel):
    type: str = Field(description="Type of scheduler to use ('local' or 'celery')")
    broker_url: Optional[str] = None
    result_backend: Optional[str] = None

    @validator("type")
    def validate_scheduler_type(cls, v):
        if v not in ["local", "celery"]:
            raise ValueError("Scheduler type must be either 'local' or 'celery'")
        return v

    @validator("broker_url", "result_backend")
    def validate_celery_urls(cls, v, values):
        if values.get("type") == "celery" and not v:
            raise ValueError(
                "broker_url and result_backend are required for Celery scheduler"
            )
        return v


class TaskConfig(BaseModel):
    interval: int = Field(description="Interval in seconds between task executions")
    question: str
    scheduler: SchedulerConfig = Field(
        default_factory=lambda: SchedulerConfig(type="local"),
        description="Scheduler configuration for this task",
    )

    @validator("interval")
    def validate_interval(cls, v):
        if v < 1:
            raise ValueError("Interval must be at least 1 second")
        return v


class AgentConfig(BaseModel):
    name: str = Field(default="default-agent", description="Name of the agent")
    description: str = Field(
        default="",
        description="A description that guides the overall behaviour of the agent",
    )
    instructions: List[str] = Field(
        default_factory=list, description="List of precise, task-specific instructions"
    )
    debug_mode: bool = Field(
        default=False, description="Enable debug mode to view detailed logs"
    )
    markdown: bool = Field(default=True, description="Format output using markdown")
    stateful: Optional[bool] = Field(
        default=True, description="Whether to load session state from storage"
    )
    llm: LLMConfig
    tools: Dict[str, Dict[str, Any]] = {}
    tasks: Dict[str, TaskConfig] = {}

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
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Load config from yaml file"""
        import yaml

        with open(path) as f:
            config_dict = yaml.safe_load(f)

            # Expand environment variables in the config
            config_dict = cls._expand_env_vars(config_dict)

            return cls(**config_dict)
