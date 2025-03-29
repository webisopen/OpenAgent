import pytest

from openagent.tools.pendle.voter_apy_analysis import (
    PendleVoterApyTool,
    PendleVoterApyConfig,
)
from openagent.agent.config import ModelConfig


@pytest.mark.asyncio
async def test_pendle_voter_apy():
    # Initialize model config
    model_config = ModelConfig(name="gpt-4o", provider="openai", temperature=0.7)

    # Initialize tool config
    config = PendleVoterApyConfig(model=model_config)

    # Initialize the tool
    voter_apy_tool = PendleVoterApyTool()
    await voter_apy_tool.setup(config)

    # Test getting Pendle voter APY analysis
    result = await voter_apy_tool()
    print(result)
