import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, TypeVar, Union, Awaitable

from agno.tools import Function
from pydantic import BaseModel

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class Tool(ABC):
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
    def __call__(self, *args, **kwargs) -> Union[Any, Awaitable[Any]]:
        """
        Execute the function. Can be either synchronous or asynchronous.
        If asynchronous, it should return an Awaitable.
        """
        raise NotImplementedError("Subclasses must implement __call__")

    def to_function(self) -> "Function":
        """Convert to Function object"""
        original_call = self.__call__
        original_signature = inspect.signature(original_call)

        @wraps(original_call)
        async def wrapper(*args, **kwargs):
            result = self.__call__(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        # Preserve the original signature with annotations
        wrapper.__signature__ = original_signature
        wrapper.__name__ = self.name
        wrapper.__doc__ = original_call.__doc__
        wrapper.__annotations__ = original_call.__annotations__

        return Function.from_callable(wrapper)
