from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic
from pydantic import BaseModel


ConfigT = TypeVar('ConfigT', bound=BaseModel)


class Output(ABC, Generic[ConfigT]):
    """Base class for all output handlers"""

    def __init__(self):
        self.context: Dict[str, Any] = {}

    @abstractmethod
    async def setup(self, config: ConfigT) -> None:
        """Setup the output handler with configuration"""
        pass

    @abstractmethod
    async def send(self, message: str) -> bool:
        """Send a message through this output channel"""
        pass
