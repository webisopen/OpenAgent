from abc import ABC, abstractmethod
from typing import Any, Dict


class Output(ABC):
    """Base class for all output handlers"""

    @abstractmethod
    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup the output handler with configuration"""
        pass

    @abstractmethod
    async def send(self, message: str) -> bool:
        """Send a message through this output channel"""
        pass 