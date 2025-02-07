import json
from typing import Any

import requests
from pydantic import BaseModel, Field

from openagent.core.interfaces.tool import Tool


class PriceToolConfig(BaseModel):
    coingecko_api_key: str = Field(
        description="CoinGecko API key for accessing price data"
    )


async def fetch_price(token: str, coingecko_api_key) -> str:
    url = f"https://pro-api.coingecko.com/api/v3/search?query={token}"

    headers = {"accept": "application/json", "x-cg-pro-api-key": coingecko_api_key}

    response = requests.get(url, headers=headers)
    token_: dict = json.loads(response.text)["coins"][0]
    token_id_ = token_["id"]

    url = (
        f"https://pro-api.coingecko.com/api/v3/simple/price?ids={token_id_}&"
        f"vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&"
        f"include_24hr_change=true&include_last_updated_at=true"
    )

    headers = {"accept": "application/json", "x-cg-pro-api-key": coingecko_api_key}

    response = requests.get(url, headers=headers)
    return response.text


class PriceTool(Tool):
    """Tool for fetching token prices from CoinGecko."""

    @property
    def name(self) -> str:
        return "token_price"

    @property
    def description(self) -> str:
        return (
            "Use this tool to get the price and market data of a cryptocurrency token"
        )

    def __init__(self):
        super().__init__()
        self.coingecko_api_key = None

    async def setup(self, config: PriceToolConfig) -> None:
        """Setup the price tool with configuration"""
        self.coingecko_api_key = config.coingecko_api_key

    async def __call__(self, token: str) -> Any:
        """Execute the price tool to get token price data
        @type token: the token symbol, like 'ETH', 'BTC'
        """
        return await fetch_price(token, self.coingecko_api_key)
