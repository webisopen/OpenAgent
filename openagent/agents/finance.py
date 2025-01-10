from phi.agent import Agent

from openagent.tools import CoinGeckoTools

finance_agent = Agent(
    name="Finance Agent",
    tools=[CoinGeckoTools()],
)
