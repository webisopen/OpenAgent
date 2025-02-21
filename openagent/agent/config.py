import os
import re
from typing import Dict, Optional, Any, List

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    name: str = Field(description="Name of the model")
    temperature: float = Field(default=0.7, description="Temperature of the model")
    provider: str = Field(default=None, description="Provider of the model")
    api_key: Optional[str] = None


class SchedulerConfig(BaseModel):
    type: str = Field(description="Type of scheduler to use ('local' or 'queue')")
    broker_url: Optional[str] = None
    result_backend: Optional[str] = None

    @classmethod
    @field_validator("type")
    def validate_scheduler_type(cls, v):
        if v not in ["local", "queue"]:
            raise ValueError("Scheduler type must be either 'local' or 'queue'")
        return v

    @classmethod
    @field_validator("broker_url", "result_backend")
    def validate_celery_urls(cls, v, values):
        if values.get("type") == "queue" and not v:
            raise ValueError(
                "broker_url and result_backend are required for Celery scheduler"
            )
        return v


class TaskConfig(BaseModel):
    interval: Optional[int] = Field(default=None, description="Interval in seconds between task executions")
    delay_variation: Optional[int] = Field(
        default=0, description="Maximum random delay in seconds to add to the interval"
    )
    query: str
    cron: Optional[str] = Field(default=None, description="Cron expression for scheduling tasks")
    schedule: SchedulerConfig = Field(
        default_factory=lambda: SchedulerConfig(type="local"),
        description="Scheduler configuration for this task",
    )

    @classmethod
    @field_validator("interval")
    def validate_interval(cls, v):
        if v is not None and v < 1:
            raise ValueError("Interval must be greater than 1 second")
        return v

    @classmethod
    @field_validator("delay_variation")
    def validate_delay_variation(cls, v):
        if v is not None and v < 0:
            raise ValueError("Delay variation must be non-negative")
        return v


class AgentConfig(BaseModel):
    name: str = Field(default="default-agent", description="Name of the agent")
    description: str = Field(
        default="",
        description="A description that guides the overall behaviour of the agent",
    )
    instructions: List[str] = Field(
        default=[], description="List of precise, task-specific instructions"
    )
    goal: List[str] = Field(default=[], description="List of goals to achieve")
    debug_mode: bool = Field(
        default=False, description="Enable debug mode to view detailed logs"
    )
    markdown: bool = Field(default=True, description="Format output using markdown")
    stateful: Optional[bool] = Field(
        default=True, description="Whether to load session state from storage"
    )
    core_model: ModelConfig
    tools: Dict[str, Dict[str, Any]] = Field(default={}, description="List of tools")
    tasks: Dict[str, TaskConfig] = Field(default={}, description="List of tasks")

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
