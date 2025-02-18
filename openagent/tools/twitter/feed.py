from typing import Optional

from loguru import logger
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta, UTC
import re

from openagent.core.tool import Tool


class Tweet(BaseModel):
    """Model representing a tweet"""

    tweet_id: str
    handle: str
    content: str
    created_at: datetime
    type: str


class TwitterFeedConfig(BaseModel):
    """Configuration for the Twitter feed function"""

    handles: list[str]  # List of Twitter handles to fetch tweets from
    limit: int = 50  # Default number of tweets to return per handle
    tweet_type: Optional[str] = (
        None  # Optional filter for tweet type (tweet, reply, retweet, quote)
    )
    time_filter: Optional[str] = (
        None  # Time filter in format like "10min", "1hour", "24hour"
    )

    @property
    def time_threshold(self) -> Optional[datetime]:
        """Convert time filter string to datetime threshold"""
        if not self.time_filter:
            return None

        pattern = r"(\d+)(min|hour)"
        match = re.match(pattern, self.time_filter)
        if not match:
            return None

        value, unit = match.groups()
        value = int(value)

        now = datetime.now(UTC)  # Already UTC aware
        if unit == "min":
            return now - timedelta(minutes=value)
        elif unit == "hour":
            return now - timedelta(hours=value)
        return None


class GetTwitterFeed(Tool[TwitterFeedConfig]):
    """Function to get tweets from a Twitter handle using RSS3 API"""

    @property
    def name(self) -> str:
        return "get_twitter_feed"

    @property
    def description(self) -> str:
        return "Get recent tweets from a specified Twitter handle with optional time filtering"

    def __init__(self):
        super().__init__()
        self.config: TwitterFeedConfig | None = None
        self.base_url = "https://ai.rss3.io/api/v1/tweets"

    async def setup(self, config: TwitterFeedConfig) -> None:
        """Setup the function with configuration"""
        self.config = config

    async def __call__(self) -> str:
        """Get recent tweets from the configured Twitter handles.

        Returns:
            str: A formatted string containing the tweets or error message
        """
        logger.info(f"{self.name} tool is called with config: {self.config}")
        all_tweets = []

        async with httpx.AsyncClient() as client:
            for handle in self.config.handles:
                try:
                    params = {"limit": self.config.limit if self.config else 50}
                    if self.config and self.config.tweet_type:
                        params["type"] = self.config.tweet_type

                    response = await client.get(
                        f"https://ai.rss3.io/api/v1/tweets/{handle}", params=params
                    )
                    if response.status_code != 200:
                        logger.error(
                            f"Error fetching tweets for @{handle}: HTTP {response.status_code}"
                        )
                        continue

                    tweets = response.json()
                    if not tweets:
                        logger.info(f"No tweets found for @{handle}")
                        continue

                    # Apply time filter if configured
                    time_threshold = self.config.time_threshold if self.config else None
                    if time_threshold:
                        filtered_tweets = []
                        for tweet in tweets:
                            tweet_time = datetime.fromisoformat(
                                tweet["created_at"]
                            ).replace(tzinfo=UTC)
                            if tweet_time >= time_threshold:
                                filtered_tweets.append(tweet)
                        tweets = filtered_tweets

                        if not tweets:
                            logger.info(f"No recent tweets found for @{handle}")
                            continue

                    # Add tweets to the collection
                    for tweet in tweets:
                        tweet_obj = Tweet(**tweet)
                        all_tweets.append(tweet_obj)

                except Exception as e:
                    logger.error(f"Error fetching tweets for @{handle}: {str(e)}")
                    continue

        if not all_tweets:
            return "No tweets found matching the criteria."

        # Sort all tweets by creation time
        all_tweets.sort(key=lambda x: x.created_at, reverse=True)

        # Format the tweets into a readable string
        formatted_tweets = []
        for tweet in all_tweets:
            created_at = tweet.created_at.strftime("%Y-%m-%d %H:%M:%S")
            formatted_tweets.append(
                f"TWEET_ID={tweet.tweet_id}||"
                f"@{tweet.handle} [{created_at}] {tweet.type.upper()}: {tweet.content}"
            )

        return "\n\n".join(formatted_tweets)
