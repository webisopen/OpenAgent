from phi.agent import Agent

from openagent.tools import DSLTools

feed_agent = Agent(
    name="Feed Agent",
    tools=[DSLTools()],
)
