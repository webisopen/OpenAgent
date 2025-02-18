import asyncio

from openagent.tools.twitter.feed import GetTwitterFeed, TwitterFeedConfig


async def test_twitter_feed():
    """Test function for the Twitter feed tool"""
    # Initialize configuration
    config = TwitterFeedConfig(
        handles=["pendleintern"],  # List of Twitter handles to monitor
        limit=1,  # Get 5 most recent tweets per handle
        tweet_type="tweet",  # Only get original tweets
        time_filter="24hour",  # Only get tweets from the last hour
    )

    # Initialize the tool
    twitter_tool = GetTwitterFeed()
    await twitter_tool.setup(config)

    # Test getting tweets
    result = await twitter_tool()
    print("\nFetching tweets from multiple accounts:")
    print(result)


if __name__ == "__main__":
    asyncio.run(test_twitter_feed())
