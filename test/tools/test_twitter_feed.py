import asyncio

from openagent.tools.twitter_feed import GetTwitterFeed, TwitterFeedConfig


async def test_twitter_feed():
    """Test function for the Twitter feed tool"""
    # Initialize configuration
    config = TwitterFeedConfig(
        limit=5,  # Get 5 most recent tweets
        tweet_type="tweet",  # Only get original tweets
        time_filter="12hour"  # Only get tweets from the last hour
    )

    # Initialize the tool
    twitter_tool = GetTwitterFeed()
    await twitter_tool.setup(config)

    # Test getting tweets for Vitalik Buterin
    test_handle = "aixbt_agent"
    result = await twitter_tool(test_handle)
    print(f"\nFetching tweets for @{test_handle}:")
    print(result)


if __name__ == "__main__":
    asyncio.run(test_twitter_feed())
