from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Dict


class Input(ABC):
    """Base class for all input handlers"""

    @abstractmethod
    async def setup(self, config: Dict[str, Any]) -> None:
        """Setup the input handler with configuration"""
        pass

    @abstractmethod
    async def listen(self) -> AsyncIterator[str]:
        """Listen for incoming messages"""
        pass 