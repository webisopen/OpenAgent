import json
from os import environ
from typing import ClassVar
import requests
from phi.tools import Toolkit


class CoinGeckoTools(Toolkit):
    base_url: ClassVar[str] = "https://pro-api.coingecko.com/api/v3"
    headers: ClassVar[dict] = {"x-cg-pro-api-key": environ.get("COINGECKO_API_KEY")}

    def __init__(self):
        super().__init__(name="coingecko_tools")

        self.register(self.fetch_tokens)
        self.register(self.fetch_token_price)

    def fetch_tokens(self, name: str) -> str:
        """
        Fetch tokens from CoinGecko API.

        Args:
            name (str): The name of token.
        Returns:
            A JSON-formatted string containing a list of tokens matching the search query.
        """

        return requests.get(
            f"{self.base_url}/search?query={name}", headers=self.headers
        ).text

    def fetch_token_price(self, name: str) -> str:
        """
        Fetch the token price from CoinGecko API.

        Args:
            name (str): The name of token.
        Returns:
            A JSON-formatted string containing the token price.
        """

        try:
            token = json.loads(self.fetch_tokens(name))["coins"][0]

            return requests.get(
                f"{self.base_url}/simple/price?ids={token['id']}&vs_currencies=usd",
                headers=self.headers,
            ).text
        except Exception as error:
            return json.dumps({"error": str(error)})
