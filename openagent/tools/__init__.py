from .coingecko import CoinGeckoTools
from typing import Optional
from .dsl import DSLTools
from pydantic import BaseModel

__all__ = [CoinGeckoTools, DSLTools]


class ToolConfig(BaseModel):
    tool_id: int
    model_id: int
    parameters: Optional[dict] = None
