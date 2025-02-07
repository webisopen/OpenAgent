from abc import ABC, abstractmethod
from typing import Any, TypeVar

from agno.tools import Function
from pydantic import BaseModel

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseFunction(ABC):
    """Base class for functions that can be converted to Function objects."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Function name must be defined in subclasses"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Function description must be defined in subclasses"""
        pass

    def __init__(self):
        self.__name__ = self.name
        self.__doc__ = self.description

    @abstractmethod
    async def setup(self, config: ConfigT) -> None:
        """Setup the function with configuration"""
        pass

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement __call__")

    def to_function(self) -> "Function":
        """Convert to Function object"""
        return Function.from_callable(self.__call__)

