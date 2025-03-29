import pytest

from openagent.agent.config import ModelConfig
from openagent.tools.pendle.market_analysis import PendleMarketTool, PendleMarketConfig


@pytest.mark.asyncio
async def test_pendle_market():
    # Initialize configuration
    config = PendleMarketConfig(
        model=ModelConfig(provider="openai", name="gpt-4", temperature=0.7),
        db_url="sqlite:///storage/test_pendle_market.db",
    )

    # Initialize the tool
    market_tool = PendleMarketTool()
    await market_tool.setup(config)

    # Test market analysis
    result = await market_tool()
    print("\nMarket Analysis Result (SQLite):")
    print(result)


@pytest.mark.asyncio
async def test_pendle_market_postgres():
    # Initialize configuration with PostgreSQL
    config = PendleMarketConfig(
        model=ModelConfig(provider="openai", name="gpt-4", temperature=0.7),
        db_url="postgresql://postgres:password@localhost:5434/pendle_market_test",
    )

    # Initialize the tool
    market_tool = PendleMarketTool()
    await market_tool.setup(config)

    # Test market analysis
    result = await market_tool()
    print("\nMarket Analysis Result (PostgreSQL):")
    print(result)
