import asyncio

from openagent.tools.twitter.feed import GetTwitterFeed, TwitterFeedConfig


async def test_twitter_feed():
    """Test function for the Twitter feed tool"""
    # Initialize configuration
    config = TwitterFeedConfig(
        handles=[
            'pendleintern',
            'pendle_fi',
            'phtevenstrong',
            '2lambro',
            'crypto_linn',
            'NaveenCypto',
            '0xMughal',
            "EthereumThaila1",
            "hmalviya9",
            "kenodnb",
            "Jonasoeth",
            "0xWenMoon",
            "tn_pendle",
            'Rightsideonly',
            'imkenchia',
            'gabavineb',
            'gentpendle',
            'DDangleDan',
            'Aprilzz423',
            '_whalebird',
            'ayobuenavista',
        ],  # List of Twitter handles to monitor
        limit=10,  # Get 5 most recent tweets per handle
        tweet_type="tweet",  # Only get original tweets
        time_filter="1hour",  # Only get tweets from the last hour
    )

    # Initialize the tool
    twitter_tool = GetTwitterFeed()
    await twitter_tool.setup(config)

    # Test getting tweets
    await twitter_tool()


if __name__ == "__main__":
    asyncio.run(test_twitter_feed())
