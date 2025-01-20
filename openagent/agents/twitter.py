from phi.agent import Agent
from ..tools.twitter.tweet_generator import TweetGeneratorTools

twitter_agent = Agent(
    name="twitter_agent",
    description="An agent that generates and posts tweets in different personalities",
    tools=[TweetGeneratorTools()],
)

__all__ = ["twitter_agent"]
