from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict
from phi.model.base import Model
from phi.tools import Toolkit
from pydantic import BaseModel, ConfigDict, model_validator


class TriggerType(Enum):
    SCHEDULED = "scheduled"
    AUTO = "auto"
    Manual = "manual"

    def __str__(self) -> str:
        return self.value


class ToolParameters(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={TriggerType: lambda v: v.value},
    )

    trigger_type: TriggerType
    schedule: str | None = None  # cron, such as "0 */2 * * *"
    config: dict | None = None

    def validate_schedule(self):
        if self.trigger_type == TriggerType.SCHEDULED and not self.schedule:
            raise ValueError("Schedule must be set when trigger_type is SCHEDULED")

    def model_dump(self, *args, **kwargs) -> dict:
        # Add custom serialization for TriggerType
        data = super().model_dump(*args, **kwargs)
        data["trigger_type"] = self.trigger_type.value
        return data


class ToolConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    tool_id: int
    model_id: int
    parameters: ToolParameters | None = None

    def validate_parameters(self):
        if self.parameters:
            self.parameters.validate_schedule()

    def model_dump(self, *args, **kwargs) -> dict:
        data = {
            "name": self.name,
            "description": self.description,
            "tool_id": self.tool_id,
            "model_id": self.model_id,
        }

        if self.parameters:
            data["parameters"] = self.parameters.model_dump()

        return data


class TwitterToolParameters(ToolParameters):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def validate_twitter_config(cls, data: Dict) -> Dict:
        if (
            isinstance(data, dict)
            and "config" in data
            and isinstance(data["config"], dict)
        ):
            data["config"] = {
                "access_token": data["config"].get("access_token"),
                "access_token_secret": data["config"].get("access_token_secret"),
            }
        return data


class BaseTool(Toolkit, ABC):
    def __init__(self, name: str, model: Model | None = None):
        super().__init__(name=name)
        self.model = model

    @abstractmethod
    def run(self, **kwargs) -> tuple[bool, Any]:
        """
        execute the tool

        Args:
            **kwargs: the input parameters

        Returns:
            Tuple[bool, Any]: (success, result)
        """
        pass

    @abstractmethod
    def validate_params(self, params: dict[str, Any]) -> tuple[bool, str]:
        """
        validate the input parameters

        Args:
            params: the input parameters

        Returns:
            Tuple[bool, str]: (success, error message)
        """
        pass


__all__ = [
    "BaseTool",
    "ToolConfig",
    "ToolParameters",
    "TwitterToolParameters",
    "TriggerType",
]
