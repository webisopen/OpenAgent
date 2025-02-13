import os
import asyncio
from dotenv import load_dotenv

from openagent.tools.token_price import PriceTool, PriceToolConfig


async def test_token_price():
    """Test function for the token price tool"""
    load_dotenv()

    # Get CoinGecko API key from environment variables
    config = PriceToolConfig(coingecko_api_key=os.getenv("COINGECKO_API_KEY"))

    # Initialize the tool
    price_tool = PriceTool()
    await price_tool.setup(config)

    # Test getting price for Ethereum
    test_token = "ETH"
    result = await price_tool(test_token)
    print(result)


if __name__ == "__main__":
    asyncio.run(test_token_price())
