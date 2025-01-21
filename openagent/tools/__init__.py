from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional
from enum import Enum
from phi.tools import Toolkit
from phi.model.base import Model
from pydantic import BaseModel, ConfigDict

from openagent.database.models.tool import Tool


class TriggerType(Enum):
    SCHEDULED = "scheduled"
    AUTO = "auto"
    Manual = "manual"


class ToolParameters(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trigger_type: TriggerType
    schedule: Optional[str] = None  # cron, such as "0 */2 * * *"
    auth: Optional[Dict[str, Any]] = None

    def validate_schedule(self):
        if self.trigger_type == TriggerType.SCHEDULED and not self.schedule:
            raise ValueError("Schedule must be set when trigger_type is SCHEDULED")


class ToolConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: Optional[str] = None
    tool_id: int
    model_id: int
    parameters: Optional[ToolParameters] = None

    def validate_parameters(self):
        if self.parameters:
            self.parameters.validate_schedule()

    def model_dump(self, *args, **kwargs) -> dict:
        data = super().model_dump(*args, **kwargs)
        if data.get("parameters") and "trigger_type" in data["parameters"]:
            data["parameters"]["trigger_type"] = data["parameters"]["trigger_type"].value
        return data


class BaseTool(Toolkit, ABC):
    def __init__(self, name: str, model: Optional[Model] = None):
        super().__init__(name=name)
        self.model = model

    @abstractmethod
    def run(self, **kwargs) -> Tuple[bool, Any]:
        """
        execute the tool

        Args:
            **kwargs: the input parameters

        Returns:
            Tuple[bool, Any]: (success, result)
        """
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        validate the input parameters

        Args:
            params: the input parameters

        Returns:
            Tuple[bool, str]: (success, error message)
        """
        pass


def get_tool_executor(tool: Tool, model: Model) -> BaseTool:
    match tool.name:
        case "twitter.post":
            from .twitter.tweet_generator import TweetGeneratorTools

            return TweetGeneratorTools(model=model)
        # TODO: add more tools
        case _:
            raise ValueError(f"Unsupported tool: {tool.name}")


__all__ = [
    "BaseTool",
    "ToolConfig",
    "TriggerType",
    "ToolParameters",
    "get_tool_executor",
]
