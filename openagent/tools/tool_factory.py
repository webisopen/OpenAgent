from openagent.database.models.agent import Agent
from openagent.database.models.tool import Tool
from phi.model.base import Model
from openagent.tools import BaseTool, ToolConfig


def get_tool_executor(
    agent: Agent, tool: Tool, model: Model, tool_config: ToolConfig
) -> BaseTool:
    match tool.name:
        case "twitter.tweet_generator":
            from .twitter.tweet_generator import TweetGeneratorTools

            return TweetGeneratorTools(
                agent=agent, model=model, tool_config=tool_config
            )
        case _:
            raise ValueError(f"Unsupported tool: {tool.name}")
