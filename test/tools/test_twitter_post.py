import os
import asyncio
from dotenv import load_dotenv

from openagent.tools.twitter_post import (
    TwitterPostTool,
    TwitterToolConfig,
    TwitterCredentials,
)


async def test_twitter_post():
    """Test function for the Twitter posting tool"""
    load_dotenv()

    # Get Twitter credentials from environment variables
    config = TwitterToolConfig(
        credentials=TwitterCredentials(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            api_key=os.getenv("TWITTER_API_KEY"),
            api_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        )
    )

    # Initialize the tool
    twitter_tool = TwitterPostTool()
    await twitter_tool.setup(config)

    # Test posting a tweet
    test_tweet = "This is a test tweet from OpenAgent Twitter Tool! 🤖"
    result = await twitter_tool(test_tweet)
    print(result)


if __name__ == "__main__":
    asyncio.run(test_twitter_post())
